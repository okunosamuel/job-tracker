"""Deloitte Canada career site (careers.deloitte.ca, SAP SuccessFactors).

The site loads results with JavaScript, so this tries its jobs feed first and its
search service second. If both fail, Deloitte postings still arrive through
LinkedIn, Indeed and Google Jobs.
"""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from .. import config
from ..models import RawJob
from . import parse_date, session


def _from_rss(s, term: str) -> list[RawJob]:
    r = s.get(f"{config.DELOITTE_BASE}/services/rss/job/",
              params={"locale": "en_US", "keywords": term}, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = item.findtext("description") or ""
        # RSS titles look like "Senior Consultant, Cyber (Toronto, ON, CA, M5H 0B3)"
        loc = ""
        m = re.search(r"\(([^()]*,\s*[A-Z]{2}[^()]*)\)\s*$", title)
        if m:
            loc = m.group(1)
            title = title[:m.start()].strip()
        ref = ""
        m2 = re.search(r"/(\d{5,7})(?:-en_US)?/?$", link)
        if m2:
            ref = m2.group(1)
        out.append(RawJob(title=title, company="Deloitte", location=loc, url=link,
                          description=desc, source="deloitte", reference=ref,
                          date_posted=parse_date(item.findtext("pubDate"))))
    return out


def _from_search(s, term: str) -> list[RawJob]:
    body = {"locale": "en_US", "pageNumber": 0, "sortBy": "recent", "keywords": term,
            "location": "", "facetFilters": {}, "brand": "", "skills": [], "categoryId": 0,
            "alertId": "", "rcmCandidateId": ""}
    r = s.post(f"{config.DELOITTE_BASE}/services/recruiting/v1/jobs", json=body, timeout=30,
               headers={"Accept": "application/json"})
    if r.ok and "json" in r.headers.get("content-type", ""):
        out = []
        for res in r.json().get("jobSearchResult", []):
            d = res.get("response", res)
            locs = d.get("jobLocationShort") or d.get("jobLocation") or []
            loc = locs[0] if isinstance(locs, list) and locs else str(locs or "")
            loc = BeautifulSoup(loc, "html.parser").get_text(" ").strip()
            jid = d.get("id")
            slug = d.get("urlTitle") or ""
            out.append(RawJob(
                title=d.get("unifiedStandardTitle") or d.get("title") or "",
                company="Deloitte", location=loc,
                url=f"{config.DELOITTE_BASE}/job/{slug}/{jid}-en_US/",
                source="deloitte", reference=str(jid or ""),
                date_posted=parse_date(d.get("unifiedStandardStart")),
            ))
        return out
    # older layout: server-rendered search page
    r = s.get(f"{config.DELOITTE_BASE}/search/", params={"q": term, "locale": "en_US",
              "sortColumn": "referencedate", "sortDirection": "desc"}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for row in soup.select("tr.data-row"):
        a = row.select_one("a.jobTitle-link")
        if not a:
            continue
        loc = row.select_one(".jobLocation")
        dt = row.select_one(".jobDate")
        href = a.get("href", "")
        out.append(RawJob(title=a.get_text(strip=True), company="Deloitte",
                          location=loc.get_text(" ", strip=True) if loc else "",
                          url=href if href.startswith("http") else config.DELOITTE_BASE + href,
                          source="deloitte",
                          date_posted=parse_date(dt.get_text(strip=True) if dt else None)))
    return out


def fetch(log) -> list[RawJob]:
    s = session()
    jobs: list[RawJob] = []
    for term in config.DELOITTE_TERMS:
        found: list[RawJob] = []
        for method in (_from_rss, _from_search):
            try:
                found = method(s, term)
                if found:
                    break
            except Exception as exc:
                log.error("deloitte", f"{method.__name__} '{term}': {str(exc)[:120]}")
        jobs.extend(found)
        time.sleep(1)
    unique = {j.url: j for j in jobs}
    log.count("deloitte", len(unique))
    return list(unique.values())
