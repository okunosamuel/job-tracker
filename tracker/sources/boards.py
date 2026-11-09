"""Greenhouse and Lever job boards (used by many tech companies). Both have open feeds."""
from __future__ import annotations

from .. import config
from ..classify import role_tags
from ..models import RawJob
from . import parse_date, session


def fetch(log) -> list[RawJob]:
    s = session()
    jobs: list[RawJob] = []
    for company, token in config.GREENHOUSE_BOARDS:
        try:
            r = s.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
                      params={"content": "true"}, timeout=30)
            r.raise_for_status()
            items = r.json().get("jobs", [])
        except Exception as exc:
            log.error(f"greenhouse:{company}", str(exc)[:160])
            continue
        n = 0
        for it in items:
            title = it.get("title", "")
            if not role_tags(title, ""):
                continue
            jobs.append(RawJob(title=title, company=company,
                               location=(it.get("location") or {}).get("name", ""),
                               url=it.get("absolute_url", ""), description=it.get("content", ""),
                               source="greenhouse", date_posted=parse_date(it.get("updated_at")),
                               reference=str(it.get("id", ""))))
            n += 1
        log.count(f"greenhouse:{company}", n)

    for company, token in config.LEVER_BOARDS:
        try:
            r = s.get(f"https://api.lever.co/v0/postings/{token}", params={"mode": "json"}, timeout=30)
            r.raise_for_status()
            items = r.json()
        except Exception as exc:
            log.error(f"lever:{company}", str(exc)[:160])
            continue
        n = 0
        for it in items:
            title = it.get("text", "")
            if not role_tags(title, ""):
                continue
            cat = it.get("categories") or {}
            commitment = (cat.get("commitment") or "").lower()
            jobs.append(RawJob(title=title, company=company, location=cat.get("location", ""),
                               url=it.get("hostedUrl", ""),
                               description=it.get("descriptionPlain", ""), source="lever",
                               job_type="parttime" if "part" in commitment else
                                        ("fulltime" if "full" in commitment else None),
                               date_posted=parse_date(it.get("createdAt")),
                               reference=str(it.get("id", ""))))
            n += 1
        log.count(f"lever:{company}", n)
    return jobs
