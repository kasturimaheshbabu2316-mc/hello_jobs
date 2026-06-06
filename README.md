# hello_jobs

A job scraping agent that searches **Naukri**, **RemoteOK**, and **LinkedIn** for job listings and saves the results to a CSV file.

## Quick Start

```bash
pip install -r requirements.txt
python -m job_agent.main "Python Developer"
```

This searches all three platforms for "Python Developer" roles and writes `jobs_output.csv`.

## Sources

| Source    | Method         | Notes                              |
|-----------|----------------|------------------------------------|
| Naukri    | HTML scraping  | India's largest job portal         |
| RemoteOK  | JSON API       | Remote-first jobs; most reliable   |
| LinkedIn  | HTML scraping  | Public guest endpoint; limited set |

## CSV Output

| Column      | Description                              |
|-------------|------------------------------------------|
| `source`    | Platform (naukri / remoteok / linkedin)   |
| `title`     | Job title                                |
| `company`   | Company name                             |
| `location`  | Location or "Remote"                     |
| `link`      | Direct URL to the posting                |
| `scraped_at`| UTC timestamp                            |

## Project Structure

```
job_agent/
  __init__.py
  __main__.py         # allows `python -m job_agent "title"`
  main.py             # CLI entry point & orchestrator
  scrapers/
    __init__.py
    base.py            # Abstract base scraper
    naukri.py          # Naukri.com scraper
    remoteok.py        # RemoteOK JSON API scraper
    linkedin.py        # LinkedIn guest search scraper
  utils.py            # CSV writer & deduplication
context.md            # Problem statement & design doc
requirements.txt      # Python dependencies
```

See [context.md](context.md) for the full problem statement and design rationale.
