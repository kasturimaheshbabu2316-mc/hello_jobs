"""
Job Agent - CLI entry point.

Usage:
    python -m job_agent.main "Python Developer"
"""

import sys

from .scrapers import NaukriScraper, RemoteOKScraper, LinkedInScraper
from .utils import deduplicate, write_jobs_to_csv


def run(job_title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  Job Agent - searching for: {job_title}")
    print(f"{'='*60}\n")

    scrapers = [
        NaukriScraper(),
        RemoteOKScraper(),
        LinkedInScraper(),
    ]

    all_jobs: list[dict] = []
    for scraper in scrapers:
        try:
            jobs = scraper.scrape(job_title)
            all_jobs.extend(jobs)
        except Exception as exc:
            print(f"[{scraper.SOURCE_NAME}] Scraper error: {exc}")

    print(f"\nTotal raw results: {len(all_jobs)}")

    unique_jobs = deduplicate(all_jobs)
    print(f"After deduplication: {len(unique_jobs)}")

    if unique_jobs:
        path = write_jobs_to_csv(unique_jobs)
        print(f"\nResults saved to {path}")
    else:
        print("\nNo jobs found. Try a different search term.")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m job_agent.main <job_title>")
        print('Example: python -m job_agent.main "Python Developer"')
        sys.exit(1)

    job_title = " ".join(sys.argv[1:])
    run(job_title)


if __name__ == "__main__":
    main()
