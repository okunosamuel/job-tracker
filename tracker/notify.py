"""Email digest (Gmail) and phone push (ntfy)."""
from __future__ import annotations

import html
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import requests

CATEGORY_NAMES = {"fulltime": "Full-time (Ontario)", "parttime": "Part-time (Durham and GTA)",
                  "graduate": "Graduate and new grad (Canada, not Quebec)"}


def push(title: str, message: str, click: str | None = None, priority: int = 4,
         tags: list[str] | None = None) -> bool:
    topic = os.getenv("NTFY_TOPIC")
    if not topic:
        return False
    body = {"topic": topic, "title": title[:250], "message": message[:3500], "priority": priority,
            "tags": tags or ["briefcase"]}
    if click:
        body["click"] = click
    try:
        r = requests.post(os.getenv("NTFY_SERVER", "https://ntfy.sh"), json=body, timeout=20)
        return r.ok
    except Exception:
        return False


def _job_html(j: dict) -> str:
    star = "&#9733; " if j.get("strong") else ""
    bits = [html.escape(x) for x in (j.get("company"), j.get("location")) if x]
    meta = " &middot; ".join(bits)
    extra = []
    if j.get("salary"):
        extra.append(html.escape(j["salary"]))
    if j.get("closing_date"):
        extra.append(f"closes {html.escape(str(j['closing_date']))}")
    if j.get("tags"):
        extra.append(", ".join(html.escape(t) for t in j["tags"]))
    extra.append(f"score {j.get('score', 0)}")
    return (f'<tr><td style="padding:10px 0;border-bottom:1px solid #e6e2da">'
            f'<a href="{html.escape(j.get("url") or "#")}" style="color:#1d3b53;font-weight:600;'
            f'text-decoration:none;font-size:15px">{star}{html.escape(j["title"])}</a><br>'
            f'<span style="color:#444;font-size:13px">{meta}</span><br>'
            f'<span style="color:#888;font-size:12px">{" &middot; ".join(extra)}</span></td></tr>')


def digest_html(new_jobs: list[dict], deadlines: list[dict], followups: list[dict],
                stats: dict, dashboard: str) -> str:
    parts = ['<div style="font-family:Segoe UI,Helvetica,Arial,sans-serif;max-width:640px;'
             'margin:auto;color:#222">',
             f'<h2 style="margin:0 0 4px;color:#1d3b53">Job Tracker: {len(new_jobs)} new '
             f'match{"es" if len(new_jobs) != 1 else ""}</h2>',
             f'<p style="margin:0 0 18px;color:#666;font-size:13px">'
             f'{stats.get("strong", 0)} strong &middot; '
             f'<a href="{html.escape(dashboard)}" style="color:#b5651d">Open dashboard</a></p>']
    if deadlines or followups:
        parts.append('<h3 style="color:#b5451d;margin:18px 0 6px">Reminders</h3><ul style="padding-left:18px">')
        for j in deadlines:
            parts.append(f'<li>Closes {html.escape(str(j.get("closing_date")))}: '
                         f'<a href="{html.escape(j.get("url") or "#")}">{html.escape(j["title"])}</a>'
                         f' at {html.escape(j.get("company") or "")}</li>')
        for j in followups:
            parts.append(f'<li>Follow up (no change in 14+ days): {html.escape(j["title"])} at '
                         f'{html.escape(j.get("company") or "")}</li>')
        parts.append("</ul>")
    for cat in ("graduate", "fulltime", "parttime"):
        group = [j for j in new_jobs if j.get("category") == cat]
        if not group:
            continue
        parts.append(f'<h3 style="margin:22px 0 4px;color:#1d3b53">{CATEGORY_NAMES[cat]} ({len(group)})</h3>'
                     '<table style="width:100%;border-collapse:collapse">')
        parts.extend(_job_html(j) for j in group[:60])
        parts.append("</table>")
        if len(group) > 60:
            parts.append(f'<p style="color:#666">and {len(group) - 60} more on the dashboard.</p>')
    if not new_jobs:
        parts.append('<p>No new matches today. Your pipeline is unchanged.</p>')
    src = stats.get("source_counts", {})
    errs = stats.get("errors", [])
    parts.append('<p style="margin-top:28px;color:#999;font-size:11px">Sources checked: ' +
                 html.escape(", ".join(f"{k} {v}" for k, v in sorted(src.items()))) +
                 (f" &middot; {len(errs)} source errors (see run log)" if errs else "") + "</p></div>")
    return "".join(parts)


def send_email(subject: str, body_html: str) -> bool:
    sender, password = os.getenv("GMAIL_ADDRESS"), os.getenv("GMAIL_APP_PASSWORD")
    to = os.getenv("ALERT_EMAIL") or sender
    if not sender or not password or not to:
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, f"Job Tracker <{sender}>", to
    msg.attach(MIMEText(body_html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(sender, password.replace(" ", ""))
        smtp.sendmail(sender, [to], msg.as_string())
    return True


def today_label() -> str:
    return datetime.now(ZoneInfo("America/Toronto")).strftime("%a %b %-d")
