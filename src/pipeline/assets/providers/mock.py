"""Deterministic fake provider for tests and dry runs: it behaves like a slow, flaky remote service.

Controlled per request through `request["_mock"]`:
  polls: int           polls spent in 'running' before success (default 2)
  fail_submit: int     first N submit calls raise a retryable network error
  fail_with: str       always fail terminally with this error kind ('auth', 'invalid-request', 'provider')
  poll_errors: int     first N status calls raise a retryable error (transient outage)
  fail_job: bool       job reaches the 'failed' state remotely (retryable=False)
  fail_job_times: int  job fails remotely this many times, then succeeds (retryable)
  hang: bool           never completes
  no_files: bool       'succeeds' without returning a file
State is kept in a JSON file so a second Engine/process can resume a job by remote id.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

from .. import base


class MockProvider(base.Provider):
    name = "mock"

    def __init__(self, state_dir: Path, tasks: Optional[List[str]] = None):
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.dir / "mock-state.json"
        self.tasks = tasks or ["text-to-image", "image-to-image", "text-to-video", "image-to-video"]
        self.submits = 0

    def _load(self) -> Dict[str, Any]:
        return json.loads(self.state_file.read_text()) if self.state_file.exists() else {"jobs": {}, "counters": {}}

    def _save(self, s: Dict[str, Any]) -> None:
        self.state_file.write_text(json.dumps(s))

    def capabilities(self) -> Dict[str, Any]:
        t = {k: {"aspect_ratios": ["16:9", "9:16", "1:1"], "resolutions": ["720p", "1080p"], "requires": ["prompt"], "max_reference_images": 4} for k in self.tasks}
        for k in t:
            if "video" in k:
                t[k]["duration_sec"] = {"min": 2, "max": 10}
        return {"provider": "mock", "summary": "Deterministic fake remote service for tests.", "tasks": t, "auth": {"method": "none"}, "local": True,
                "verification": {"level": "local", "checked_on": "2026-11-02"}}

    def available(self) -> Optional[str]:
        return None

    def submit(self, task: str, request: Dict[str, Any]) -> str:
        m = request.get("_mock", {})
        s = self._load()
        key = request.get("prompt", "") + request["_job"]
        n = s["counters"].get("submit:" + request.get("prompt", ""), 0)
        s["counters"]["submit:" + request.get("prompt", "")] = n + 1
        self._save(s)
        if m.get("fail_with"):
            raise base.ProviderError(m["fail_with"], f"mock refused ({m['fail_with']})", retryable=False)
        if n < m.get("fail_submit", 0):
            raise base.ProviderError("network", "mock transient network error", retryable=True)
        rid = "mock-" + hashlib.sha256(f"{key}{n}".encode()).hexdigest()[:10]
        s = self._load()
        s["jobs"][rid] = {"polls": 0, "mock": m, "prompt": request.get("prompt", ""), "task": task, "attempt": n}
        self._save(s)
        return rid

    def status(self, remote_id: str) -> base.RemoteStatus:
        s = self._load()
        j = s["jobs"][remote_id]
        m = j["mock"]
        j["polls"] += 1
        self._save(s)
        if j["polls"] <= m.get("poll_errors", 0):
            raise base.ProviderError("network", "mock transient poll error", retryable=True)
        if m.get("hang"):
            return base.RemoteStatus(base.RUNNING, progress=0.1)
        if m.get("fail_job") or j["attempt"] < m.get("fail_job_times", 0):
            return base.RemoteStatus(base.FAILED, error=base.ProviderError("provider", "mock generation failed", retryable=bool(m.get("fail_job_times"))))
        if j["polls"] <= m.get("polls", 2):
            return base.RemoteStatus(base.RUNNING, progress=j["polls"] / (m.get("polls", 2) + 1))
        if m.get("no_files"):
            return base.RemoteStatus(base.SUCCEEDED, result_urls=[])
        return base.RemoteStatus(base.SUCCEEDED, result_urls=[f"mock://{remote_id}"], cost={"credits": 1.0, "reported_by": "mock"})

    def fetch(self, status: base.RemoteStatus, dest_dir: str, stem: str) -> List[str]:
        out = []
        for i, u in enumerate(status.result_urls):
            h = hashlib.sha256(u.encode()).digest()
            im = Image.new("RGB", (64, 36), (h[0], h[1], h[2]))
            p = Path(dest_dir) / f"{stem}-{i}.png"
            im.save(p)
            out.append(str(p))
        return out
