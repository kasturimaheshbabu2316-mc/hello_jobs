"""Data model shared across all job sources."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

# Order here defines the CSV column order.
CSV_FIELDS = [
    "source",
    "title",
    "company",
    "location",
    "link",
    "posted_date",
    "salary",
    "tags",
    "scraped_at",
]


@dataclass
class Job:
    """A single normalized job posting."""

    source: str
    title: str
    company: str = ""
    location: str = ""
    link: str = ""
    posted_date: str = ""
    salary: str = ""
    tags: str = ""
    scraped_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def dedupe_key(self) -> str:
        """Stable identity for de-duplication.

        Prefer the canonical link; fall back to source/title/company/location.
        """
        if self.link:
            return self.link.strip().lower()
        return "|".join(
            part.strip().lower()
            for part in (self.source, self.title, self.company, self.location)
        )

    def to_row(self) -> dict[str, str]:
        return {k: str(v) for k, v in asdict(self).items()}
