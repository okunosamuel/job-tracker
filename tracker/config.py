"""Everything you might want to tune lives here: searches, places, employers, sources.

Edit this file on GitHub to change what the tracker looks for. No other file needs to change.
"""

# ---------------------------------------------------------------------------
# Searches. Each bucket is searched separately with its own location.
# ---------------------------------------------------------------------------
SEARCHES = {
    # Full-time: all of Ontario, entry level and experienced
    "fulltime": {
        "location": "Ontario, Canada",
        "adzuna_where": "Ontario",
        "terms": [
            "GRC analyst",
            "governance risk compliance",
            "IT risk analyst",
            "cybersecurity risk",
            "IT audit",
            "technology risk",
            "SOC analyst",
            "security analyst",
            "cybersecurity analyst",
            "network administrator",
            "network technician",
            "IT support",
            "desktop support",
            "service desk analyst",
        ],
    },
    # Part-time: Durham Region and the Greater Toronto Area (GTA)
    "parttime": {
        "location": "Oshawa, ON",
        "distance_miles": 45,
        "adzuna_where": "Toronto",
        "adzuna_distance_km": 70,
        "terms": [
            "part time IT support",
            "part time help desk",
            "part time technical support",
            "part time computer technician",
            "part time tech specialist retail",
            "Geek Squad",
            "part time service desk",
        ],
    },
    # Graduate / new grad programs: all of Canada except Quebec
    "graduate": {
        "location": "Canada",
        "adzuna_where": "",
        "terms": [
            "new grad cyber",
            "new graduate cybersecurity",
            "new grad technology risk",
            "new grad IT audit",
            "graduate program technology",
            "campus cyber security",
            "entry level GRC",
            "2027 new grad consulting",
        ],
    },
}

# How far back each run looks (hours). 72 covers a missed day or two.
HOURS_OLD = 72

# ---------------------------------------------------------------------------
# Target employers: any relevant posting from these counts as a strong match.
# Lowercase names matched as whole words against the company name.
# ---------------------------------------------------------------------------
TARGET_EMPLOYERS = [
    "deloitte", "kpmg", "pwc", "pricewaterhouse", "ernst & young", "ernst and young", "ey",
    "accenture", "bdo", "grant thornton", "mnp", "protiviti",
    "rbc", "royal bank", "td bank", "td", "toronto-dominion", "bmo", "bank of montreal",
    "scotiabank", "cibc", "national bank", "manulife", "sun life", "intact",
    "ibm", "microsoft", "google", "amazon", "shopify", "cisco", "bell canada", "rogers", "telus",
    "government of ontario", "ontario public service", "government of canada",
    "ontario power generation", "hydro one",
]

# ---------------------------------------------------------------------------
# Places
# ---------------------------------------------------------------------------
DURHAM_GTA = [
    # Durham Region
    "oshawa", "whitby", "ajax", "pickering", "clarington", "bowmanville", "courtice",
    "newcastle", "uxbridge", "scugog", "port perry", "brock", "durham",
    # City of Toronto
    "toronto", "scarborough", "north york", "etobicoke", "east york", "york, on",
    # Peel, York and Halton regions
    "mississauga", "brampton", "caledon", "markham", "vaughan", "richmond hill",
    "concord", "woodbridge", "thornhill", "maple", "newmarket", "aurora",
    "stouffville", "king city", "east gwillimbury", "georgina", "oakville",
    "burlington", "milton", "halton hills", "georgetown", "gta",
]

ONTARIO_CITIES = DURHAM_GTA + [
    "ottawa", "hamilton", "london, on", "kitchener", "waterloo", "cambridge", "guelph",
    "barrie", "kingston", "windsor", "sudbury", "thunder bay", "peterborough",
    "st. catharines", "niagara", "belleville", "brantford", "sarnia", "north bay",
    "sault ste", "cobourg", "orillia", "lindsay", "kanata", "nepean",
]

QUEBEC_MARKERS = [
    "quebec", "québec", "montreal", "montréal", "laval", "gatineau", "sherbrooke",
    "longueuil", "trois-rivi", "saguenay", "lévis", "levis", "terrebonne", "brossard",
    "boucherville", "pointe-claire", "dorval", "saint-laurent",
]

# ---------------------------------------------------------------------------
# Sources that need no keys. Failures are logged and skipped, never fatal.
# ---------------------------------------------------------------------------
JOBSPY_SITES = ["indeed", "linkedin", "glassdoor", "google"]
JOBSPY_RESULTS_PER_SEARCH = 25

# Adzuna free plan: one run uses about 29 searches a day (about 900 a month).
ADZUNA_MAX_CALLS = 40

# Company career sites on Workday: (company name, host, tenant, site)
WORKDAY_BOARDS = [
    ("RBC", "rbc.wd3.myworkdayjobs.com", "rbc", "RBCGLOBAL1"),
    ("TD Bank", "td.wd3.myworkdayjobs.com", "td", "TD_Bank_Careers"),
    ("BMO", "bmo.wd3.myworkdayjobs.com", "bmo", "External"),
    ("CIBC", "cibc.wd3.myworkdayjobs.com", "cibc", "search"),
    ("PwC", "pwc.wd3.myworkdayjobs.com", "pwc", "Global_Experienced_Careers"),
    ("PwC", "pwc.wd3.myworkdayjobs.com", "pwc", "Global_Campus_Careers"),
    ("Manulife", "manulife.wd3.myworkdayjobs.com", "manulife", "MFCJH_Jobs"),
    ("Sun Life", "sunlife.wd3.myworkdayjobs.com", "sunlife", "Experienced-Jobs"),
]
WORKDAY_TERMS = ["cyber", "security analyst", "IT risk", "technology risk", "IT audit",
                 "GRC", "new grad technology", "network", "service desk"]

# KPMG Canada career site (Jibe). Searched with these keywords.
KPMG_BASE = "https://careers.kpmg.ca"
KPMG_TERMS = ["cyber", "technology risk", "IT audit", "risk consulting", "privacy", "graduate"]

# Deloitte Canada career site (SAP SuccessFactors)
DELOITTE_BASE = "https://careers.deloitte.ca"
DELOITTE_TERMS = ["cyber", "risk", "IT audit", "privacy", "new grad"]

# Greenhouse and Lever job boards (company name, board token)
GREENHOUSE_BOARDS = [
    ("Wealthsimple", "wealthsimple"),
    ("Arctic Wolf", "arcticwolf"),
]
LEVER_BOARDS = [
    ("eSentire", "esentire"),
]

# Job Bank (Government of Canada)
JOBBANK_ENABLED = True

# ---------------------------------------------------------------------------
# Tracking rules
# ---------------------------------------------------------------------------
FOLLOWUP_DAYS = 14          # nudge when an application has had no change this long
DEADLINE_WARN_DAYS = 3      # warn when a saved or new posting closes within this many days
STALE_DAYS = 30             # unapplied postings older than this ...
UNSEEN_DAYS = 14            # ... and not seen in any source for this long are removed
