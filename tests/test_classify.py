from tracker.classify import classify, dedupe_key, merge_duplicates, province_of, french_required
from tracker.models import RawJob


def job(title, company="Acme", location="Toronto, ON", bucket="fulltime", **kw):
    return classify(RawJob(title=title, company=company, location=location, bucket=bucket,
                           source=kw.pop("source", "indeed"), **kw))


# ---------- full-time, Ontario ----------
def test_grc_fulltime_ontario():
    j = job("GRC Analyst", location="Mississauga, ON")
    assert j and j.category == "fulltime" and "GRC" in j.tags


def test_it_audit_tag():
    j = job("IT Audit Senior Associate", company="Grant Thornton")
    assert j and "IT Audit" in j.tags and j.strong      # target employer


def test_soc_analyst():
    j = job("SOC Analyst I", location="Ottawa, Ontario")
    assert j and "SOC" in j.tags and j.level == "entry" and j.strong


def test_soc2_is_audit_not_soc():
    j = job("SOC 2 Compliance Analyst")
    assert j and "IT Audit" in j.tags and "SOC" not in j.tags


def test_network_and_support():
    assert "Network" in job("Network Administrator", location="Whitby, ON").tags
    assert "IT Support" in job("Service Desk Analyst", location="Kingston, ON").tags


def test_fulltime_outside_ontario_dropped():
    assert job("SOC Analyst", location="Calgary, AB") is None
    assert job("SOC Analyst", location="Montréal, QC") is None


def test_fulltime_remote_canada_kept():
    assert job("Cybersecurity Analyst", location="Remote, Canada", is_remote=True)


def test_canada_written_as_ca():
    j = job("Cyber Agentic AI Analyst", company="Deloitte", location="Toronto, ON, CA, M5H 0A9")
    assert j and j.category == "fulltime"
    assert job("SOC Analyst", location="Mississauga, ON, CA")
    assert job("SOC Analyst", location="San Jose, CA") is None


def test_foreign_dropped():
    assert job("SOC Analyst", location="Austin, TX") is None
    assert job("SOC Analyst", location="Bengaluru, India") is None


def test_irrelevant_dropped():
    assert job("Registered Nurse") is None
    assert job("Credit Risk Analyst") is None   # financial risk, not IT risk


def test_excluded_titles():
    assert job("Cybersecurity Intern") is None
    assert job("IT Support Co-op Student") is None
    assert job("Director, Cyber Risk") is None


def test_retail_tech_not_fulltime():
    assert job("Geek Squad Agent", location="Oshawa, ON") is None


# ---------- part-time, Durham and GTA ----------
def test_parttime_durham():
    j = job("Part-Time IT Support Technician", location="Oshawa, ON", bucket="parttime")
    assert j and j.category == "parttime" and j.strong


def test_parttime_retail_tech():
    j = job("Geek Squad Agent", location="Pickering, ON", bucket="parttime", job_type="parttime")
    assert j and j.category == "parttime" and "Retail Tech" in j.tags


def test_parttime_outside_area_dropped():
    assert job("Part-time Help Desk", location="Ottawa, ON", bucket="parttime") is None


# ---------- graduate, Canada except Quebec ----------
def test_graduate_vancouver_kept():
    j = job("Technology Risk Consultant - New Grad 2027", company="KPMG",
            location="Vancouver, BC", bucket="graduate")
    assert j and j.category == "graduate" and j.level == "graduate" and j.strong


def test_graduate_quebec_dropped():
    assert job("Cyber New Grad 2027", company="Deloitte", location="Montreal, QC",
               bucket="graduate") is None


def test_graduate_big_firm_generic_title():
    j = job("Tech & Transformation - Strategy - New Grad 2027", company="Deloitte",
            location="Toronto, ON", bucket="graduate")
    assert j and j.category == "graduate"


def test_graduate_student_not_grad_program():
    assert job("Graduate Research Assistant, Cyber", bucket="graduate") is None


# ---------- French ----------
def test_french_required_dropped():
    assert job("Security Analyst", location="Ottawa, ON",
               description="Bilingualism (English and French) is required for this role.") is None
    assert french_required("Bilingual imperative position")


def test_french_asset_kept():
    assert job("Security Analyst", location="Ottawa, ON",
               description="Knowledge of French is an asset.")


# ---------- places, duplicates ----------
def test_province():
    assert province_of("Toronto, ON") == "ON"
    assert province_of("Whitby") == "ON"
    assert province_of("Laval, Quebec") == "QC"
    assert province_of("Halifax, NS, CA") == "NS"
    assert province_of("Canada") is None


def test_dedupe_same_job_two_sources():
    a = job("SOC Analyst", company="Bell Canada Inc.", location="Toronto, ON", source="indeed")
    b = job("SOC Analyst", company="Bell Canada", location="Toronto, Ontario, Canada",
            source="linkedin", description="Full description here")
    assert a.dedupe_key == b.dedupe_key
    merged = merge_duplicates([a, b])
    assert len(merged) == 1 and set(merged[0].sources) == {"indeed", "linkedin"}


def test_dedupe_key_ignores_part_time_word():
    assert dedupe_key("X", "Help Desk (Part-Time)", "Ajax, ON") == dedupe_key("X", "Help Desk", "Ajax")
