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
