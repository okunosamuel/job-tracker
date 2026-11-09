"""Prints what each tricky source and the email server actually return.

Run from GitHub: Actions > Diagnose > Run workflow. Secrets are never printed.
"""
from __future__ import annotations

import os
import smtplib
import socket

from . import config
from .classify import classify
from .main import RunLog
from .sources import deloitte, session


def kpmg():
    print("== KPMG ==")
    s = session()
    r0 = s.get(f"{config.KPMG_BASE}/professionals/jobs", timeout=30)
    print("jobs page:", r0.status_code, "cookies:", list(s.cookies.keys()))
    for params in ({"keywords": "cyber", "limit": 5, "page": 1}, {"keywords": "cyber"}, {}):
        try:
            r = s.get(f"{config.KPMG_BASE}/api/jobs", params=params, timeout=30,
                      headers={"Accept": "application/json, text/plain, */*"})
            print(params, r.status_code, r.headers.get("content-type"), "|", r.text[:400].replace("\n", " "))
        except Exception as exc:
            print(params, "ERROR", type(exc).__name__, str(exc)[-300:])


def deloitte_sample():
    print("== Deloitte ==")
    log = RunLog()
    jobs = deloitte.fetch(log)
    for j in jobs[:12]:
        c = classify(j)
        print(repr(j.title), "|", repr(j.location), "|", j.url[:90], "|", "KEPT" if c else "dropped")


def email():
    print("== Email ==")
    sender = (os.getenv("GMAIL_ADDRESS") or "").strip()
    pw = "".join((os.getenv("GMAIL_APP_PASSWORD") or "").split())
    print("address set:", bool(sender), "| looks like an email:", "@" in sender,
          "| password length:", len(pw), "| password is ascii:", pw.isascii())
    for host, port in (("smtp.gmail.com", 465), ("smtp.gmail.com", 587)):
        try:
            sock = socket.create_connection((host, port), timeout=10)
            print(port, "tcp connect ok")
            sock.close()
        except Exception as exc:
            print(port, "tcp connect FAILED:", exc)
            continue
        stage = "connect"
        try:
            if port == 465:
                smtp = smtplib.SMTP_SSL(host, port, timeout=30)
            else:
                smtp = smtplib.SMTP(host, port, timeout=30)
                stage = "starttls"
                smtp.ehlo(); smtp.starttls(); smtp.ehlo()
            stage = "login"
            smtp.ehlo_or_helo_if_needed()
            smtp.user, smtp.password = sender, pw
            smtp.auth("PLAIN", smtp.auth_plain)   # one clear answer, no fallbacks
            print(port, "LOGIN OK")
            smtp.quit()
        except smtplib.SMTPAuthenticationError as exc:
            print(port, "Gmail rejected the address/app password:", exc.smtp_code)
        except Exception as exc:
            print(port, f"failed at {stage}:", type(exc).__name__, str(exc)[:300])


if __name__ == "__main__":
    for step in (email, kpmg, deloitte_sample):
        try:
            step()
        except Exception as exc:
            print(step.__name__, "crashed:", exc)
