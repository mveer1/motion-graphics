"""kie.ai adapter (Market API). Verification level: PARTIAL, checked 2026-11-02.

Verified from the official docs (docs.kie.ai): Bearer auth; errors on /api/v1/* come back as HTTP 200 with a
`code` in the body; `GET /api/v1/jobs/recordInfo?taskId=` returns data.state in
{waiting, queuing, generating, success, fail}, `resultJson` as a JSON *string* (images/video: resultUrls),
failCode/failMsg, costTime, creditsConsumed; creation returns {"code":200,"data":{"taskId":...}};
20 creates per 10 s per account (429 beyond that).

NOT verified from a primary source (do not rely on these without a live check):
  * the create path and body: POST /api/v1/jobs/createTask {"model", "input", "callBackUrl"?} (corroborated by
    Open-Higgsfield's client and a third-party mirror only);
  * the per-model `input` field names (they differ per model; this adapter passes `request["input"]` through
    untouched and only fills `prompt` / `aspect_ratio` when the caller did not);
  * which body `code` values mean what beyond 200 and 429;
  * prices (the API reports creditsConsumed afterwards; this adapter never estimates cost).

Never run against the live service without a key supplied by the user and their approval. Tested here only
against a local stub that reproduces the documented envelope (tests/test-creative-intelligence.py).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from .. import base
from ..secrets import MissingSecret, get_secret, has_secret, redact

ENV_VAR = "KIE_API_KEY"
DEFAULT_BASE = "https://api.kie.ai"
STATE = {"waiting": base.SUBMITTED, "queuing": base.SUBMITTED, "generating": base.RUNNING, "success": base.SUCCEEDED, "fail": base.FAILED}


class KieProvider(base.Provider):
    name = "kie"

    def __init__(self, base_url: str = DEFAULT_BASE, timeout: float = 30.0, sleep=time.sleep, clock=time.monotonic):
        self.base = base_url.rstrip("/")
        self.timeout, self._sleep, self._clock = timeout, sleep, clock
        self._creates: Deque[float] = deque()

    def capabilities(self) -> Dict[str, Any]:
        t = lambda reqs: {"requires": reqs, "models": [], "input_formats": ["url"]}  # noqa: E731  (no model list claimed)
        return {"provider": "kie", "summary": "kie.ai Market API: many third-party image/video models behind one key. Model ids and input fields come from the caller.",
                "tasks": {"text-to-image": t(["model", "prompt"]), "image-to-image": t(["model", "prompt", "image"]),
                          "text-to-video": t(["model", "prompt"]), "image-to-video": t(["model", "prompt", "image"])},
                "auth": {"method": "env-bearer", "env_var": ENV_VAR}, "limits": {"creates_per_10s": 20}, "local": False,
                "verification": {"level": "partial", "checked_on": "2026-11-02", "sources": ["https://docs.kie.ai/", "https://docs.kie.ai/market/common/get-task-detail"],
                                 "unverified": ["create path and body", "per-model input schemas", "error code table beyond 200/429", "pricing", "supported aspect ratios/resolutions per model"]}}

    def available(self) -> Optional[str]:
        return None if has_secret(ENV_VAR) else f"{ENV_VAR} is not set"

    # ---- http
    def _call(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        key = get_secret(ENV_VAR)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "motion-lab/1"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            raise self._http_error(e.code, e.read().decode("utf-8", "replace")) from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise base.ProviderError("network", redact(f"{type(e).__name__}: {e}"), retryable=True) from None
        try:
            j = json.loads(raw)
        except ValueError:
            raise base.ProviderError("provider", "non-JSON response: " + redact(raw[:120]), retryable=True) from None
        code = j.get("code", 200)
        if code != 200:  # documented: failures arrive as HTTP 200 with a code in the body
            raise self._code_error(code, str(j.get("msg", "")))
        return j

    @staticmethod
    def _http_error(status: int, text: str) -> base.ProviderError:
        msg = f"HTTP {status}: {redact(text[:160])}"
        if status in (401, 403):
            return base.ProviderError("auth", msg)
        if status == 429:
            return base.ProviderError("rate-limit", msg, retryable=True)
        if status >= 500:
            return base.ProviderError("provider", msg, retryable=True)
        return base.ProviderError("invalid-request", msg)

    @staticmethod
    def _code_error(code: int, msg: str) -> base.ProviderError:
        m = f"code {code}: {redact(msg[:160])}"
        if code in (401, 403):
            return base.ProviderError("auth", m)
        if code == 429:
            return base.ProviderError("rate-limit", m, retryable=True)
        if code in (400, 422):
            return base.ProviderError("invalid-request", m)
        if code >= 500:
            return base.ProviderError("provider", m, retryable=True)
        return base.ProviderError("unknown", m)  # semantics of other codes are not documented

    def _throttle(self) -> None:
        now = self._clock()
        while self._creates and now - self._creates[0] > 10:
            self._creates.popleft()
        if len(self._creates) >= 20:
            self._sleep(10 - (now - self._creates[0]) + 0.05)
        self._creates.append(self._clock())

    # ---- provider api
    def submit(self, task: str, request: Dict[str, Any]) -> str:
        model = request.get("_model") or request.get("model")
        if not model:
            raise base.ProviderError("invalid-request", "kie needs a model id (taken from the Market page)")
        inp = dict(request.get("input") or {})
        if request.get("prompt") and "prompt" not in inp:
            inp["prompt"] = request["prompt"]
        if request.get("aspect_ratio") and "aspect_ratio" not in inp:
            inp["aspect_ratio"] = request["aspect_ratio"]
        self._throttle()
        j = self._call("POST", "/api/v1/jobs/createTask", {"model": model, "input": inp})
        tid = (j.get("data") or {}).get("taskId")
        if not tid:
            raise base.ProviderError("provider", "create returned no taskId", retryable=False)
        return str(tid)

    def status(self, remote_id: str) -> base.RemoteStatus:
        j = self._call("GET", "/api/v1/jobs/recordInfo?" + urllib.parse.urlencode({"taskId": remote_id}))
        d = j.get("data") or {}
        state = STATE.get(str(d.get("state", "")).lower(), base.RUNNING)
        cost = {"credits": d["creditsConsumed"], "reported_by": "kie"} if d.get("creditsConsumed") is not None else {}
        if state == base.FAILED:
            return base.RemoteStatus(base.FAILED, error=base.ProviderError("provider", f"failCode {d.get('failCode', '?')}: {redact(str(d.get('failMsg', ''))[:200])}"), cost=cost)
        if state == base.SUCCEEDED:
            rj = d.get("resultJson")
            try:
                parsed = json.loads(rj) if isinstance(rj, str) and rj else (rj or {})
            except ValueError:
                parsed = {}
            urls = [u for u in parsed.get("resultUrls", []) if isinstance(u, str)]
            return base.RemoteStatus(base.SUCCEEDED, result_urls=urls, cost=cost)
        return base.RemoteStatus(state, cost=cost)

    def fetch(self, status: base.RemoteStatus, dest_dir: str, stem: str) -> List[str]:
        out = []
        for i, u in enumerate(status.result_urls):
            ext = os.path.splitext(urllib.parse.urlparse(u).path)[1] or ".bin"
            dst = Path(dest_dir) / f"{stem}-{i}{ext}"
            # result URLs live on a CDN: fetched WITHOUT the API key
            req = urllib.request.Request(u, headers={"User-Agent": "motion-lab/1"})
            try:
                with urllib.request.urlopen(req, timeout=120) as r, open(dst, "wb") as f:
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
            except (urllib.error.URLError, OSError) as e:
                raise base.ProviderError("network", redact(f"download failed: {e}"), retryable=True) from None
            out.append(str(dst))
        return out
