import json
import re
import time

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper


class NaukriScraper(BaseScraper):
    """Scrape job listings from Naukri.com search results.

    Tries two extraction strategies:
    1. CSS selectors on server-rendered HTML (fastest).
    2. JSON-LD structured data embedded in the page (fallback).

    Note: Naukri heavily relies on client-side rendering.  Results may be
    empty when run from datacenter / cloud IPs.
    """

    SOURCE_NAME = "naukri"
    BASE_URL = "https://www.naukri.com/{keyword}-jobs"

    def _build_url(self, job_title: str) -> str:
        keyword = job_title.strip().lower().replace(" ", "-")
        return self.BASE_URL.format(keyword=keyword)

    def _parse_html(self, soup: BeautifulSoup) -> list[dict]:
        """Strategy 1: parse rendered job cards."""
        job_cards = soup.select(".srp-jobtuple-wrapper")
        results: list[dict] = []
        for card in job_cards:
            title_elem = card.select_one("a.title")
            if not title_elem:
                continue

            company_elem = card.select_one("a.comp-name")
            subtitle_elem = card.select_one(".subTitle")
            location_elem = card.select_one(".locWdth")

            company = ""
            if company_elem:
                company = company_elem.text.strip()
            elif subtitle_elem:
                company = subtitle_elem.text.strip()

            results.append(
                {
                    "source": self.SOURCE_NAME,
                    "title": title_elem.text.strip(),
                    "company": company,
                    "location": location_elem.text.strip() if location_elem else "",
                    "link": title_elem.get("href", ""),
                }
            )
        return results

    def _parse_json_ld(self, soup: BeautifulSoup) -> list[dict]:
        """Strategy 2: extract jobs from JSON-LD script tags."""
        results: list[dict] = []
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue

            items = []
            if isinstance(data, dict) and data.get("@type") == "ItemList":
                items = data.get("itemListElement", [])
            elif isinstance(data, list):
                items = data

            for item in items:
                job = item.get("item", item) if isinstance(item, dict) else {}
                title = job.get("title", job.get("name", ""))
                if not title:
                    continue
                org = job.get("hiringOrganization", {})
                loc = job.get("jobLocation", {})
                address = loc.get("address", {}) if isinstance(loc, dict) else {}
                results.append(
                    {
                        "source": self.SOURCE_NAME,
                        "title": title,
                        "company": org.get("name", "") if isinstance(org, dict) else "",
                        "location": address.get("addressLocality", "")
                        if isinstance(address, dict)
                        else "",
                        "link": job.get("url", ""),
                    }
                )
        return results

    def _parse_inline_json(self, html: str) -> list[dict]:
        """Strategy 3: extract from inline JS data (window.__data__ etc)."""
        results: list[dict] = []
        pattern = re.compile(r'"title"\s*:\s*"([^"]+)".*?"companyName"\s*:\s*"([^"]*)"', re.DOTALL)
        for match in pattern.finditer(html):
            title, company = match.group(1), match.group(2)
            results.append(
                {
                    "source": self.SOURCE_NAME,
                    "title": title,
                    "company": company,
                    "location": "",
                    "link": "",
                }
            )
        return results

    def scrape(self, job_title: str) -> list[dict]:
        url = self._build_url(job_title)
        print(f"[Naukri] Fetching {url}")

        try:
            response = requests.get(url, headers=self.HEADERS, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[Naukri] Request failed: {exc}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        results = self._parse_html(soup)
        if results:
            print(f"[Naukri] Found {len(results)} jobs via HTML selectors")
            time.sleep(1)
            return results

        results = self._parse_json_ld(soup)
        if results:
            print(f"[Naukri] Found {len(results)} jobs via JSON-LD")
            time.sleep(1)
            return results

        results = self._parse_inline_json(response.text)
        if results:
            print(f"[Naukri] Found {len(results)} jobs via inline JSON")
            time.sleep(1)
            return results

        print("[Naukri] No jobs found (page may require JS rendering)")
        time.sleep(1)
        return []
