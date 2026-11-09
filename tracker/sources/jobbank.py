"""Job Bank, the Government of Canada job board (jobbank.gc.ca)."""
from __future__ import annotations

import re
import time

from bs4 import BeautifulSoup

from .. import config
from ..models import RawJob
from . import parse_date, session

BASE = "https://www.jobbank.gc.ca"
LOCATIONS = {"fulltime": "Ontario", "parttime": "Oshawa, ON", "graduate": ""}


def _parse(html: str, bucket: str) -> list[RawJob]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.select("a[href*='/jobsearch/jobposting/']"):
        title_el = a.select_one(".noctitle") or a.select_one("h3") or a
        title = title_el.get_text(" ", strip=True)
        title = re.sub(r"^(New|Updated)\s+", "", title).strip()
        def pick(cls):
            el = a.select_one(f".{cls}")
            if not el:
                return ""
            for inv in el.select(".wb-inv"):
                inv.decompose()
            return el.get_text(" ", strip=True)
        href = a.get("href", "").split(";")[0]
        m = re.search(r"/jobposting/(\d+)", href)
        loc = pick("location")
        # Job Bank writes "Toronto (ON)"; make it "Toronto, ON"
        loc = re.sub(r"\s*\((\w{2})\)", r", \1", loc)
        salary = re.sub(r"^Salary:?\s*", "", pick("salary"))
        out.append(RawJob(
            title=title, company=pick("business"), location=loc,
            url=BASE + href if href.startswith("/") else href,
            source="jobbank", bucket=bucket, salary=salary[:120],
            date_posted=parse_date(pick("date")),
            reference=m.group(1) if m else "",
            job_type="parttime" if re.search(r"part[- ]time", a.get_text(" "), re.I) else None,
        ))
    return out


def fetch(log) -> list[RawJob]:
    if not config.JOBBANK_ENABLED:
        return []
    s = session()
    jobs: list[RawJob] = []
    for bucket, spec in config.SEARCHES.items():
        for term in spec["terms"]:
            params = {"searchstring": term, "sort": "D", "fage": "7"}
            if LOCATIONS.get(bucket):
                params["locationstring"] = LOCATIONS[bucket]
            if bucket == "parttime":
                params["fpt"] = "2"   # part-time filter (ignored if Job Bank changes it)
            try:
                r = s.get(f"{BASE}/jobsearch/jobsearch", params=params, timeout=30)
                r.raise_for_status()
                found = _parse(r.text, bucket)
            except Exception as exc:
                log.error("jobbank", f"'{term}': {str(exc)[:160]}")
                continue
            jobs.extend(found)
            log.count("jobbank", len(found))
            time.sleep(1.5)
    return jobs
