"""Consolidated CSV output with de-duplication."""
from __future__ import annotations

import csv
from pathlib import Path

from .models import CSV_FIELDS, Job


def _existing_keys(path: Path) -> set[str]:
    """Read dedupe keys already present in an existing CSV."""
    keys: set[str] = set()
    if not path.exists():
        return keys
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            link = (row.get("link") or "").strip().lower()
            if link:
                keys.add(link)
            else:
                keys.add(
                    "|".join(
                        (row.get(k) or "").strip().lower()
                        for k in ("source", "title", "company", "location")
                    )
                )
    return keys


def write_jobs(jobs: list[Job], csv_path: str, mode: str = "append") -> dict[str, int]:
    """Write jobs to CSV, de-duplicating within the batch and against the file.

    Returns counts: {"input", "written", "skipped"}.
    """
    path = Path(csv_path)
    overwrite = mode == "overwrite" or not path.exists()

    seen = set() if overwrite else _existing_keys(path)

    new_rows: list[Job] = []
    for job in jobs:
        key = job.dedupe_key()
        if key in seen:
            continue
        seen.add(key)
        new_rows.append(job)

    path.parent.mkdir(parents=True, exist_ok=True)
    file_mode = "w" if overwrite else "a"
    with path.open(file_mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if overwrite:
            writer.writeheader()
        for job in new_rows:
            writer.writerow(job.to_row())

    return {
        "input": len(jobs),
        "written": len(new_rows),
        "skipped": len(jobs) - len(new_rows),
    }
