"""Adzuna job search API (free key from developer.adzuna.com)."""
from __future__ import annotations

import os
import time

from .. import config
from ..models import RawJob
from . import money, parse_date, session

API = "https://api.adzuna.com/v1/api/jobs/ca/search/{page}"


def fetch(log) -> list[RawJob]:
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        log.error("adzuna", "skipped: ADZUNA_APP_ID / ADZUNA_APP_KEY not set")
        return []
    s = session()
    jobs: list[RawJob] = []
    calls = 0
    for bucket, spec in config.SEARCHES.items():
        for term in spec["terms"]:
            if calls >= config.ADZUNA_MAX_CALLS:
                log.error("adzuna", f"stopped at {calls} searches to stay inside the free limit")
                return jobs
            calls += 1
            params = {
                "app_id": app_id, "app_key": app_key, "what": term,
                "results_per_page": 50, "max_days_old": max(1, config.HOURS_OLD // 24),
                "sort_by": "date", "content-type": "application/json",
            }
            if spec.get("adzuna_where"):
                params["where"] = spec["adzuna_where"]
            if spec.get("adzuna_distance_km"):
                params["distance"] = spec["adzuna_distance_km"]
            if bucket == "parttime":
                params["part_time"] = 1
            try:
                r = s.get(API.format(page=1), params=params, timeout=30)
                r.raise_for_status()
                results = r.json().get("results", [])
            except Exception as exc:
                log.error("adzuna", f"'{term}': {str(exc)[:160]}")
                continue
            for it in results:
                area = (it.get("location") or {}).get("area") or []
                loc = (it.get("location") or {}).get("display_name", "")
                if len(area) >= 2 and area[1] not in loc:
                    loc = f"{loc}, {area[1]}"
                ct = (it.get("contract_time") or "").replace("_", "")
                jobs.append(RawJob(
                    title=it.get("title", ""),
                    company=(it.get("company") or {}).get("display_name", ""),
                    location=loc,
                    url=it.get("redirect_url", ""),
                    description=it.get("description", ""),
                    source="adzuna",
                    bucket=bucket,
                    job_type=ct if ct in ("fulltime", "parttime") else
                             ("contract" if it.get("contract_type") == "contract" else None),
                    date_posted=parse_date(it.get("created")),
                    salary=money(it.get("salary_min"), it.get("salary_max"), "yearly")
                           if not it.get("salary_is_predicted") == "1" else "",
                    reference=str(it.get("id", "")),
                ))
            log.count("adzuna", len(results))
            time.sleep(3)   # free plan allows about 25 searches a minute; this keeps it near 20
    return jobs
