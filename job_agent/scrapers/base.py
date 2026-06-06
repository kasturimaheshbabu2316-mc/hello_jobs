from abc import ABC, abstractmethod


class BaseScraper(ABC):
    """Abstract base class for all job scrapers."""

    SOURCE_NAME: str = ""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    @abstractmethod
    def scrape(self, job_title: str) -> list[dict]:
        """Return a list of job dicts with keys:
        source, title, company, location, link
        """
