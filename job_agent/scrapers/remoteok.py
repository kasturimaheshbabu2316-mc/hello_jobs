import time

import requests

from .base import BaseScraper


class RemoteOKScraper(BaseScraper):
    """Scrape job listings from RemoteOK's public JSON API.

    Note: RemoteOK blocks requests from datacenter / VPN IPs.
    Run from a residential IP for best results.
    """

    SOURCE_NAME = "remoteok"
    API_URL = "https://remoteok.com/api"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://remoteok.com/",
    }

    def scrape(self, job_title: str) -> list[dict]:
        print(f"[RemoteOK] Fetching {self.API_URL}")

        try:
            response = requests.get(
                self.API_URL, headers=self.HEADERS, timeout=15
            )
            if response.status_code == 403:
                print(
                    "[RemoteOK] 403 Forbidden - site blocks datacenter/VPN IPs. "
                    "Try running from a residential network."
                )
                return []
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            print(f"[RemoteOK] Request failed: {exc}")
            return []
        except ValueError:
            print("[RemoteOK] Failed to parse JSON response")
            return []

        # First element is a metadata/legal notice object; skip it
        jobs = data[1:] if len(data) > 1 else data

        keywords = job_title.lower().split()
        results: list[dict] = []

        for job in jobs:
            position = job.get("position", "")
            tags = " ".join(job.get("tags", []))
            searchable = f"{position} {tags}".lower()

            if not any(kw in searchable for kw in keywords):
                continue

            slug = job.get("slug", "")
            link = (
                f"https://remoteok.com/remote-jobs/{slug}"
                if slug
                else job.get("url", "")
            )

            results.append(
                {
                    "source": self.SOURCE_NAME,
                    "title": position,
                    "company": job.get("company", ""),
                    "location": job.get("location", "Remote"),
                    "link": link,
                }
            )

        print(f"[RemoteOK] Matched {len(results)} jobs for '{job_title}'")
        time.sleep(1)
        return results
