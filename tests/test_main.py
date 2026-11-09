import json
from types import SimpleNamespace

from tracker import main as M
from tracker import notify
from tracker.models import RawJob
from tracker.sources.jobbank import _parse


def fake_source(jobs):
    return SimpleNamespace(fetch=lambda log: jobs)


RAWS = [
    RawJob(title="SOC Analyst I", company="Bell Canada", location="Toronto, ON", source="indeed", bucket="fulltime"),
    RawJob(title="SOC Analyst I", company="Bell Canada Inc.", location="Toronto, Ontario", source="linkedin", bucket="fulltime"),
    RawJob(title="Registered Nurse", company="Lakeridge", location="Oshawa, ON", source="indeed", bucket="fulltime"),
    RawJob(title="Cyber New Grad 2027", company="Deloitte", location="Calgary, AB", source="linkedin", bucket="graduate"),
]


def broken_fetch(log):
    raise RuntimeError("site changed")


def test_dry_run(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "ROOT", tmp_path)
    monkeypatch.setattr(M, "SOURCES", [("fake", fake_source(RAWS)), ("broken", SimpleNamespace(fetch=broken_fetch))])
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    assert M.main(["x"]) == 0
    out = json.loads((tmp_path / "data" / "dry_run.json").read_text())
    titles = sorted(j["title"] for j in out["jobs"])
    assert titles == ["Cyber New Grad 2027", "SOC Analyst I"]        # nurse dropped, duplicate merged
    assert any("broken" in e for e in out["errors"])                 # broken source logged, run continued


class FakeDB:
    def __init__(self, url, key):
        self.calls = []
        FakeDB.last = self

    def select(self, table, params):
        self.calls.append(("select", table, params))
        if params.get("select") == "dedupe_key,id,stage":
            return [{"dedupe_key": "bell|soc analyst i|toronto", "id": "1", "stage": "applied"}]
        if params.get("stage") == "in.(new,saved)":
            return [{"id": "9", "title": "IT Audit", "company": "KPMG", "url": "u", "closing_date": "2026-11-10", "stage": "saved"}]
        return []

    def insert(self, table, rows):
        self.calls.append(("insert", table, rows))

    def upsert(self, table, rows, on_conflict):
        self.calls.append(("upsert", table, rows))

    def delete(self, table, filters):
        self.calls.append(("delete", table, filters))
        return 2

    def update(self, table, filters, values):
        self.calls.append(("update", table, filters, values))


def test_full_run_with_database(tmp_path, monkeypatch):
    import tracker.db
    monkeypatch.setattr(M, "ROOT", tmp_path)
    monkeypatch.setattr(M, "SOURCES", [("fake", fake_source(RAWS))])
    monkeypatch.setattr(tracker.db, "Supabase", FakeDB)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "k")
    sent, pushes = [], []
    monkeypatch.setattr(notify, "send_email", lambda s, b: sent.append((s, b)) or True)
    monkeypatch.setattr(notify, "push", lambda *a, **k: pushes.append(a) or True)
    assert M.main(["x"]) == 0
    db = FakeDB.last
    inserted = [c for c in db.calls if c[:2] == ("insert", "jobs")][0][2]
    upserted = [c for c in db.calls if c[0] == "upsert"][0][2]
    assert [r["title"] for r in inserted] == ["Cyber New Grad 2027"]      # only the unseen job is new
    assert "stage" not in upserted[0] and "notes" not in upserted[0]      # never overwrites your stage or notes
    assert sent and "1 new" in sent[0][0] and "reminder" in sent[0][0]
    assert any("Closes" in p[1] for p in pushes if len(p) > 1)            # deadline push
    assert ("update", "jobs", {"id": "eq.9"}) == [c for c in db.calls if c[0] == "update"][0][:3]
    assert json.loads((tmp_path / "data" / "last_run.json").read_text())["removed"] == 4


def test_jobbank_parser():
    html = """<article><a href="/jobsearch/jobposting/4123456;jsessionid=abc?source=searchresults" class="resultJobItem">
      <h3 class="title"><span class="flag">New</span> <span class="noctitle">IT support technician</span></h3>
      <ul><li class="date">November 07, 2026</li><li class="business">Durham Tech Inc.</li>
      <li class="location"><span class="wb-inv">Location</span>Whitby (ON)</li>
      <li class="salary"><span class="wb-inv">Salary:</span>$22.00 hourly</li></ul></a></article>"""
    jobs = _parse(html, "parttime")
    assert len(jobs) == 1
    j = jobs[0]
    assert j.title == "IT support technician" and j.company == "Durham Tech Inc."
    assert j.location == "Whitby, ON" and j.reference == "4123456" and j.date_posted.isoformat() == "2026-11-07"
    assert j.url == "https://www.jobbank.gc.ca/jobsearch/jobposting/4123456"
