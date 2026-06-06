# Project Context: Multi-Source Job Aggregation Agent

## 1. Problem Statement

We want a **job agent** that, given a set of relevant job titles/keywords, searches
multiple job platforms, collects matching job postings, de-duplicates them, and stores
the consolidated results in a **CSV file**.

The agent should be runnable on demand (and later, on a schedule) so the user always has
an up-to-date spreadsheet of relevant openings across the sources they care about.

## 2. Sources to Cover

| Source | URL | Access method | Difficulty | Notes |
|---|---|---|---|---|
| **Naukri** | https://www.naukri.com | Internal JSON API (`https://www.naukri.com/jobapi/v3/search`) | Hard | Requires specific headers (`appid`, `systemid`, etc.); strong anti-bot. HTML scraping is unreliable because listings are rendered client-side. |
| **RemoteOK** | https://remoteok.com | Public JSON API (`https://remoteok.com/api`) | Easy | Returns all recent remote jobs as JSON; filter client-side by title/keyword. Free, no auth. |
| **Wellfound** (formerly AngelList Talent) | https://wellfound.com | Internal GraphQL API | Hard | Cloudflare-protected; may require a browser session (Playwright) or authenticated cookies. |

> The three sources differ a lot in how accessible they are. RemoteOK is trivial via its
> public API. Naukri and Wellfound are protected and will likely need either their internal
> APIs with the right headers, or a real browser (Playwright via the existing Chrome/CDP
> setup) to render and extract listings.

## 3. Goal / Desired Outcome

- **Input:** a configurable list of job titles / keywords (e.g. `["Software Engineer",
  "DevOps Engineer", "Data Engineer"]`) and optional filters (location, remote-only,
  experience).
- **Process:** query each enabled source for each keyword, normalize the results into a
  common schema, and de-duplicate.
- **Output:** a single consolidated **CSV** of jobs (one row per unique job).

## 4. Output Schema (CSV columns)

| Column | Description |
|---|---|
| `source` | `naukri` / `remoteok` / `wellfound` |
| `title` | Job title |
| `company` | Company name |
| `location` | Location (or `Remote`) |
| `link` | Direct URL to the posting |
| `posted_date` | When the job was posted (if available) |
| `salary` | Salary / compensation (if available) |
| `tags` | Skills / tags (if available) |
| `scraped_at` | Timestamp when the agent fetched the row |

De-duplication key: normalized (`title` + `company` + `source`) or the canonical job
`link` when present.

## 5. Current State of the Repo

- `scrape.py` — a first prototype that fetches a **single hardcoded URL** with `requests`
  + `BeautifulSoup` and writes `jobs.csv`, a `.txt` dump, and an HTML report. It currently
  points at a LinkedIn article URL while using Naukri-style CSS selectors
  (`.srp-jobtuple-wrapper`, `a.title`, `a.comp-name`, `.locWdth`), so it does not yet
  return real results.
- `job.csv` — sample/placeholder rows (dummy companies and links), not real scraped data.
- `selector.md` — documents the Naukri CSS selectors and the company-name fallback logic.
- `README.md` — placeholder only.

In short: there is a single-source scraping prototype. This project turns it into a
multi-source, keyword-driven aggregation agent.

## 6. Proposed Architecture

```
job_agent/
  config.py / config.yaml   # job titles, keywords, filters, enabled sources
  sources/
    base.py                 # JobSource interface -> search(keyword) -> list[Job]
    remoteok.py             # public API client (start here, easiest)
    naukri.py               # internal API or Playwright fallback
    wellfound.py            # GraphQL/Playwright fallback
  models.py                 # Job dataclass = the CSV schema above
  dedupe.py                 # de-duplication logic
  writer.py                 # write/append consolidated CSV
  main.py                   # orchestration: for each source x keyword -> collect -> dedupe -> write
```

Each source implements a common `JobSource` interface so adding/removing platforms is
isolated and testable.

## 7. Key Challenges & Considerations

- **Anti-scraping:** Naukri and Wellfound actively block bots. Plan: prefer official/internal
  JSON APIs with correct headers; fall back to Playwright (the environment already exposes
  Chrome via CDP) for rendering when needed.
- **Rate limiting / politeness:** add delays and retries; cache responses during development.
- **Schema drift:** site HTML/selectors change; keep selectors centralized (see
  `selector.md`) and validate output.
- **Terms of Service:** scraping may violate site ToS. Prefer official APIs where available;
  for personal/educational use, throttle requests and avoid heavy load.
- **Incremental output:** support append mode + de-dupe so repeated runs grow one CSV
  instead of overwriting.

## 8. Tech Stack

- **Python 3** (existing).
- `requests` for HTTP APIs, `beautifulsoup4` for HTML parsing (already used).
- `playwright` (optional) for JS-heavy / protected sources.
- `csv` (stdlib) for output; optionally `pandas` for easier de-dup/merge.

## 9. Proposed Next Steps

1. Implement the **RemoteOK** source first via its public API (quickest win, real data).
2. Define the `Job` model + consolidated CSV writer with de-duplication.
3. Add a config for job titles/keywords and filters.
4. Implement **Naukri** via its internal search API (with required headers), Playwright as fallback.
5. Implement **Wellfound** (likely Playwright + authenticated session).
6. Add a single `main.py` entry point to run all enabled sources and produce one CSV.

## 10. Open Questions

- How should target job titles/keywords be provided — a config file, CLI args, or hardcoded
  list to start?
- Any location / remote-only / experience-level filters required?
- Should repeated runs **append + de-dupe** into one growing CSV, or overwrite each run?
- For Naukri/Wellfound, can the user provide logged-in session cookies if the APIs require auth?

---

## 11. Implementation Code

Below is the full source code for the job agent.

### `config.yaml`

```yaml
# Job agent configuration.
# Edit the keywords/sources/filters, then run:
#   python -m job_agent.main --config config.yaml

keywords:
  - Software Engineer
  - DevOps Engineer
  - Data Engineer

# Sources to query. Available: remoteok, naukri, wellfound
sources:
  - remoteok
  - naukri
  - wellfound

filters:
  location: ""        # substring match on job location; "" = any
  remote_only: false  # keep only jobs whose location mentions "remote"

limits:
  per_keyword: 50     # max jobs per keyword per source

output:
  csv_path: jobs.csv
  mode: append        # "append" (de-dupe into existing file) or "overwrite"

request:
  delay_seconds: 1.5  # politeness delay between requests
  timeout: 20
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
```

### `requirements.txt`

```
requests>=2.31
beautifulsoup4>=4.12
PyYAML>=6.0
```

### `job_agent/models.py`

```python
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
```

### `job_agent/config.py`

```python
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
```

### `job_agent/writer.py`

```python
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
```

### `job_agent/sources/base.py`

```python
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
```

### `job_agent/sources/remoteok.py`

```python
"""RemoteOK source.

RemoteOK exposes a public JSON feed at https://remoteok.com/api . The first
element of the array is a legal/metadata object; the rest are job postings.
The feed has no real keyword search, so we fetch it once and filter
client-side by matching the keyword against the title, tags and description.
"""
from __future__ import annotations

import requests

from ..models import Job
from .base import JobSource, SourceError

API_URL = "https://remoteok.com/api"


class RemoteOKSource(JobSource):
    name = "remoteok"

    def __init__(self, config) -> None:
        super().__init__(config)
        self._cache: list[dict] | None = None  # feed is fetched once per run

    def _fetch_feed(self) -> list[dict]:
        if self._cache is not None:
            return self._cache
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "application/json",
        }
        try:
            resp = requests.get(API_URL, headers=headers, timeout=self.config.timeout)
        except requests.RequestException as exc:
            raise SourceError(f"remoteok request failed: {exc}") from exc

        if resp.status_code != 200:
            raise SourceError(f"remoteok returned HTTP {resp.status_code}")

        ctype = resp.headers.get("content-type", "")
        if "application/json" not in ctype:
            # RemoteOK blocks datacenter IPs with an HTML "Disable your VPN" page.
            raise SourceError(
                "remoteok did not return JSON (likely IP/anti-bot block); "
                f"first bytes: {resp.text[:80]!r}"
            )
        try:
            data = resp.json()
        except ValueError as exc:
            raise SourceError(f"remoteok returned invalid JSON: {exc}") from exc

        # Drop the leading legal/metadata object.
        jobs = [item for item in data if isinstance(item, dict) and item.get("id")]
        self._cache = jobs
        return jobs

    def search(self, keyword: str) -> list[Job]:
        feed = self._fetch_feed()
        needle = keyword.lower().strip()
        results: list[Job] = []
        for item in feed:
            title = (item.get("position") or "").strip()
            tags = item.get("tags") or []
            haystack = " ".join(
                [title, " ".join(tags), (item.get("description") or "")]
            ).lower()
            if needle and needle not in haystack:
                continue
            results.append(
                Job(
                    source=self.name,
                    title=title,
                    company=(item.get("company") or "").strip(),
                    location=(item.get("location") or "Remote").strip(),
                    link=(item.get("url") or item.get("apply_url") or "").strip(),
                    posted_date=(item.get("date") or "").strip(),
                    salary=self._format_salary(item),
                    tags=", ".join(tags),
                )
            )
            if len(results) >= self.config.per_keyword:
                break
        return results

    @staticmethod
    def _format_salary(item: dict) -> str:
        lo, hi = item.get("salary_min"), item.get("salary_max")
        if lo and hi:
            return f"${lo:,} - ${hi:,}"
        if lo:
            return f"${lo:,}+"
        return ""
```

### `job_agent/sources/naukri.py`

```python
"""Naukri source.

Naukri renders listings client-side and exposes an internal JSON search API at
``/jobapi/v3/search``. It requires app-identifying headers (``appid``,
``systemid``) and is protected by anti-bot measures: requests from datacenter
IPs are challenged with ``{"message": "recaptcha required"}`` (HTTP 406). From a
residential IP / proxy with the headers below it returns JSON we can parse.
"""
from __future__ import annotations

import requests

from ..models import Job
from .base import JobSource, SourceError

API_URL = "https://www.naukri.com/jobapi/v3/search"


class NaukriSource(JobSource):
    name = "naukri"

    def _headers(self) -> dict[str, str]:
        return {
            "authority": "www.naukri.com",
            "accept": "application/json",
            "appid": "109",
            "systemid": "Naukri",
            "clientid": "d3skt0p",
            "gid": "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
            "user-agent": self.config.user_agent,
            "referer": "https://www.naukri.com/",
        }

    def search(self, keyword: str) -> list[Job]:
        params = {
            "noOfResults": self.config.per_keyword,
            "urlType": "search_by_keyword",
            "searchType": "adv",
            "keyword": keyword,
            "k": keyword,
            "seoKey": keyword.lower().replace(" ", "-") + "-jobs",
            "src": "jobsearchDesk",
        }
        if self.config.location:
            params["location"] = self.config.location
            params["l"] = self.config.location

        try:
            resp = requests.get(
                API_URL,
                params=params,
                headers=self._headers(),
                timeout=self.config.timeout,
            )
        except requests.RequestException as exc:
            raise SourceError(f"naukri request failed: {exc}") from exc

        if resp.status_code == 406 or "recaptcha" in resp.text.lower():
            raise SourceError(
                "naukri requires a recaptcha (datacenter IP blocked); "
                "use a residential proxy/VPN"
            )
        if resp.status_code != 200:
            raise SourceError(f"naukri returned HTTP {resp.status_code}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise SourceError(f"naukri returned invalid JSON: {exc}") from exc

        results: list[Job] = []
        for item in data.get("jobDetails", []) or []:
            ph = {p.get("type"): p.get("label", "") for p in item.get("placeholders", []) or []}
            jd_url = item.get("jdURL", "") or ""
            link = jd_url if jd_url.startswith("http") else f"https://www.naukri.com{jd_url}"
            results.append(
                Job(
                    source=self.name,
                    title=(item.get("title") or "").strip(),
                    company=(item.get("companyName") or "").strip(),
                    location=ph.get("location", "").strip(),
                    link=link,
                    posted_date=(item.get("footerPlaceholderLabel") or item.get("createdDate") or "").strip()
                    if not isinstance(item.get("createdDate"), int)
                    else item.get("footerPlaceholderLabel", ""),
                    salary=ph.get("salary", "").strip(),
                    tags=(item.get("tagsAndSkills") or "").strip(),
                )
            )
        return results
```

### `job_agent/sources/wellfound.py`

```python
"""Wellfound (formerly AngelList Talent) source.

Wellfound is a Next.js app behind Cloudflare. Listings are embedded in a
``__NEXT_DATA__`` JSON blob on the search page. Cloudflare blocks plain
``requests`` from datacenter IPs (HTTP 403), so this source typically needs a
real browser session (Playwright via the existing Chrome/CDP) or authenticated
cookies. When the page is reachable, we extract listings from the embedded JSON.
"""
from __future__ import annotations

import json
import re

import requests
from bs4 import BeautifulSoup

from ..models import Job
from .base import JobSource, SourceError

SEARCH_URL = "https://wellfound.com/jobs"
_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.DOTALL
)


class WellfoundSource(JobSource):
    name = "wellfound"

    def _headers(self) -> dict[str, str]:
        return {
            "user-agent": self.config.user_agent,
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
        }

    def search(self, keyword: str) -> list[Job]:
        try:
            resp = requests.get(
                SEARCH_URL,
                params={"q": keyword},
                headers=self._headers(),
                timeout=self.config.timeout,
            )
        except requests.RequestException as exc:
            raise SourceError(f"wellfound request failed: {exc}") from exc

        if resp.status_code in (403, 429) or "cloudflare" in resp.text.lower()[:2000]:
            raise SourceError(
                "wellfound blocked by Cloudflare (HTTP "
                f"{resp.status_code}); use a browser session or cookies"
            )
        if resp.status_code != 200:
            raise SourceError(f"wellfound returned HTTP {resp.status_code}")

        return self.parse_html(resp.text)

    def parse_html(self, html: str) -> list[Job]:
        match = _NEXT_DATA_RE.search(html)
        if not match:
            raise SourceError("wellfound: __NEXT_DATA__ not found (page structure changed)")
        try:
            data = json.loads(match.group(1))
        except ValueError as exc:
            raise SourceError(f"wellfound: failed to parse embedded JSON: {exc}") from exc

        results: list[Job] = []
        for node in self._walk_listings(data):
            results.append(node)
            if len(results) >= self.config.per_keyword:
                break
        return results

    def _walk_listings(self, obj) -> list[Job]:
        """Recursively collect objects that look like job listings."""
        found: list[Job] = []

        def visit(o) -> None:
            if isinstance(o, dict):
                typename = str(o.get("__typename", ""))
                if "JobListing" in typename and o.get("title"):
                    found.append(self._to_job(o))
                for v in o.values():
                    visit(v)
            elif isinstance(o, list):
                for v in o:
                    visit(v)

        visit(obj)
        return found

    def _to_job(self, o: dict) -> Job:
        startup = o.get("startup") or o.get("company") or {}
        company = startup.get("name", "") if isinstance(startup, dict) else str(startup)
        slug = o.get("slug") or o.get("id") or ""
        link = f"https://wellfound.com/jobs/{slug}" if slug else ""
        return Job(
            source=self.name,
            title=str(o.get("title", "")).strip(),
            company=str(company).strip(),
            location=str(o.get("locationNames") or o.get("location") or "").strip(),
            link=link,
            salary=str(o.get("compensation") or o.get("salary") or "").strip(),
            tags="",
        )
```

### `job_agent/main.py`

```python
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
```

### How to Run

```bash
# Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run with config file
python -m job_agent.main --config config.yaml

# Or override via CLI
python -m job_agent.main --keywords "Software Engineer,DevOps Engineer" \
    --sources remoteok,naukri --out jobs.csv --mode overwrite
```
