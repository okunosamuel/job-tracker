"""Job sources. Each module exposes fetch(log) -> list[RawJob] and never raises."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124.0 Safari/537.36 personal-job-tracker")


def session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=2, backoff_factor=1.5, status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset(["GET", "POST"]))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-CA,en;q=0.9"})
    return s


def parse_date(value) -> date | None:
    """Turn the many date formats sources use into a date."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    low = text.lower()
    today = datetime.now(timezone.utc).date()
    if "today" in low or "just posted" in low:
        return today
    if "yesterday" in low:
        return today - timedelta(days=1)
    m = re.search(r"(\d+)\+?\s*(day|days|hour|hours)\s*ago", low)
    if m:
        n = int(m.group(1))
        return today if m.group(2).startswith("hour") else today - timedelta(days=n)
    if re.fullmatch(r"\d{10,13}", text):
        ts = int(text) / (1000 if len(text) == 13 else 1)
        return datetime.fromtimestamp(ts, tz=timezone.utc).date()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d %B %Y",
                "%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def money(lo, hi, interval: str | None = None) -> str:
    def fmt(v):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return None
        if v != v or v <= 0:   # NaN or empty
            return None
        return f"${v:,.0f}" if v >= 1000 else f"${v:,.2f}"
    a, b = fmt(lo), fmt(hi)
    if not a and not b:
        return ""
    rng = f"{a} to {b}" if a and b and a != b else (a or b)
    suffix = {"yearly": "/yr", "year": "/yr", "annual": "/yr", "hourly": "/hr", "hour": "/hr",
              "monthly": "/mo", "weekly": "/wk"}.get((interval or "").lower(), "")
    return rng + suffix
