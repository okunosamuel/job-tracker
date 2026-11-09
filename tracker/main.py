"""The daily run: collect, filter, save, clean up, remind, alert.

Run it with:  python -m tracker.main
Without Supabase settings it does a dry run and writes data/dry_run.json instead.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config, notify
from .classify import classify, merge_duplicates
from .sources import adzuna, boards, deloitte, jobbank, jobspy_src, kpmg, workday

ROOT = Path(__file__).resolve().parent.parent
SOURCES = [("kpmg", kpmg), ("deloitte", deloitte), ("workday", workday), ("boards", boards),
           ("adzuna", adzuna), ("jobbank", jobbank), ("jobspy", jobspy_src)]


class RunLog:
    def __init__(self):
        self.counts: Counter = Counter()
        self.errors: list[str] = []

    def count(self, source: str, n: int):
        self.counts[source.split(":")[0]] += n

    def error(self, source: str, msg: str):
        line = f"[{source}] {msg}"
        self.errors.append(line)
        print("  warn", line, flush=True)


def collect(log: RunLog, only: set[str] | None = None):
    raws = []
    for name, mod in SOURCES:
        if only and name not in only:
            continue
        print(f"-> {name}", flush=True)
        try:
            got = mod.fetch(log)
        except Exception as exc:   # a broken source never stops the run
            log.error(name, f"crashed: {exc}")
            traceback.print_exc()
            got = []
        print(f"   {len(got)} raw postings", flush=True)
        raws.extend(got)
    return raws


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def main(argv: list[str]) -> int:
    started = datetime.now(timezone.utc)
    only = set(argv[1].split(",")) if len(argv) > 1 else None
    log = RunLog()
    raws = collect(log, only)
    classified = [j for j in (classify(r) for r in raws) if j]
    jobs = merge_duplicates(classified)
    print(f"{len(raws)} raw -> {len(classified)} relevant -> {len(jobs)} unique", flush=True)

    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        out = ROOT / "data" / "dry_run.json"
        out.parent.mkdir(exist_ok=True)
        rows = sorted((j.to_row() for j in jobs), key=lambda r: (-r["strong"], -r["score"]))
        out.write_text(json.dumps({"counts": log.counts, "errors": log.errors, "jobs": rows},
                                  indent=2, default=str))
        print(f"Dry run (no Supabase settings): wrote {len(rows)} jobs to {out}")
        return 0

    from .db import Supabase
    db = Supabase(url, key)
    now = datetime.now(timezone.utc)
    today = now.date()

    existing = {r["dedupe_key"]: r for r in db.select("jobs", {"select": "dedupe_key,id,stage"})}
    new_rows, seen_rows = [], []
    for j in jobs:
        row = j.to_row()
        if j.dedupe_key in existing:
            seen_rows.append({"dedupe_key": row["dedupe_key"], "title": row["title"],
                              "last_seen": iso(now), "score": row["score"], "strong": row["strong"],
                              "tags": row["tags"], "sources": row["sources"]})
        else:
            row["first_seen"] = row["last_seen"] = iso(now)
            new_rows.append(row)
    if new_rows:
        db.insert("jobs", new_rows)
    if seen_rows:
        db.upsert("jobs", seen_rows, on_conflict="dedupe_key")
    print(f"saved {len(new_rows)} new, refreshed {len(seen_rows)}", flush=True)

    # ---- remove expired postings you have not applied to ----
    removable = "in.(new,saved,dismissed)"
    removed = db.delete("jobs", {"stage": removable, "closing_date": f"lt.{today.isoformat()}"})
    removed += db.delete("jobs", {"stage": removable, "manual": "is.false",
                                  "first_seen": f"lt.{iso(now - timedelta(days=config.STALE_DAYS))}",
                                  "last_seen": f"lt.{iso(now - timedelta(days=config.UNSEEN_DAYS))}"})
    print(f"removed {removed} expired", flush=True)

    # ---- reminders ----
    cols = "id,title,company,url,closing_date,stage"
    deadlines = db.select("jobs", {
        "select": cols, "stage": "in.(new,saved)", "deadline_sent_at": "is.null",
        "and": f"(closing_date.gte.{today.isoformat()},"
               f"closing_date.lte.{(today + timedelta(days=config.DEADLINE_WARN_DAYS)).isoformat()})"})
    followups = db.select("jobs", {
        "select": cols, "followup_sent_at": "is.null",
        "stage": "in.(applied,assessment,interview_1,interview_2,interview_final)",
        "stage_changed_at": f"lt.{iso(now - timedelta(days=config.FOLLOWUP_DAYS))}"})

    # ---- alerts ----
    new_rows.sort(key=lambda r: (-int(r["strong"]), -r["score"]))
    strong = [r for r in new_rows if r["strong"]]
    dashboard = os.getenv("DASHBOARD_URL", "")
    stats = {"strong": len(strong), "source_counts": dict(log.counts), "errors": log.errors}
    try:
        subject = f"{len(new_rows)} new jobs ({len(strong)} strong) for {notify.today_label()}"
        if deadlines or followups:
            subject += f" + {len(deadlines) + len(followups)} reminders"
        sent = notify.send_email(subject, notify.digest_html(new_rows, deadlines, followups,
                                                             stats, dashboard))
        print("email sent" if sent else "email skipped (Gmail settings missing)", flush=True)
    except Exception as exc:
        log.error("email", str(exc)[:200])

    by_cat = Counter(r["category"] for r in new_rows)
    print(f"new by category: {dict(by_cat)}; strong: {len(strong)}", flush=True)
    for r in new_rows[:25]:
        print(f"   {r['score']:>3} {'*' if r['strong'] else ' '} [{r['category']}] {r['title']} | "
              f"{r.get('company')} | {r.get('location')} | {','.join(r['tags'])}", flush=True)
    if len(strong) <= 5:
        for r in strong:
            notify.push(f"Strong match: {r['title']}",
                        f"{r.get('company') or ''} · {r.get('location') or ''} · score {r['score']}",
                        click=r.get("url") or dashboard, tags=["star"])
    else:
        ok = notify.push(f"{len(strong)} strong matches today",
                    "\n".join(f"• {r['title']} ({r.get('company') or ''})" for r in strong[:10]),
                    click=dashboard, tags=["star"])
        print("phone push sent" if ok else "phone push failed or NTFY_TOPIC missing", flush=True)
    reminder_lines = [f"Closes {r['closing_date']}: {r['title']}" for r in deadlines] + \
                     [f"Follow up: {r['title']} ({r.get('company') or ''})" for r in followups]
    if reminder_lines:
        notify.push(f"{len(reminder_lines)} job reminder{'s' if len(reminder_lines) > 1 else ''}",
                    "\n".join(reminder_lines[:10]), click=dashboard, priority=3, tags=["alarm_clock"])
    for r in deadlines:
        db.update("jobs", {"id": f"eq.{r['id']}"}, {"deadline_sent_at": iso(now)})
    for r in followups:
        db.update("jobs", {"id": f"eq.{r['id']}"}, {"followup_sent_at": iso(now)})

    summary = {"started_at": iso(started), "finished_at": iso(datetime.now(timezone.utc)),
               "found": len(jobs), "added": len(new_rows), "removed": removed,
               "source_counts": dict(log.counts), "errors": log.errors[:100]}
    try:
        db.insert("runs", [summary])
    except Exception as exc:
        print("could not record run:", exc)
    out = ROOT / "data" / "last_run.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "errors"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
