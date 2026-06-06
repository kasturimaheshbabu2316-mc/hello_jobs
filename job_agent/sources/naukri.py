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
