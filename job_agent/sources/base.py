"""Common interface and helpers for all job sources."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import Config
from ..models import Job


class SourceError(Exception):
    """Raised when a source cannot return results (blocked, network, parse)."""


class JobSource(ABC):
    """Interface every source must implement.

    A source knows how to take a single keyword and return a list of `Job`s.
    Filtering (location / remote-only) and de-duplication happen in the
    orchestrator so each source stays small and focused.
    """

    #: short identifier, also written to the CSV `source` column
    name: str = "base"

    def __init__(self, config: Config) -> None:
        self.config = config

    @abstractmethod
    def search(self, keyword: str) -> list[Job]:
        """Return jobs matching `keyword`. Raise `SourceError` if unavailable."""
        raise NotImplementedError
