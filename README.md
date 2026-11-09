# Job Tracker

A personal job tracker that searches for postings every morning, keeps only the relevant ones,
and tracks each application from Saved to Offer.

- **Full-time:** Governance, Risk, and Compliance (GRC), IT audit, Security Operations Centre (SOC)
  analyst, network and IT support roles across Ontario, entry level and experienced.
- **Part-time:** IT support, help desk and retail tech roles in Durham Region and the Greater
  Toronto Area (GTA).
- **Graduate and new grad:** programs at the Big 4, banks, tech companies and government,
  anywhere in Canada except Quebec. Roles that require French are skipped.

## How it works

| Part | What it does | Where it runs |
| --- | --- | --- |
| Scanner (`tracker/`) | Collects postings, removes duplicates, scores each one, removes expired ones, sends reminders and alerts | GitHub Actions, every morning (free) |
| Database (`supabase/`) | Stores postings, stages, dates and notes | Supabase (free) |
| Dashboard (`docs/`) | Browse jobs, change stages, write notes, add jobs by hand | GitHub Pages (free) |
| Alerts | Daily email digest, plus phone pushes for strong matches and reminders | Gmail and the ntfy app |

### Sources

| Source | How | Reliability |
| --- | --- | --- |
| KPMG Canada | Its career site's open jobs feed | High |
| Deloitte Canada | Its career site (two methods tried) | Medium |
| RBC, TD, BMO, CIBC, PwC, Manulife, Sun Life | Their Workday career sites | High (a board that moves is skipped and logged) |
| Adzuna | Free Application Programming Interface (API) | High |
| Job Bank (Government of Canada) | Search pages | Medium |
| Indeed, LinkedIn, Glassdoor, Google Jobs | The JobSpy library | Varies: these sites block automated access some days |
| Greenhouse and Lever boards | Open feeds | High |

The bottom line of every daily email lists how many postings each source returned, so you can
see when one stops working. To add or remove searches, places, employers or company boards, edit
`tracker/config.py` on GitHub. Nothing else needs to change.

### Match score (out of 100)

- Role: 40 for GRC, IT audit, cyber or SOC; 30 for network, IT support or retail tech
- Location: 20 if it is in your area for that category
- Level: 20 graduate or entry, 15 mid, 5 senior
- Target employer (Big 4, banks, big tech, government): 20

A **strong match** (star) is a target employer, or a top role in your area at graduate or entry
level. Strong matches push to your phone right away; everything else is in the morning email.

### Rules

- Postings you have not applied to are removed when their closing date passes, or when they are
  over 30 days old and no source has shown them for 14 days.
- Anything you applied to is never removed.
- A follow-up reminder fires when an application has had no stage change for 14 days.
- A deadline reminder fires when a new or saved posting closes within 3 days.

## Setup (one time, about 30 minutes)

### 1. Database (Supabase)

1. In your Supabase project, open **SQL Editor**, click **New query**, paste all of
   `supabase/schema.sql`, and click **Run**.
2. New query again: paste `supabase/seed.sql` and click **Run**. This loads your existing
   Deloitte, KPMG and PwC applications.
3. **Authentication > Users > Add user > Create new user**: your email and a password, with
   **Auto Confirm User** ticked. This is your dashboard login.
4. **Authentication > Sign In / Providers**: turn **off** "Allow new users to sign up", so nobody
   else can create an account.
5. **Project Settings > API Keys** (or **API**): note the **Project URL**, the **publishable** or
   **anon public** key (safe to share), and the **secret** or **service_role** key (never share).

### 2. Secrets (GitHub)

In the repository: **Settings > Secrets and variables > Actions > New repository secret**.
Add each of these:

| Name | Value |
| --- | --- |
| `SUPABASE_URL` | The Project URL |
| `SUPABASE_SERVICE_KEY` | The **secret** / service_role key |
| `ADZUNA_APP_ID` | From developer.adzuna.com |
| `ADZUNA_APP_KEY` | From developer.adzuna.com |
| `GMAIL_ADDRESS` | The Gmail account that sends the digest |
| `GMAIL_APP_PASSWORD` | The 16-character app password |
| `ALERT_EMAIL` | Where the digest goes |
| `NTFY_TOPIC` | Your ntfy topic name |

### 3. Dashboard (GitHub Pages)

1. Edit `docs/config.js` on GitHub and paste in the Project URL and the **publishable / anon** key.
2. **Settings > Pages**: Source **Deploy from a branch**, branch **main**, folder **/docs**, Save.
3. After a minute the dashboard is live at `https://<your-username>.github.io/<repo-name>/`.

### 4. First run

**Actions > Daily job scan > Run workflow.** It takes 15 to 30 minutes. After that it runs by
itself every morning.

## Running on your own computer

```
pip install -r requirements.txt
python -m tracker.main            # without Supabase settings this is a dry run: see data/dry_run.json
python -m tracker.main kpmg,adzuna   # only some sources
python -m pytest -q               # tests
```

To run against the real database, set the same values as the GitHub secrets as environment
variables first.
