"""Host lock for scripts that load Kokoro or Chromium themselves.

The 8 GB host runs one heavy job at a time. scripts/session-guard.py owns the lock; this loads it by path
(the filename has a hyphen) so a script can guard itself instead of relying on the caller to remember
`session-guard.py run`. Re-entrant: under `session-guard build` or `studio.py build` it is a no-op.

    with heavy_lock("tts", slug="my-film"):
        synthesise()
"""
import importlib.util
from pathlib import Path
from typing import Optional

_GUARD = Path(__file__).resolve().parent.parent.parent / "scripts" / "session-guard.py"


def heavy_lock(resource: str, slug: Optional[str] = None):
    """Context manager for the shared host lock; resource is 'render', 'tts' or 'analysis'."""
    spec = importlib.util.spec_from_file_location("session_guard", _GUARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.acquire_lock(resource, slug=slug)
