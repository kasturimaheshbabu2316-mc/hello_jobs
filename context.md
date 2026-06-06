# Project Context: Multi-Source Job Aggregation Agent

## 1. Problem Statement

We want to build a **job agent** that, given a set of relevant job titles /
keywords, searches multiple job platforms, collects matching job postings, and
stores the consolidated results in a **CSV file**.

The agent should be runnable on demand (and later on a schedule) so the user
always has an up-to-date spreadsheet of relevant openings across the sources
they care about.

## 2. Sources to Cover

The agent must pull jobs from three platforms:

| Source | URL | Access method | Difficulty | Notes |
|---|---|---|---|---|
| **Naukri** | https://www.naukri.com | Internal JSON API (`https://www.naukri.com/jobapi/v3/search`) | Hard | Requires specific headers (`appid`, `systemid`, etc.) and has strong anti-bot protection. Plain HTML scraping is unreliable because listings render client-side. |
| **RemoteOK** | https://remoteok.com | Public JSON API (`https://remoteok.com/api`) | Easy | Returns recent remote jobs as JSON; filter client-side by title/keyword. Free, no auth. Best starting point. |
| **Wellfound** (formerly AngelList Talent) | https://wellfound.com | Internal GraphQL API (`https://wellfound.com/graphql`) | Hard | Cloudflare-protected; likely needs a real browser session (Playwright via the existing Chrome/CDP setup) or authenticated cookies. |

The three sources differ a lot in accessibility. RemoteOK is trivial via its
public API. Naukri and Wellfound are protected and will likely need either their
internal APIs with the right headers, or a real browser to render and extract
listings.

## 3. Goal / Desired Outcome

- **Input:** a configurable list of job titles / keywords (e.g.
  `["Software Engineer", "DevOps Engineer", "Data Engineer"]`) plus optional
  filters (location, remote-only, experience).
- **Process:** query each enabled source for each keyword, normalize results
  into a common schema, and de-duplicate.
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

**De-duplication key:** the canonical job `link` when present, otherwise a
normalized combination of (`title` + `company` + `source`).

## 5. Current State of the Repo

- `scrape.py` — a first prototype that fetches a **single hardcoded URL** with
  `requests` + `BeautifulSoup` and writes `jobs.csv`, a `.txt` dump, and an HTML
  report. It currently points at a LinkedIn article URL while using Naukri-style
  CSS selectors (`.srp-jobtuple-wrapper`, `a.title`, `a.comp-name`, `.locWdth`),
  so it does not yet return real results.
- `job.csv` — sample/placeholder rows (dummy companies and links), not real
  scraped data.
- `selector.md` — documents the Naukri CSS selectors and the company-name
  fallback logic.
- `README.md` — placeholder only.

In short: there is a single-source scraping prototype today. This project turns
it into a multi-source, keyword-driven aggregation agent.

## 6. Proposed Architecture

```
job_agent/
  config.py / config.yaml   # job titles, keywords, filters, enabled sources
  sources/
    base.py                 # JobSource interface -> search(keyword) -> list[Job]
    remoteok.py             # public API client (start here, easiest)
    naukri.py               # internal API or Playwright fallback
    wellfound.py            # GraphQL / Playwright fallback
  models.py                 # Job dataclass = the CSV schema above
  dedupe.py                 # de-duplication logic
  writer.py                 # write / append consolidated CSV
  main.py                   # orchestration: for each source x keyword ->
                            #   collect -> normalize -> dedupe -> write CSV
```

Each source implements a common `JobSource` interface so adding or removing a
platform stays isolated and testable.

## 7. Key Challenges & Considerations

- **Anti-scraping:** Naukri and Wellfound actively block bots. Prefer
  official/internal JSON APIs with correct headers; fall back to Playwright (the
  environment already exposes Chrome via CDP) for rendering when needed.
- **Rate limiting / politeness:** add delays and retries; cache responses during
  development to avoid hammering the sources.
- **Schema drift:** site HTML/selectors change over time; keep selectors
  centralized (see `selector.md`) and validate output.
- **Terms of Service:** scraping may violate a site's ToS. Prefer official APIs
  where available; for personal/educational use, throttle requests and avoid
  heavy load.
- **Incremental output:** support append mode + de-dupe so repeated runs grow a
  single CSV instead of overwriting it.

## 8. Tech Stack

- **Python 3** (existing).
- `requests` for HTTP/JSON APIs, `beautifulsoup4` for any HTML parsing.
- **Playwright** (via the existing Chrome/CDP setup) as a fallback for
  JS-rendered or Cloudflare-protected sources (Naukri, Wellfound).
- Standard-library `csv` for output.

## 9. Milestones

1. **RemoteOK first** — implement the public-API source end to end and write the
   consolidated CSV. This proves the pipeline (search -> normalize -> dedupe ->
   CSV) with the easiest source.
2. **Naukri** — add the internal JSON API client with the required headers; fall
   back to Playwright if blocked.
3. **Wellfound** — add a Playwright-based source to handle Cloudflare/GraphQL.
4. **Orchestration & polish** — config-driven keywords/filters, append + dedupe,
   retries/rate limiting, and (optionally) scheduled runs.
