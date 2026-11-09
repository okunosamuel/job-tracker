"""Decides whether a posting is relevant, which category it belongs to, and how good a match it is."""
from __future__ import annotations

import re

from . import config
from .models import Job, RawJob, clean_text

# ---------------------------------------------------------------------------
# Role tags, matched against the job title
# ---------------------------------------------------------------------------
ROLE_PATTERNS: dict[str, list[str]] = {
    "GRC": [
        r"\bgrc\b",
        r"governance,? risk",
        r"\b(it|technology|tech|cyber|cybersecurity|information|security|operational technology|third[- ]party|vendor)\s+risk\b",
        r"\brisk\b.*\b(cyber|security|technology)\b",
        r"\b(cyber|cybersecurity|security|it|information)\b.*\b(risk|governance|compliance)\b",
        r"\b(security|it|technology|cyber)\s+compliance\b",
        r"\bprivacy\b",
        r"\bdigital trust\b",
        r"\biso ?27001\b",
        r"\bnist\b",
    ],
    "IT Audit": [
        r"\b(it|technology|information systems|is|cyber|systems)\s+(audit|auditor|assurance)\b",
        r"\baudit\b.*\b(technology|it|systems|cyber)\b",
        r"\bsoc ?[12]\b",
        r"\b(risk|technology) assurance\b",
        r"\bsox\b.*\b(it|itgc)\b|\bitgc\b",
    ],
    "SOC": [
        r"\bsoc\b(?! ?[12]\b)",
        r"security operations",
        r"\b(cyber ?security|information security|security|cyber)\s+(analyst|specialist|engineer|consultant|associate)\b",
        r"\bincident response\b",
        r"\bthreat\b",
        r"\bsiem\b",
        r"\bvulnerability\b",
    ],
    "Cyber": [
        r"\bcyber",
        r"\binformation security\b",
        r"\binfosec\b",
    ],
    "Network": [
        r"\bnetwork(ing)?\s+(admin|administrator|technician|analyst|engineer|specialist|support|operations|associate)\b",
        r"\bnoc\b",
        r"\bnetwork\b",
    ],
    "IT Support": [
        r"\bhelp ?desk\b",
        r"\bservice desk\b",
        r"\bdesktop support\b",
        r"\b(it|i\.t\.|technical|tech|end[- ]user|deskside|field|computer|pc|desktop)\s+(support|technician|specialist)\b",
        r"\bit\s+(analyst|administrator|coordinator|assistant|officer|associate)\b",
        r"\bsystems? administrator\b",
        r"\bsysadmin\b",
        r"\btier ?[12]\b.*\bsupport\b",
        r"\bsupport (analyst|technician|specialist)\b",
    ],
    "Retail Tech": [
        r"\bgeek squad\b",
        r"\b(tech|technology|computer|mobile|device|repair|electronics)\s+(advisor|consultant|specialist|sales|expert|technician|associate)\b",
        r"\bretail\b.*\b(tech|technology|technician|computer)\b",
        r"\b(apple|samsung) (specialist|technical|expert)\b",
        r"\bgenius\b",
        r"\bcomputer sales\b",
    ],
}

# Extra tag only used for graduate programs at big firms ("Risk Consulting - New Grad 2027")
GRAD_EXTRA = [r"\brisk\b", r"\bassurance\b", r"\btechnology\b", r"\bdigital\b", r"\bconsult",
              r"\btransformation\b", r"\banalytics\b"]

TOP_TAGS = {"GRC", "IT Audit", "Cyber", "SOC"}

COMPILED = {tag: [re.compile(p, re.I) for p in pats] for tag, pats in ROLE_PATTERNS.items()}
GRAD_EXTRA_RE = [re.compile(p, re.I) for p in GRAD_EXTRA]

EXCLUDE_TITLE = re.compile(
    r"\b(intern|internship|interns|co-?op|coop|summer student|work term|placement student|"
    r"student assistant|director|vice[- ]president|vp|chief|head of|principal|partner|"
    r"senior manager|managing director|executive|volunteer|unpaid|research assistant|"
    r"teaching assistant|graduate student|postdoc|postdoctoral|professor|instructor|faculty)\b", re.I)

GRADUATE_RE = re.compile(
    r"\b(new grad|new graduate|recent grad|recent graduate|graduate program|graduate programme|"
    r"campus|early career|early talent|university hire|university graduate|class of 20\d\d|"
    r"20(26|27) (graduate|grad)|graduate,|- graduate|graduate -|graduate analyst|graduate consultant|"
    r"graduate associate|graduate role|new grad 20\d\d|full[- ]time graduate|early graduate)\b", re.I)
NOT_GRADUATE_RE = re.compile(r"graduate (student|research|teaching|assistant)|postgraduate|post-graduate", re.I)

PARTTIME_RE = re.compile(r"\bpart[- ]?time\b", re.I)
SENIOR_RE = re.compile(r"\b(senior|sr\.?|lead|manager|staff|architect|iii|iv)\b", re.I)
ENTRY_RE = re.compile(r"\b(junior|jr\.?|entry[- ]level|associate|tier ?1|level ?1|analyst i|i)\b", re.I)

FRENCH_REQUIRED_RE = re.compile(
    r"(french (is |language )?(required|mandatory|essential|is a must)|"
    r"(must|required to|need to|should) (be )?(fluent|proficient|bilingual)[^.]{0,30}french|"
    r"fluen(t|cy) in (both )?(english and french|french and english|french)[^.]{0,40}(required|mandatory|essential|must)|"
    r"bilingual(ism)? (\(english[^)]*french\) )?(is )?(required|mandatory|essential|imperative)|"
    r"bilingual imperative|bilingue|français|francais|langue fran)", re.I)

PROVINCE_RE = re.compile(r"(?:,|\(|\b)\s*(ON|QC|BC|AB|MB|SK|NS|NB|NL|PE|PEI|YT|NT|NU)\s*(?:\)|,|$|\b)")
PROVINCE_NAMES = {
    "ontario": "ON", "quebec": "QC", "québec": "QC", "british columbia": "BC", "alberta": "AB",
    "manitoba": "MB", "saskatchewan": "SK", "nova scotia": "NS", "new brunswick": "NB",
    "newfoundland": "NL", "prince edward island": "PE", "yukon": "YT", "northwest territories": "NT",
    "nunavut": "NU",
}
CANADA_CITIES = {
    "vancouver": "BC", "victoria": "BC", "burnaby": "BC", "surrey": "BC", "richmond, bc": "BC",
    "kelowna": "BC", "calgary": "AB", "edmonton": "AB", "winnipeg": "MB", "regina": "SK",
    "saskatoon": "SK", "halifax": "NS", "fredericton": "NB", "moncton": "NB", "saint john": "NB",
    "st. john's": "NL", "charlottetown": "PE", "whitehorse": "YT", "yellowknife": "NT",
}
FOREIGN_RE = re.compile(r"\b(united states|usa|u\.s\.|india|united kingdom|uk|london, england|"
                        r"philippines|mexico|ireland|germany|poland|australia|singapore)\b|"
                        r",\s*(ny|ca|tx|wa|il|ma|nj|ga|fl|va|nc|pa|oh|co|az|mn|mi)\s*(,|$)", re.I)


def norm(text: str | None) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


COMPANY_SUFFIX_RE = re.compile(r"\b(inc|ltd|llp|llc|corp|corporation|limited|co|canada|group|the)\b")


def dedupe_key(company: str, title: str, location: str) -> str:
    c = re.sub(r"\s+", " ", COMPANY_SUFFIX_RE.sub(" ", norm(company))).strip()
    t = norm(title)
    t = re.sub(r"\b(part time|full time|remote|hybrid)\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    city = norm((location or "").split(",")[0].split("(")[0])
    return f"{c}|{t}|{city}"


def role_tags(title: str, bucket: str) -> list[str]:
    tags = [tag for tag, pats in COMPILED.items() if any(p.search(title) for p in pats)]
    if "SOC" in tags and "IT Audit" in tags and re.search(r"\bsoc ?[12]\b", title, re.I):
        tags.remove("SOC")
    return tags


def province_of(location: str) -> str | None:
    loc = location or ""
    low = loc.lower()
    if any(m in low for m in config.QUEBEC_MARKERS):
        return "QC"
    for name, code in PROVINCE_NAMES.items():
        if name in low:
            return code
    m = PROVINCE_RE.search(loc)
    if m:
        code = m.group(1).upper()
        return "PE" if code == "PEI" else code
    if any(c in low for c in config.ONTARIO_CITIES):
        return "ON"
    for city, code in CANADA_CITIES.items():
        if city in low:
            return code
    return None


def in_durham_gta(location: str) -> bool:
    low = (location or "").lower()
    return any(c in low for c in config.DURHAM_GTA)


def is_target_employer(company: str) -> bool:
    low = (company or "").lower()
    return any(re.search(r"\b" + re.escape(e) + r"\b", low) for e in config.TARGET_EMPLOYERS)


def french_required(text: str) -> bool:
    return bool(FRENCH_REQUIRED_RE.search(text or ""))


def level_of(title: str, is_grad: bool) -> str:
    if is_grad:
        return "graduate"
    if ENTRY_RE.search(title) and not SENIOR_RE.search(title):
        return "entry"
    if SENIOR_RE.search(title):
        return "senior"
    return "mid"


def classify(raw: RawJob) -> Job | None:
    """Return a classified Job, or None if the posting should be ignored."""
    title = clean_text(raw.title)
    if not title:
        return None
    if EXCLUDE_TITLE.search(title):
        return None

    desc = clean_text(raw.description)
    loc = raw.location or ""
    remote = raw.is_remote or bool(re.search(r"\bremote\b", loc, re.I))
    prov = province_of(loc)
    # ", CA" after a province means Canada, so only check for other countries
    # when no Canadian province or city was found
    if prov is None and FOREIGN_RE.search(loc) and "canada" not in loc.lower():
        return None

    is_grad = bool(GRADUATE_RE.search(title)) and not NOT_GRADUATE_RE.search(title)
    is_part = raw.job_type == "parttime" or bool(PARTTIME_RE.search(title))
    if not is_part and raw.job_type is None and raw.bucket == "parttime":
        is_part = bool(PARTTIME_RE.search(desc[:600]))

    tags = role_tags(title, raw.bucket)

    # ---- pick the category and check its rules ----
    if is_part:
        category = "parttime"
        if not tags:
            return None
        if not in_durham_gta(loc):
            return None
    elif is_grad:
        category = "graduate"
        if not tags:
            if is_target_employer(raw.company) and any(p.search(title) for p in GRAD_EXTRA_RE):
                tags = ["Risk & Tech"]
            else:
                return None
        if prov == "QC":
            return None
        if prov is None and not remote and raw.bucket != "graduate" and "canada" not in loc.lower():
            return None
    else:
        category = "fulltime"
        tags = [t for t in tags if t != "Retail Tech"]
        if not tags:
            return None
        if prov is not None and prov != "ON" and not remote:
            return None
        if prov is None and not remote and raw.bucket != "fulltime":
            return None
        if prov == "QC":
            return None

    if french_required(desc) or french_required(title):
        return None

    level = level_of(title, is_grad)
    target = is_target_employer(raw.company)

    # ---- score out of 100 ----
    score = 0
    score += 40 if TOP_TAGS & set(tags) else 30
    location_ok = (category == "parttime" and in_durham_gta(loc)) or \
                  (category == "fulltime" and (prov == "ON" or remote)) or \
                  (category == "graduate" and prov not in (None, "QC")) or remote
    score += 20 if location_ok else 10
    score += {"graduate": 20, "entry": 20, "mid": 15, "senior": 5}[level]
    score += 20 if target else 0
    if category == "parttime" and ("IT Support" in tags or "Retail Tech" in tags):
        score += 10
    score = min(score, 100)

    strong = target or (bool(TOP_TAGS & set(tags)) and location_ok and level in ("graduate", "entry"))
    if category == "parttime":
        strong = target or ("IT Support" in tags and location_ok)

    return Job(raw=raw, category=category, tags=tags, level=level, score=score, strong=strong,
               dedupe_key=dedupe_key(raw.company, title, loc), sources=[raw.source])


def merge_duplicates(jobs: list[Job]) -> list[Job]:
    """Keep one job per dedupe key, preferring the version with the most detail."""
    best: dict[str, Job] = {}
    for job in jobs:
        cur = best.get(job.dedupe_key)
        if cur is None:
            best[job.dedupe_key] = job
            continue
        srcs = sorted(set(cur.sources) | set(job.sources))
        # prefer company career sites and longer descriptions
        def quality(j: Job) -> tuple:
            direct = j.raw.source in ("workday", "kpmg", "deloitte", "greenhouse", "lever", "jobbank")
            return (direct, bool(j.raw.closing_date), len(j.raw.description or ""))
        keep = job if quality(job) > quality(cur) else cur
        other = cur if keep is job else job
        keep.raw.closing_date = keep.raw.closing_date or other.raw.closing_date
        keep.raw.salary = keep.raw.salary or other.raw.salary
        keep.raw.date_posted = keep.raw.date_posted or other.raw.date_posted
        keep.sources = srcs
        keep.score = max(keep.score, other.score)
        keep.strong = keep.strong or other.strong
        best[job.dedupe_key] = keep
    return list(best.values())
