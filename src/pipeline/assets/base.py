"""Provider interface and shared types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

QUEUED, SUBMITTED, RUNNING, SUCCEEDED, FAILED, TIMED_OUT, CANCELLED = (
    "queued", "submitted", "running", "succeeded", "failed", "timed_out", "cancelled")
TERMINAL = {SUCCEEDED, FAILED, TIMED_OUT, CANCELLED}


class ProviderError(Exception):
    """A provider failure with a machine-readable kind and a retry hint (matches asset-spec job.error)."""

    def __init__(self, kind: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.kind, self.retryable = kind, retryable


@dataclass
class RemoteStatus:
    state: str                                   # one of the job states above (never 'queued' after submit)
    result_urls: List[str] = field(default_factory=list)
    result_paths: List[str] = field(default_factory=list)
    error: Optional[ProviderError] = None
    cost: Dict[str, Any] = field(default_factory=dict)  # reported by the provider after the fact, never estimated
    progress: Optional[float] = None


class Provider(ABC):
    """Adapter contract. Implementations must be safe to construct without credentials: a missing
    credential is reported by `available()` and by submit() raising ProviderError('auth')."""

    name = "base"

    @abstractmethod
    def capabilities(self) -> Dict[str, Any]:
        """A document valid against asset-spec #/definitions/capabilities."""

    @abstractmethod
    def available(self) -> Optional[str]:
        """None when usable now, otherwise a short reason (missing credential, offline...)."""

    @abstractmethod
    def submit(self, task: str, request: Dict[str, Any]) -> str:
        """Start work and return a remote id. May complete synchronously (local providers)."""

    @abstractmethod
    def status(self, remote_id: str) -> RemoteStatus:
        """Non-blocking status of a submitted job."""

    @abstractmethod
    def fetch(self, status: RemoteStatus, dest_dir: str, stem: str) -> List[str]:
        """Materialise results as local files under dest_dir; returns their paths."""

    def cancel(self, remote_id: str) -> None:  # optional
        return None
