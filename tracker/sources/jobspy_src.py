"""Indeed, LinkedIn, Glassdoor and Google Jobs, through the open-source JobSpy library.

These sites discourage automated access, so results vary from day to day. Every
site and search runs separately, and any failure is logged and skipped.
"""
from __future__ import annotations

import math
import time

from .. import config
from ..models import RawJob
from . import money, parse_date


def _job_type(value) -> str | None:
    v = str(value or "").lower()
    if "part" in v:
        return "parttime"
    if "full" in v:
        return "fulltime"
    if "contract" in v or "temporary" in v:
        return "contract"
    return None


def _val(row, key, default=""):
    v = row.get(key, default)
    if v is None:
        return default
    if isinstance(v, float) and math.isnan(v):
        return default
    return v


def fetch(log) -> list[RawJob]:
    try:
        from jobspy import scrape_jobs
    except Exception as exc:  # library missing or broken
        log.error("jobspy", f"library not available: {exc}")
        return []

    jobs: list[RawJob] = []
    for bucket, spec in config.SEARCHES.items():
        for term in spec["terms"]:
            for site in config.JOBSPY_SITES:
                kwargs = dict(
                    site_name=[site],
                    search_term=term,
                    location=spec["location"],
                    results_wanted=config.JOBSPY_RESULTS_PER_SEARCH,
                    hours_old=config.HOURS_OLD,
                    country_indeed="Canada",
                    description_format="markdown",
                    verbose=0,
                )
                if spec.get("distance_miles"):
                    kwargs["distance"] = spec["distance_miles"]
                if site == "google":
                    kwargs["google_search_term"] = f"{term} jobs near {spec['location']} since 3 days ago"
                try:
                    df = scrape_jobs(**kwargs)
                except Exception as exc:
                    log.error(f"jobspy:{site}", f"'{term}': {str(exc)[:160]}")
                    time.sleep(2)
                    continue
                n = 0
                for row in df.to_dict("records"):
                    title = _val(row, "title")
                    if not title:
                        continue
                    jobs.append(RawJob(
                        title=str(title),
                        company=str(_val(row, "company")),
                        location=str(_val(row, "location")),
                        url=str(_val(row, "job_url_direct") or _val(row, "job_url")),
                        description=str(_val(row, "description")),
                        source=site,
                        bucket=bucket,
                        job_type=_job_type(_val(row, "job_type")),
                        date_posted=parse_date(_val(row, "date_posted", None)),
                        salary=money(_val(row, "min_amount", None), _val(row, "max_amount", None),
                                     _val(row, "interval", None)),
                        is_remote=bool(_val(row, "is_remote", False)),
                    ))
                    n += 1
                log.count(site, n)
                time.sleep(1.5 if site != "linkedin" else 4)
    return jobs
