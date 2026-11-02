"""Credentials: environment variables only, never stored, never logged.

A provider declares the NAME of its variable (capabilities.auth.env_var). `get_secret` reads it at
call time. Everything that is written to disk or printed goes through `redact`, which removes the
literal value of every secret that has been read in this process plus common token shapes, so a
provider error body that echoes a key cannot leak it into a job record or a log.
"""
from __future__ import annotations

import os
import re
from typing import Optional, Set

_SEEN: Set[str] = set()
_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"(?i)((?:api[_-]?key|token|secret|authorization)\"?\s*[:=]\s*\"?)[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
]


class MissingSecret(RuntimeError):
    """Raised when a provider's credential variable is unset; carries only the variable NAME."""

    def __init__(self, env_var: str):
        super().__init__(f"environment variable {env_var} is not set")
        self.env_var = env_var


def get_secret(env_var: str) -> str:
    v = os.environ.get(env_var)
    if not v:
        raise MissingSecret(env_var)
    _SEEN.add(v)
    return v


def has_secret(env_var: Optional[str]) -> bool:
    return bool(env_var and os.environ.get(env_var))


def redact(text: str) -> str:
    if not text:
        return text
    for s in sorted(_SEEN, key=len, reverse=True):
        if s and len(s) >= 6:
            text = text.replace(s, "[REDACTED]")
    for p in _PATTERNS:
        text = p.sub(lambda m: (m.group(1) if m.lastindex else "") + "[REDACTED]", text)
    return text
