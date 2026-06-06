import csv
import os
from datetime import datetime, timezone


FIELDNAMES = ["source", "title", "company", "location", "link", "scraped_at"]


def write_jobs_to_csv(jobs: list[dict], filepath: str = "jobs_output.csv") -> str:
    """Write job listings to a CSV file. Returns the absolute path written."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    for job in jobs:
        job.setdefault("scraped_at", now)

    abs_path = os.path.abspath(filepath)
    with open(abs_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(jobs)

    return abs_path


def deduplicate(jobs: list[dict]) -> list[dict]:
    """Remove duplicate jobs based on (title, company, link) tuple."""
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict] = []
    for job in jobs:
        key = (job["title"].lower(), job["company"].lower(), job["link"])
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique
