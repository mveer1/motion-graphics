"""Planning, submission, polling, retry and fallback.

Failure is data, not an exception: `run` never raises for a provider problem. A failed or timed-out job
is recorded with a typed error, the next provider in the plan is tried when one is allowed, and the
caller gets a result per request so one failing asset cannot stop a production.

Rules that matter for cost and safety:
  * An identical earlier request is reused from the library; no provider is called.
  * A job that already has a remote id is POLLED, never re-submitted (re-submitting a slow job pays twice).
  * Only errors marked retryable are retried, at most `max_attempts` times, with exponential backoff.
  * Progress is judged by the provider's own state, never by silence: a slow job is not "stalled".
  * Every record and message is redacted before it is written.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import base
from .secrets import MissingSecret, redact
from .store import JobStore, Library, now, request_key, sha256_file

TYPE_BY_TASK = {"text-to-image": "image", "image-to-image": "image", "reference-image": "image", "image-edit": "image", "image-upscale": "image",
                "procedural-image": "image", "text-to-video": "video", "image-to-video": "video", "video-extend": "video", "lip-sync": "video", "import": "image"}


class Engine:
    def __init__(self, workspace: Path, providers: Dict[str, base.Provider], library_root: Optional[Path] = None,
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic):
        self.ws = Path(workspace)
        self.root = Path(library_root) if library_root else self.ws / "assets" / "library"
        self.lib, self.jobs = Library(self.root, self.ws), JobStore(self.root)
        self.providers = providers
        self._sleep, self._clock = sleep, clock

    # ---- planning ---------------------------------------------------------------
    def plan(self, task: str, *, aspect: Optional[str] = None, resolution: Optional[str] = None, duration: Optional[float] = None,
             references: int = 0, prefer: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Providers that can do `task` under the constraints, available ones first. Each entry says why."""
        out = []
        for name, p in self.providers.items():
            caps = p.capabilities()
            spec = caps["tasks"].get(task)
            if spec is None:
                continue
            why: List[str] = []
            ok = True
            if aspect and spec.get("aspect_ratios") and aspect not in spec["aspect_ratios"]:
                ok, why = False, why + [f"aspect {aspect} not offered"]
            if resolution and spec.get("resolutions") and resolution not in spec["resolutions"]:
                ok, why = False, why + [f"resolution {resolution} not offered"]
            if duration is not None and spec.get("duration_sec"):
                d = spec["duration_sec"]
                if duration < d.get("min", 0) or duration > d.get("max", 1e9):
                    ok, why = False, why + [f"duration {duration}s outside {d}"]
            if references > spec.get("max_reference_images", 0 if task != "reference-image" else 0) and references:
                ok, why = False, why + [f"{references} reference images exceed max {spec.get('max_reference_images', 0)}"]
            unavailable = p.available()
            out.append({"provider": name, "fits": ok, "available": unavailable is None, "unavailable_reason": unavailable, "local": bool(caps.get("local")),
                        "verification": caps["verification"]["level"], "notes": why})
        rank = {n: i for i, n in enumerate(prefer or [])}
        out.sort(key=lambda e: (not e["fits"], not e["available"], rank.get(e["provider"], 99), not e["local"]))
        return out

    # ---- submission -------------------------------------------------------------
    def submit(self, *, project: str, task: str, request: Dict[str, Any], providers: List[str], model: str = "",
               max_attempts: int = 3, deadline_sec: float = 600.0, beat: str = "", shot: str = "", force: bool = False) -> Dict[str, Any]:
        """Return a job (new, resumed) or a reuse hit. `providers` is the ordered fallback chain."""
        refs = [self.lib.get(r) for r in request.get("references", [])]
        ref_hashes = [r["sha256"] for r in refs if r]
        params = {k: v for k, v in request.items() if k not in ("prompt", "references", "negative_prompt")}
        key = request_key(task, providers[0], model, request.get("prompt", ""), params, ref_hashes)
        if not force:
            hit = self.lib.find_reusable(key, None)
            if hit:
                return {"reused": True, "asset": hit, "request_key": key}
            open_job = self.jobs.find_open(key)
            if open_job:
                return {"reused": False, "resumed": True, "job": open_job, "request_key": key}
        jid = "job-" + hashlib.sha256(f"{key}{now()}{self._clock()}".encode()).hexdigest()[:12]
        job = {"id": jid, "project": project, "provider": providers[0], "task": task, "state": base.QUEUED, "request": request, "request_key": key,
               "attempts": 0, "max_attempts": max_attempts, "created_at": now(), "deadline_sec": deadline_sec, "poll_count": 0,
               "_chain": providers, "_chain_pos": 0}
        if model:
            job["model"] = model
        if beat:
            job["beat"] = beat
        if shot:
            job["shot"] = shot
        self.jobs.save(job)
        return {"reused": False, "job": job, "request_key": key}

    # ---- stepping ---------------------------------------------------------------
    def _fail(self, job: Dict[str, Any], kind: str, msg: str, retryable: bool, state: str = base.FAILED) -> None:
        job["state"] = state
        job["error"] = {"kind": kind, "retryable": retryable, "message": redact(msg)[:500]}

    def _next_provider(self, job: Dict[str, Any]) -> bool:
        pos = job.get("_chain_pos", 0) + 1
        chain = job.get("_chain", [])
        while pos < len(chain):
            p = self.providers.get(chain[pos])
            if p and chain[pos] and job["task"] in p.capabilities()["tasks"] and p.available() is None:
                job.update(provider=chain[pos], _chain_pos=pos, attempts=0, state=base.QUEUED, remote_id=None)
                job.pop("error", None)
                job.setdefault("fallbacks", []).append(chain[pos])
                return True
            pos += 1
        return False

    def step(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Advance one job by one action (submit or poll). Never raises for provider problems."""
        if job["state"] in base.TERMINAL:
            return job
        p = self.providers.get(job["provider"])
        if p is None:
            self._fail(job, "unsupported", f"provider {job['provider']!r} is not registered", False)
        elif job["state"] == base.QUEUED:
            why = p.available()
            if why:
                self._fail(job, "auth", why, False)
            else:
                job["attempts"] += 1
                try:
                    job["remote_id"] = p.submit(job["task"], {**job["request"], "_model": job.get("model", ""), "_job": job["id"], "_out_dir": str(self.root / "incoming" / job["id"])})
                    job["state"], job["submitted_at"] = base.SUBMITTED, now()
                except base.ProviderError as e:
                    self._fail(job, e.kind, str(e), e.retryable)
                except MissingSecret as e:
                    self._fail(job, "auth", str(e), False)
                except Exception as e:  # adapter bug or network: typed, retryable once
                    self._fail(job, "network" if "urlopen" in repr(e) or isinstance(e, OSError) else "unknown", f"{type(e).__name__}: {e}", isinstance(e, OSError))
        else:
            job["poll_count"] += 1
            try:
                st = p.status(job["remote_id"])
            except base.ProviderError as e:
                if e.retryable:
                    job["last_poll_error"] = redact(str(e))[:200]  # transient: keep polling, do not resubmit
                    st = None
                else:
                    self._fail(job, e.kind, str(e), False)
                    st = None
            except Exception as e:
                job["last_poll_error"] = redact(f"{type(e).__name__}: {e}")[:200]
                st = None
            if st is not None:
                job["state"] = st.state if st.state in (base.RUNNING, base.SUCCEEDED, base.FAILED, base.SUBMITTED, base.CANCELLED) else base.RUNNING
                if st.cost:
                    job["cost"] = st.cost
                if st.state == base.SUCCEEDED:
                    self._finish(job, p, st)
                elif st.state == base.FAILED and st.error:
                    self._fail(job, st.error.kind, str(st.error), st.error.retryable)
        # retry / fallback decision on failure
        if job["state"] == base.FAILED:
            err = job.get("error", {})
            if err.get("retryable") and job["attempts"] < job["max_attempts"]:
                job.update(state=base.QUEUED, remote_id=None)
                job["backoff_sec"] = min(30.0, 1.5 * 2 ** job["attempts"])
            elif self._next_provider(job):
                job["backoff_sec"] = 0
        self.jobs.save(job)
        return job

    def _finish(self, job: Dict[str, Any], p: base.Provider, st: base.RemoteStatus) -> None:
        out_dir = self.root / "incoming" / job["id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            paths = p.fetch(st, str(out_dir), job["id"])
        except Exception as e:
            self._fail(job, "network", f"download failed: {type(e).__name__}: {e}", True)
            return
        ids = []
        for path in paths:
            src = Path(path)
            rec = self.lib.register(src, project=job["project"], type_=TYPE_BY_TASK.get(job["task"], "image") if src.suffix.lower() not in (".mp4", ".mov", ".webm") else "video",
                                    source="procedural" if job["provider"] == "procedural" else ("imported" if job["provider"] == "import" else "generated"),
                                    request_key_=job["request_key"], workspace=self.ws, provider=job["provider"], model=job.get("model") or None, task=job["task"],
                                    prompt=job["request"].get("prompt") or None, params={k: v for k, v in job["request"].items() if k not in ("prompt", "references", "negative_prompt", "_job")} or None,
                                    references=job["request"].get("references") or None, job=job["id"], beat=job.get("beat") or None, shot=job.get("shot") or None,
                                    license=job["request"].get("license") or ({"status": "not-applicable", "notes": "generated procedurally by this workspace"} if job["provider"] == "procedural" else {"status": "provider-terms"}))
            dims = _dims(src)
            if dims:
                rec["width"], rec["height"] = dims
                self.lib._append(rec)
            ids.append(rec["id"])
        job["asset_ids"] = ids
        job["state"] = base.SUCCEEDED if ids else base.FAILED
        if not ids:
            self._fail(job, "provider", "provider reported success but returned no files", False)

    # ---- running ----------------------------------------------------------------
    def run(self, jobs: List[Dict[str, Any]], *, poll_sec: float = 2.0, max_parallel: int = 4, on_event: Optional[Callable[[str], None]] = None) -> List[Dict[str, Any]]:
        """Drive jobs to a terminal state. At most `max_parallel` are in flight; others wait their turn.
        Local providers finish inside submit, so this is cheap for them; remote ones are polled."""
        log = on_event or (lambda m: None)
        start = {j["id"]: self._clock() for j in jobs}
        pending = list(jobs)
        while True:
            live = [j for j in pending if j["state"] not in base.TERMINAL]
            if not live:
                break
            inflight = [j for j in live if j["state"] in (base.SUBMITTED, base.RUNNING)]
            queued = [j for j in live if j["state"] == base.QUEUED]
            todo = inflight + queued[:max(0, max_parallel - len(inflight))]
            for j in todo:
                if self._clock() - start[j["id"]] > j["deadline_sec"]:
                    self._fail(j, "timeout", f"no result within {j['deadline_sec']}s (remote id kept for later polling: {j.get('remote_id')})", False, state=base.TIMED_OUT)
                    self.jobs.save(j)
                    log(f"{j['id']} timed out")
                    continue
                if j.get("backoff_sec"):
                    self._sleep(j.pop("backoff_sec"))
                before = j["state"]
                self.step(j)
                if j["state"] != before:
                    log(f"{j['id']} {before} -> {j['state']} ({j['provider']})")
            if any(j["state"] not in base.TERMINAL for j in pending):
                self._sleep(poll_sec)
        return pending

    def resume_all(self, **kw: Any) -> List[Dict[str, Any]]:
        return self.run([j for j in self.jobs.all() if j["state"] not in base.TERMINAL], **kw)


def _dims(p: Path) -> Optional[tuple]:
    if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        try:
            from PIL import Image
            with Image.open(p) as im:
                return im.size
        except Exception:
            return None
    return None
