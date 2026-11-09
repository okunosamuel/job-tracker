"""The shape every source turns its results into."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date


@dataclass
class RawJob:
    title: str
    company: str = ""
    location: str = ""
    url: str = ""
    description: str = ""
    source: str = ""
    bucket: str = ""                 # which search found it: fulltime, parttime or graduate
    job_type: str | None = None      # "fulltime", "parttime", "contract", or None if unknown
    date_posted: date | None = None
    closing_date: date | None = None
    salary: str = ""
    reference: str = ""
    is_remote: bool = False


@dataclass
class Job:
    """A raw job after classification, ready to save."""
    raw: RawJob
    category: str
    tags: list[str]
    level: str
    score: int
    strong: bool
    dedupe_key: str
    sources: list[str] = field(default_factory=list)

    def to_row(self) -> dict:
        r = self.raw
        return {
            "dedupe_key": self.dedupe_key,
            "title": r.title.strip()[:300],
            "company": (r.company or "").strip()[:200],
            "location": (r.location or "").strip()[:200],
            "category": self.category,
            "job_type": r.job_type,
            "level": self.level,
            "salary": (r.salary or "")[:120],
            "date_posted": r.date_posted.isoformat() if r.date_posted else None,
            "closing_date": r.closing_date.isoformat() if r.closing_date else None,
            "url": r.url,
            "reference": (r.reference or "")[:80],
            "source": r.source,
            "sources": sorted(set(self.sources or [r.source])),
            "tags": self.tags,
            "score": self.score,
            "strong": self.strong,
            "description": clean_text(r.description)[:3000],
        }


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = _TAG_RE.sub(" ", str(text))
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")
                .replace("&quot;", '"'))
    return _WS_RE.sub(" ", text).strip()
