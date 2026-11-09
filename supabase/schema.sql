-- Job Tracker database schema for Supabase (PostgreSQL)
-- Paste this whole file into Supabase > SQL Editor > New query, then click Run.
-- Safe to run more than once.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------
-- Jobs: one row per unique posting (duplicates across sources are merged)
-- ---------------------------------------------------------------
create table if not exists public.jobs (
  id               uuid primary key default gen_random_uuid(),
  dedupe_key       text not null unique,
  title            text not null,
  company          text,
  location         text,
  category         text not null default 'fulltime'
                   check (category in ('fulltime', 'parttime', 'graduate')),
  job_type         text,
  level            text,
  salary           text,
  date_posted      date,
  closing_date     date,
  url              text,
  reference        text,
  source           text,
  sources          text[] not null default '{}',
  tags             text[] not null default '{}',
  score            integer not null default 0,
  strong           boolean not null default false,
  description      text,
  stage            text not null default 'new'
                   check (stage in ('new', 'saved', 'applied', 'assessment',
                                    'interview_1', 'interview_2', 'interview_final',
                                    'offer', 'accepted', 'rejected', 'withdrawn',
                                    'no_response', 'dismissed')),
  stage_changed_at timestamptz not null default now(),
  applied_at       timestamptz,
  notes            text not null default '',
  manual           boolean not null default false,
  first_seen       timestamptz not null default now(),
  last_seen        timestamptz not null default now(),
  followup_sent_at timestamptz,
  deadline_sent_at timestamptz
);

create index if not exists jobs_stage_idx      on public.jobs (stage);
create index if not exists jobs_first_seen_idx on public.jobs (first_seen desc);
create index if not exists jobs_category_idx   on public.jobs (category);

-- ---------------------------------------------------------------
-- Stage history: every stage change, with its date
-- ---------------------------------------------------------------
create table if not exists public.stage_history (
  id         bigint generated always as identity primary key,
  job_id     uuid not null references public.jobs (id) on delete cascade,
  stage      text not null,
  changed_at timestamptz not null default now()
);
create index if not exists stage_history_job_idx on public.stage_history (job_id, changed_at);

-- ---------------------------------------------------------------
-- Runs: one row per daily scan, so the dashboard can show "last checked"
-- ---------------------------------------------------------------
create table if not exists public.runs (
  id          bigint generated always as identity primary key,
  started_at  timestamptz not null default now(),
  finished_at timestamptz,
  found       integer default 0,
  added       integer default 0,
  removed     integer default 0,
  source_counts jsonb default '{}'::jsonb,
  errors      jsonb default '[]'::jsonb
);

-- ---------------------------------------------------------------
-- Triggers: record stage changes automatically
-- ---------------------------------------------------------------
create or replace function public.jobs_before_update()
returns trigger language plpgsql as $$
begin
  if tg_op = 'INSERT' then
    if new.stage not in ('new', 'saved', 'dismissed') and new.applied_at is null then
      new.applied_at := now();
    end if;
    return new;
  end if;
  if new.stage is distinct from old.stage then
    new.stage_changed_at := now();
    if new.stage = 'applied' and new.applied_at is null then
      new.applied_at := now();
    end if;
    -- a fresh stage gets a fresh follow-up clock
    new.followup_sent_at := null;
  end if;
  return new;
end $$;

create or replace function public.jobs_after_write()
returns trigger language plpgsql as $$
begin
  if tg_op = 'INSERT' or new.stage is distinct from old.stage then
    insert into public.stage_history (job_id, stage, changed_at)
    values (new.id, new.stage, now());
  end if;
  return new;
end $$;

drop trigger if exists jobs_before_update on public.jobs;
create trigger jobs_before_update before insert or update on public.jobs
  for each row execute function public.jobs_before_update();

drop trigger if exists jobs_after_write on public.jobs;
create trigger jobs_after_write after insert or update on public.jobs
  for each row execute function public.jobs_after_write();

-- ---------------------------------------------------------------
-- Row Level Security: only a signed-in user (you) can read or change data.
-- The daily scanner uses the secret key, which bypasses these rules.
-- ---------------------------------------------------------------
alter table public.jobs          enable row level security;
alter table public.stage_history enable row level security;
alter table public.runs          enable row level security;

drop policy if exists "owner full access" on public.jobs;
create policy "owner full access" on public.jobs
  for all to authenticated using (true) with check (true);

drop policy if exists "owner full access" on public.stage_history;
create policy "owner full access" on public.stage_history
  for all to authenticated using (true) with check (true);

drop policy if exists "owner read runs" on public.runs;
create policy "owner read runs" on public.runs
  for select to authenticated using (true);

grant select, insert, update, delete on public.jobs, public.stage_history to authenticated;
grant select on public.runs to authenticated;
