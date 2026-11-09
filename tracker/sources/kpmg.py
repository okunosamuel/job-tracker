"""KPMG Canada career site (careers.kpmg.ca), which offers an open jobs feed."""
from __future__ import annotations

import time

from .. import config
from ..models import RawJob
from . import parse_date, session


def _job_type(value) -> str | None:
    v = str(value or "").lower()
    if "part" in v:
        return "parttime"
    if "full" in v or "regular" in v or "permanent" in v:
        return "fulltime"
    if "contract" in v or "temporary" in v:
        return "contract"
    return None


def fetch(log) -> list[RawJob]:
    s = session()
    jobs: list[RawJob] = []
    seen: set[str] = set()
    for term in config.KPMG_TERMS:
        try:
            r = s.get(f"{config.KPMG_BASE}/api/jobs",
                      params={"keywords": term, "limit": 100, "page": 1},
                      headers={"Accept": "application/json, text/plain, */*",
                               "Referer": f"{config.KPMG_BASE}/professionals/jobs"}, timeout=30)
            r.raise_for_status()
            items = r.json().get("jobs", [])
        except Exception as exc:
            log.error("kpmg", f"'{term}': {str(exc)[-300:]}")
            continue
        for it in items:
            d = it.get("data", it)
            key = str(d.get("req_id") or d.get("slug"))
            if key in seen:
                continue
            seen.add(key)
            loc = d.get("full_location") or ", ".join(
                x for x in (d.get("city"), d.get("state"), d.get("country")) if x)
            url = d.get("canonical_url") or d.get("apply_url") or \
                f"{config.KPMG_BASE}/jobs/{d.get('slug')}"
            jobs.append(RawJob(
                title=d.get("title", ""),
                company="KPMG",
                location=loc,
                url=url,
                description=" ".join(str(d.get(k) or "") for k in
                                     ("description", "qualifications", "responsibilities")),
                source="kpmg",
                bucket="",
                job_type=_job_type(d.get("employment_type")),
                date_posted=parse_date(d.get("posted_date") or d.get("create_date")),
                reference=str(d.get("req_id") or ""),
            ))
        time.sleep(1)
    log.count("kpmg", len(seen))
    return jobs
