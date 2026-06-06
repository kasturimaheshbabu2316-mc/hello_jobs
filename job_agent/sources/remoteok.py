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
