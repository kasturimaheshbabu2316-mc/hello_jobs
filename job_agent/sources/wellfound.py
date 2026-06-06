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
