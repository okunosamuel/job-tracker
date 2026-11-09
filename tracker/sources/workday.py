"""Company career sites that run on Workday (most big banks, PwC, insurers)."""
from __future__ import annotations

import re
import time

from .. import config
from ..classify import EXCLUDE_TITLE, role_tags
from ..models import RawJob
from . import parse_date, session


def _time_type(text: str | None) -> str | None:
    t = (text or "").lower()
    if "part" in t:
        return "parttime"
    if "full" in t:
        return "fulltime"
    return None


def fetch(log) -> list[RawJob]:
    s = session()
    jobs: list[RawJob] = []
    for company, host, tenant, site in config.WORKDAY_BOARDS:
        api = f"https://{host}/wday/cxs/{tenant}/{site}"
        seen: set[str] = set()
        board_ok = False
        for term in config.WORKDAY_TERMS:
            try:
                r = s.post(f"{api}/jobs", json={"appliedFacets": {}, "limit": 20, "offset": 0,
                                                "searchText": term}, timeout=30)
                r.raise_for_status()
                postings = r.json().get("jobPostings", []) or []
                board_ok = True
            except Exception as exc:
                log.error(f"workday:{company}", f"'{term}': {str(exc)[:140]}")
                if not board_ok:
                    break   # board itself is unreachable; skip the other terms
                continue
            for p in postings:
                path = p.get("externalPath") or ""
                title = p.get("title") or ""
                if not path or path in seen:
                    continue
                seen.add(path)
                # only open detail pages for titles that could match
                if EXCLUDE_TITLE.search(title) or not (
                        role_tags(title, "") or re.search(r"grad|campus|early career", title, re.I)):
                    continue
                detail = {}
                try:
                    d = s.get(f"{api}{path}", timeout=30)
                    d.raise_for_status()
                    detail = d.json().get("jobPostingInfo", {}) or {}
                except Exception:
                    pass
                loc = detail.get("location") or p.get("locationsText") or ""
                country = (detail.get("country") or {}).get("descriptor", "") if isinstance(
                    detail.get("country"), dict) else ""
                if country and country.lower() not in ("canada",):
                    continue
                if country and "canada" not in loc.lower():
                    loc = f"{loc}, Canada"
                bullets = p.get("bulletFields") or []
                jobs.append(RawJob(
                    title=title,
                    company=company,
                    location=loc,
                    url=detail.get("externalUrl") or f"https://{host}/en-US/{site}{path}",
                    description=detail.get("jobDescription", ""),
                    source="workday",
                    bucket="",
                    job_type=_time_type(detail.get("timeType")),
                    date_posted=parse_date(detail.get("startDate") or p.get("postedOn")),
                    closing_date=parse_date(detail.get("endDate")),
                    reference=detail.get("jobReqId") or (bullets[0] if bullets else ""),
                ))
                time.sleep(0.3)
            time.sleep(0.8)
        log.count(f"workday:{company}", len(seen))
    return jobs
