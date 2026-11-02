"""Manual-import provider: register files the user obtained elsewhere (Veo / Flow downloads, stock, photos).

This is the credential-free path for generated footage (specs/veo-integration.md, Mode 1), now with a
record: prompt, tool, licence and who approved it travel with the file instead of living in a chat.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import base

EXT = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".webm", ".wav", ".mp3", ".svg"}


class ImportProvider(base.Provider):
    name = "import"

    def capabilities(self) -> Dict[str, Any]:
        return {"provider": "import", "summary": "Register an existing local file with provenance. No generation.",
                "tasks": {"import": {"input_formats": sorted(e.lstrip(".") for e in EXT), "requires": ["path"]}},
                "auth": {"method": "manual-import"}, "local": True,
                "verification": {"level": "local", "checked_on": "2026-11-02", "sources": ["tests/test-creative-intelligence.py"]}}

    def available(self) -> Optional[str]:
        return None

    def submit(self, task: str, request: Dict[str, Any]) -> str:
        p = Path(str(request.get("path", ""))).expanduser()
        if not p.is_file():
            raise base.ProviderError("invalid-request", f"file not found: {p}")
        if p.suffix.lower() not in EXT:
            raise base.ProviderError("invalid-request", f"unsupported file type {p.suffix!r}")
        return str(p)

    def status(self, remote_id: str) -> base.RemoteStatus:
        return base.RemoteStatus(base.SUCCEEDED, result_paths=[remote_id])

    def fetch(self, status: base.RemoteStatus, dest_dir: str, stem: str) -> List[str]:
        return list(status.result_paths)
