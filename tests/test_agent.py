"""Offline tests for the job agent (no network required).

Live scraping is often blocked by anti-bot IP checks, so these tests exercise
the parsing / filtering / de-duplication logic against fixed sample payloads.
"""
from __future__ import annotations

import json
from pathlib import Path

from job_agent.config import Config
from job_agent.models import Job
from job_agent.sources.remoteok import RemoteOKSource
from job_agent.sources.wellfound import WellfoundSource
from job_agent.writer import write_jobs

SAMPLE_REMOTEOK = [
    {"legal": "RemoteOK legal notice"},
    {
        "id": "1",
        "position": "Senior Python Engineer",
        "company": "Acme",
        "location": "Worldwide",
        "url": "https://remoteok.com/remote-jobs/1",
        "date": "2024-01-01T00:00:00+00:00",
        "tags": ["python", "backend"],
        "salary_min": 100000,
        "salary_max": 150000,
        "description": "Build APIs",
    },
    {
        "id": "2",
        "position": "Marketing Lead",
        "company": "BetaCo",
        "location": "Remote",
        "url": "https://remoteok.com/remote-jobs/2",
        "tags": ["marketing"],
        "description": "Growth",
    },
]


def _config(**kw) -> Config:
    base = dict(keywords=["python"], sources=["remoteok"], per_keyword=50)
    base.update(kw)
    return Config(**base)


def test_remoteok_parse_and_keyword_filter():
    src = RemoteOKSource(_config())
    src._cache = [i for i in SAMPLE_REMOTEOK if i.get("id")]
    jobs = src.search("python")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Senior Python Engineer"
    assert job.company == "Acme"
    assert job.salary == "$100,000 - $150,000"
    assert job.tags == "python, backend"
    assert job.source == "remoteok"


def test_remoteok_keyword_no_match():
    src = RemoteOKSource(_config())
    src._cache = [i for i in SAMPLE_REMOTEOK if i.get("id")]
    assert src.search("rust") == []


def test_writer_dedupes_within_batch_and_file(tmp_path: Path):
    out = tmp_path / "jobs.csv"
    j = Job(source="remoteok", title="Eng", company="Acme", link="https://x/1")
    dup = Job(source="remoteok", title="Eng", company="Acme", link="https://x/1")
    other = Job(source="naukri", title="Eng2", company="Beta", link="https://x/2")

    stats = write_jobs([j, dup, other], str(out), mode="append")
    assert stats == {"input": 3, "written": 2, "skipped": 1}

    # Re-running with an overlapping job appends only the new one.
    new = Job(source="naukri", title="Eng3", company="Gamma", link="https://x/3")
    stats2 = write_jobs([j, new], str(out), mode="append")
    assert stats2 == {"input": 2, "written": 1, "skipped": 1}

    lines = out.read_text().strip().splitlines()
    assert lines[0].startswith("source,title,company")
    assert len(lines) == 1 + 3  # header + 3 unique jobs


def test_writer_overwrite_mode(tmp_path: Path):
    out = tmp_path / "jobs.csv"
    write_jobs([Job(source="s", title="a", link="l1")], str(out), mode="append")
    write_jobs([Job(source="s", title="b", link="l2")], str(out), mode="overwrite")
    lines = out.read_text().strip().splitlines()
    assert len(lines) == 2  # header + only the overwrite row
    assert "l2" in lines[1]


def test_wellfound_parse_next_data():
    payload = {
        "props": {
            "x": {
                "__typename": "JobListingSearchResult",
                "title": "Backend Engineer",
                "slug": "backend-engineer-123",
                "startup": {"name": "StartupX"},
                "locationNames": "Remote",
                "compensation": "$120k",
            }
        }
    }
    html = (
        '<html><body><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(payload)
        + "</script></body></html>"
    )
    src = WellfoundSource(_config(sources=["wellfound"]))
    jobs = src.parse_html(html)
    assert len(jobs) == 1
    assert jobs[0].title == "Backend Engineer"
    assert jobs[0].company == "StartupX"
    assert jobs[0].link == "https://wellfound.com/jobs/backend-engineer-123"
