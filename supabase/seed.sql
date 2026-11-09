-- Your existing applications, so the tracker starts with them.
-- Paste into Supabase > SQL Editor and click Run, AFTER schema.sql. Safe to run twice.
-- Check each stage on the dashboard afterwards and correct any that are wrong.

insert into public.jobs (dedupe_key, title, company, location, category, level, url, reference,
                         source, sources, tags, score, strong, stage, manual, notes)
values
  ('seed:deloitte:134475', 'Tech & Transformation - Cyber - Strategy & Transformation - New Grad 2027',
   'Deloitte', 'Toronto, ON', 'graduate', 'graduate',
   'https://careers.deloitte.ca/search/?q=134475&locale=en_US', '134475', 'manual', '{manual}',
   '{Cyber,GRC}', 100, true, 'applied', true, 'Imported from earlier notes. Check the stage.'),
  ('seed:deloitte:134491', 'Tech & Transformation - Cyber - Digital Trust & Privacy - New Grad 2027',
   'Deloitte', 'Toronto, ON', 'graduate', 'graduate',
   'https://careers.deloitte.ca/search/?q=134491&locale=en_US', '134491', 'manual', '{manual}',
   '{Cyber,GRC}', 100, true, 'applied', true, 'Usaamah Saeed''s team. Imported from earlier notes.'),
  ('seed:deloitte:134255', 'Consultant - IT Audit & Assurance - New Grad - 2027',
   'Deloitte', 'Toronto, ON', 'graduate', 'graduate',
   'https://careers.deloitte.ca/search/?q=134255&locale=en_US', '134255', 'manual', '{manual}',
   '{"IT Audit"}', 100, true, 'applied', true, 'Imported from earlier notes. Check the stage.'),
  ('seed:kpmg:33461', 'Management Consulting GTA: Early Graduate/Full Time Consultant, September ''27',
   'KPMG', 'Toronto, ON', 'graduate', 'graduate',
   'https://careers.kpmg.ca/jobs/33461', '33461', 'manual', '{manual}',
   '{"Risk & Tech"}', 90, true, 'applied', true, 'Imported from earlier notes. Check the stage.'),
  ('seed:kpmg:33315', 'Risk Services - Technology Risk Services',
   'KPMG', 'Toronto, ON', 'graduate', 'graduate',
   'https://careers.kpmg.ca/jobs/33315', '33315', 'manual', '{manual}',
   '{GRC}', 100, true, 'applied', true, 'Chosen over KPMG IT Audit (BC, ref 33445). Check the stage.'),
  ('seed:pwc:risk-services-2027', 'Risk Services (Non-CPA) - September 2027',
   'PwC', 'Toronto, ON (also Ottawa, Calgary, Vancouver)', 'graduate', 'graduate',
   'https://www.pwc.com/ca/en/careers.html', '', 'manual', '{manual}',
   '{GRC}', 100, true, 'saved', true, 'Was considering this. Pick the office and apply.')
on conflict (dedupe_key) do nothing;
