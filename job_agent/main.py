"""Job agent entry point.

Runs each enabled source for each configured keyword, applies filters,
de-duplicates, and writes a single consolidated CSV.

Usage:
    python -m job_agent.main --config config.yaml
    python -m job_agent.main --keywords "Software Engineer,DevOps Engineer"
"""
from __future__ import annotations

import argparse
import time

from .config import Config
from .models import Job
from .sources.base import JobSource, SourceError
from .sources.naukri import NaukriSource
from .sources.remoteok import RemoteOKSource
from .sources.wellfound import WellfoundSource
from .writer import write_jobs

SOURCE_REGISTRY: dict[str, type[JobSource]] = {
    "remoteok": RemoteOKSource,
    "naukri": NaukriSource,
    "wellfound": WellfoundSource,
}


def _passes_filters(job: Job, config: Config) -> bool:
    if config.remote_only and "remote" not in job.location.lower():
        return False
    if config.location and config.location.lower() not in job.location.lower():
        return False
    return True


def run(config: Config) -> list[Job]:
    collected: list[Job] = []
    for source_name in config.sources:
        source_cls = SOURCE_REGISTRY.get(source_name)
        if source_cls is None:
            print(f"[warn] unknown source '{source_name}', skipping")
            continue
        source = source_cls(config)
        for keyword in config.keywords:
            try:
                jobs = source.search(keyword)
            except SourceError as exc:
                print(f"[warn] {source_name} '{keyword}': {exc}")
                continue
            kept = [j for j in jobs if _passes_filters(j, config)]
            print(f"[info] {source_name} '{keyword}': {len(kept)} jobs")
            collected.extend(kept)
            time.sleep(config.delay_seconds)
    return collected


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Multi-source job aggregation agent")
    p.add_argument("--config", default="config.yaml", help="path to config YAML")
    p.add_argument("--keywords", help="comma-separated keywords (overrides config)")
    p.add_argument("--sources", help="comma-separated sources (overrides config)")
    p.add_argument("--out", help="output CSV path (overrides config)")
    p.add_argument(
        "--mode", choices=["append", "overwrite"], help="CSV write mode (overrides config)"
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    config = Config.load(args.config)

    if args.keywords:
        config.keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if args.sources:
        config.sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    if args.out:
        config.csv_path = args.out
    if args.mode:
        config.mode = args.mode

    if not config.keywords:
        raise SystemExit("No keywords configured. Set 'keywords' in config or use --keywords.")

    jobs = run(config)
    stats = write_jobs(jobs, config.csv_path, config.mode)
    print(
        f"[done] collected={stats['input']} written={stats['written']} "
        f"skipped(dupes)={stats['skipped']} -> {config.csv_path}"
    )


if __name__ == "__main__":
    main()
