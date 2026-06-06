# Job Agent - Context & Problem Statement

## Problem

Job seekers spend hours manually browsing multiple job portals (Naukri, RemoteOK, LinkedIn) to find relevant openings for their desired role. There is no single unified view of jobs across these platforms, making the search process time-consuming and error-prone (missed listings, duplicates, etc.).

## Solution

Build a **Job Agent** that:

1. Accepts a **job title** (e.g. "Python Developer", "Data Engineer") as input.
2. Scrapes job listings from **three sources**:
   - **Naukri.com** - India's largest job portal (HTML scraping)
   - **RemoteOK** - Remote-first job board (JSON API)
   - **LinkedIn** - Professional network's public job listings (HTML scraping)
3. Normalises results into a common schema and **stores them in a CSV file** (`jobs_output.csv`).

## Output Schema (CSV columns)

| Column     | Description                          |
|------------|--------------------------------------|
| `source`   | Platform name (naukri / remoteok / linkedin) |
| `title`    | Job title                            |
| `company`  | Company name                         |
| `location` | Job location or "Remote"             |
| `link`     | Direct URL to the job posting        |
| `scraped_at` | Timestamp when the job was scraped |

## Architecture

```
job_agent/
  __init__.py
  main.py            # CLI entry point - accepts job title, orchestrates scrapers
  scrapers/
    __init__.py
    base.py           # Abstract base class for scrapers
    naukri.py          # Naukri scraper
    remoteok.py        # RemoteOK scraper (JSON API)
    linkedin.py        # LinkedIn public job scraper
  utils.py            # CSV writer, deduplication, timestamping
```

## Tech Stack

- **Python 3.10+**
- `requests` - HTTP client
- `beautifulsoup4` - HTML parsing (Naukri, LinkedIn)
- `csv` (stdlib) - CSV output
- No heavy frameworks; keep it simple and dependency-light.

## Usage

```bash
pip install -r requirements.txt
python -m job_agent.main "Python Developer"
```

This produces `jobs_output.csv` with all found listings.

## Limitations & Notes

- **Rate limiting**: Job portals may rate-limit or block automated requests. The agent uses polite headers and delays between requests.
- **LinkedIn**: Uses the public guest job search endpoint; results are limited compared to authenticated access.
- **Naukri**: Uses search result page scraping; CSS selectors may break if Naukri redesigns their UI.
- **RemoteOK**: Uses their public JSON API which is the most reliable source.
- This is a scraping tool for personal use; respect each site's terms of service.
