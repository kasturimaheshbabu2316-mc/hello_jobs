"""Configuration loading for the job agent."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class Config:
    keywords: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=lambda: ["remoteok", "naukri", "wellfound"])
    location: str = ""
    remote_only: bool = False
    per_keyword: int = 50
    csv_path: str = "jobs.csv"
    mode: str = "append"  # "append" | "overwrite"
    delay_seconds: float = 1.5
    timeout: int = 20
    user_agent: str = DEFAULT_USER_AGENT

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        path = Path(path)
        data = yaml.safe_load(path.read_text()) or {}

        filters = data.get("filters", {}) or {}
        limits = data.get("limits", {}) or {}
        output = data.get("output", {}) or {}
        request = data.get("request", {}) or {}

        return cls(
            keywords=list(data.get("keywords", []) or []),
            sources=list(data.get("sources", []) or cls.sources),
            location=str(filters.get("location", "") or ""),
            remote_only=bool(filters.get("remote_only", False)),
            per_keyword=int(limits.get("per_keyword", 50)),
            csv_path=str(output.get("csv_path", "jobs.csv")),
            mode=str(output.get("mode", "append")),
            delay_seconds=float(request.get("delay_seconds", 1.5)),
            timeout=int(request.get("timeout", 20)),
            user_agent=str(request.get("user_agent", DEFAULT_USER_AGENT)),
        )
