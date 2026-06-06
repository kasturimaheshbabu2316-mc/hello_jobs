# CSS Selectors used in scrape.py

| Selector | Purpose | Fallback |
|---|---|---|
| `.srp-jobtuple-wrapper` | Job card container | — |
| `a.title` | Job title link | — |
| `a.comp-name` | Company name | Falls back to `.subTitle` text if missing |
| `.subTitle` | Fallback for company name | Used when `a.comp-name` is not found |
| `.locWdth` | Job location | — |

## Fallback Logic

If `a.comp-name` does not exist for a job card, the script extracts the text of `.subTitle` as the company name instead.
