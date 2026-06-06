import time
import urllib.parse
import requests
from bs4 import BeautifulSoup

from .base import BaseScraper


class LinkedInScraper(BaseScraper):
    """Scrape public (guest) LinkedIn job listings."""

    SOURCE_NAME = "linkedin"
    SEARCH_URL = (
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    )

    def _build_params(self, job_title: str, start: int = 0) -> dict:
        return {
            "keywords": job_title,
            "location": "",
            "start": start,
        }

    def scrape(self, job_title: str) -> list[dict]:
        params = self._build_params(job_title)
        url = f"{self.SEARCH_URL}?{urllib.parse.urlencode(params)}"
        print(f"[LinkedIn] Fetching {url}")

        try:
            response = requests.get(url, headers=self.HEADERS, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[LinkedIn] Request failed: {exc}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("li")
        print(f"[LinkedIn] Found {len(cards)} list items")

        results: list[dict] = []
        for card in cards:
            title_elem = card.select_one("h3.base-search-card__title")
            company_elem = card.select_one("h4.base-search-card__subtitle")
            location_elem = card.select_one("span.job-search-card__location")
            link_elem = card.select_one("a.base-card__full-link")

            if not title_elem:
                continue

            results.append(
                {
                    "source": self.SOURCE_NAME,
                    "title": title_elem.text.strip(),
                    "company": company_elem.text.strip() if company_elem else "",
                    "location": location_elem.text.strip() if location_elem else "",
                    "link": link_elem["href"].split("?")[0] if link_elem else "",
                }
            )

        print(f"[LinkedIn] Matched {len(results)} jobs")
        time.sleep(1)
        return results
