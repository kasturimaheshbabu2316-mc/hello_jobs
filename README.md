# hello_jobs

A multi-source **job aggregation agent**. Given a set of job titles/keywords, it
searches **RemoteOK**, **Naukri**, and **Wellfound**, normalizes the results into a
common schema, de-duplicates them, and writes a single consolidated **CSV**.

See [`context.md`](context.md) for the full project context and design.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Configure

Edit [`config.yaml`](config.yaml) — set your `keywords`, which `sources` to query,
optional `filters` (location / remote-only), and the output CSV path/mode.

## Run

```bash
# use config.yaml
python -m job_agent.main --config config.yaml

# or override on the CLI
python -m job_agent.main --keywords "Software Engineer,DevOps Engineer" \
    --sources remoteok,naukri --out jobs.csv --mode overwrite
```

Output columns: `source, title, company, location, link, posted_date, salary, tags, scraped_at`.
Repeated runs in `append` mode de-duplicate against the existing CSV (by link, else
source+title+company+location).

## Sources & anti-bot notes

| Source | Access | Notes |
|---|---|---|
| RemoteOK | public JSON API (`/api`) | Blocks datacenter IPs with a "Disable your VPN" page. |
| Naukri | internal JSON API (`/jobapi/v3/search`) | Needs `appid`/`systemid` headers; datacenter IPs get `recaptcha required` (HTTP 406). |
| Wellfound | `__NEXT_DATA__` on the search page | Cloudflare-protected (HTTP 403); needs a browser session/cookies. |

> All three actively block datacenter / cloud IPs. To fetch live data, run the agent
> from a residential network or via a residential proxy/VPN. Each source fails
> independently with a clear `[warn]` message, so the agent still produces a CSV from
> whatever sources succeed.

## Tests

```bash
pip install pytest
python -m pytest tests/ -q
```

Tests run fully offline against sample payloads (parsing, filtering, de-duplication,
CSV append/overwrite).

## Layout

```
job_agent/
  config.py        # load config.yaml + CLI overrides
  models.py        # Job dataclass = CSV schema
  writer.py        # consolidated CSV writer with de-dupe
  sources/
    base.py        # JobSource interface
    remoteok.py
    naukri.py
    wellfound.py
  main.py          # orchestrator + CLI entry point
config.yaml
tests/
```
