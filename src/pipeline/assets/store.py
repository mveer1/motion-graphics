"""Asset library and job store: plain JSON on disk, atomic writes, content-addressed media.

  <root>/index.jsonl        one asset record per line (specs/asset-spec.json #/definitions/asset)
  <root>/files/<sha[:2]>/<sha>.<ext>   media, deduplicated by content hash
  <root>/jobs/<job-id>.json            job records (#/definitions/job); survive a crashed run

The index is append-mostly: an update writes a new line and the last line per id wins, so a crash can
never truncate history. Reuse lookups go through `request_key`, a hash of everything that determines the
output (task, provider, model, prompt, params, reference content hashes), so an identical request is
answered from the library instead of generating (and paying) again.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .secrets import redact


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def request_key(task: str, provider: str, model: str, prompt: str, params: Dict[str, Any], reference_hashes: Iterable[str]) -> str:
    blob = json.dumps({"task": task, "provider": provider, "model": model, "prompt": prompt, "params": params, "refs": sorted(reference_hashes)}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


class Library:
    def __init__(self, root: Path, workspace: Optional[Path] = None):
        self.root = Path(root)
        self.workspace = Path(workspace) if workspace else self.root.parent.parent
        self.index = self.root / "index.jsonl"
        self.files = self.root / "files"

    # ---- assets
    def all(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        if self.index.exists():
            for line in self.index.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    out[rec["id"]] = rec
        return out

    def get(self, asset_id: str) -> Optional[Dict[str, Any]]:
        return self.all().get(asset_id)

    def _append(self, rec: Dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with open(self.index, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def find_reusable(self, key: str, project: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Newest non-rejected asset made by an identical request whose media still exists."""
        for rec in sorted(self.all().values(), key=lambda r: r["created_at"], reverse=True):
            if rec.get("request_key") == key and rec.get("approval") != "rejected" and (self.workspace / rec["path"]).exists():
                return rec
        return None

    def register(self, src: Path, *, project: str, type_: str, source: str, request_key_: Optional[str] = None, workspace: Optional[Path] = None, **meta: Any) -> Dict[str, Any]:
        """Copy `src` into the content-addressed store and append its record. Returns the record."""
        sha = sha256_file(src)
        ext = src.suffix.lower() or ".bin"
        dst = self.files / sha[:2] / f"{sha}{ext}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)
        rec: Dict[str, Any] = {"id": "ast-" + sha[:12], "project": project, "type": type_, "source": source, "path": str(dst.relative_to(Path(workspace) if workspace else self.workspace)),
                               "sha256": sha, "bytes": dst.stat().st_size, "created_at": now(), "approval": "pending"}
        existing = self.get(rec["id"])
        if existing:  # same bytes already registered: keep the earliest provenance, extend the project/beat links
            rec = {**existing}
            if project != existing["project"]:
                rec.setdefault("notes", "")
                rec["notes"] = (rec["notes"] + f" Also used by {project}.").strip()
        for k, v in meta.items():
            if v is not None:
                rec[k] = v
        if request_key_:
            rec["request_key"] = request_key_
        self._append(rec)
        return rec

    def set_approval(self, asset_id: str, approval: str, note: str = "") -> Dict[str, Any]:
        rec = self.get(asset_id)
        if not rec:
            raise KeyError(asset_id)
        rec = {**rec, "approval": approval}
        if note:
            rec["notes"] = (rec.get("notes", "") + " " + note).strip()
        self._append(rec)
        return rec

    def search(self, **filters: Any) -> List[Dict[str, Any]]:
        out = []
        for rec in self.all().values():
            if all(v is None or rec.get(k) == v for k, v in filters.items()):
                out.append(rec)
        return sorted(out, key=lambda r: r["created_at"])


class JobStore:
    def __init__(self, root: Path):
        self.dir = Path(root) / "jobs"

    def path(self, job_id: str) -> Path:
        return self.dir / f"{job_id}.json"

    def save(self, job: Dict[str, Any]) -> None:
        job["updated_at"] = now()
        atomic_write(self.path(job["id"]), redact(json.dumps(job, indent=2, ensure_ascii=False, default=str)) + "\n")

    def load(self, job_id: str) -> Dict[str, Any]:
        return json.loads(self.path(job_id).read_text(encoding="utf-8"))

    def all(self) -> List[Dict[str, Any]]:
        if not self.dir.exists():
            return []
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(self.dir.glob("job-*.json"))]

    def find_open(self, key: str) -> Optional[Dict[str, Any]]:
        """An unfinished job for an identical request (so a rerun resumes instead of resubmitting)."""
        for j in self.all():
            if j["request_key"] == key and j["state"] in ("queued", "submitted", "running"):
                return j
        return None
