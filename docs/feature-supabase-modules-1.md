---
goal: Connect ModuleGo to Supabase for loading RP module data
version: 1.0
date_created: 2026-07-14
last_updated: 2026-07-14
status: 'Planned'
tags: ['feature', 'supabase', 'migration']
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

Currently, the app tries to load module data from a local JSON file (`rp-modules-final.json`) that does not exist. The user wants to load modules from their Supabase `rp_modules` table instead, both locally and on Vercel. The Supabase credentials are already in `.env`.

## 1. Requirements & Constraints

- **REQ-001**: Load module data from Supabase `rp_modules` table instead of a local JSON file
- **REQ-002**: Must work both locally and on Vercel
- **REQ-003**: Supabase credentials (`SUPABASE_URL`, `SUPABASE_KEY`) are in `.env`
- **REQ-004**: The existing diploma data (`diploma.json`) remains loaded from local static files
- **REQ-005**: The existing REVIEWS API (Flask endpoints) must continue to work
- **CON-001**: Frontend JS cannot directly call Supabase (no anon key exposure); must go through Flask API
- **CON-002**: Module fields used by frontend: `code`, `name`, `school`, `category`, `description`, `url`, `features`, `suitableFor`, `source`

## 2. Implementation Steps

### Implementation Phase 1: Update Flask backend to always initialize Supabase and serve modules

- GOAL-001: Make Supabase available in all environments and add a `/api/modules` endpoint

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | In `app.py`: Remove the `IS_VERCEL` conditional around Supabase init. Always load `SUPABASE_URL` and `SUPABASE_KEY` from env and call `create_client()`. Keep SQLite `init_db()` only for local reviews fallback. | | |
| TASK-002 | In `app.py`: Add `GET /api/modules` endpoint that queries `supabase.table("rp_modules").select("*").execute()` and returns the data as JSON. | | |
| TASK-003 | In `app.py`: Update existing REVIEWS endpoints to use the always-initialized `supabase` client instead of the conditionally-defined one. | | |

### Implementation Phase 2: Update frontend to fetch modules from Flask API

- GOAL-002: Replace the broken local JSON fetch with an API call to Flask

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-004 | In `app/static/js/data.js`: Change `loadData()` to fetch from `/api/modules` instead of `/static/data/rp-modules-final.json`. Keep the `diploma.json` fetch as-is. | | |

### Implementation Phase 3: Verify and test

- GOAL-003: Ensure everything works end-to-end

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-005 | Run the Flask app locally and verify modules load from Supabase. | | |
| TASK-006 | Verify the comparison page still works (it also calls `DataManager.loadData()`). | | |
| TASK-007 | Verify reviews API still works (POST and GET). | | |

## 3. Alternatives

- **ALT-001**: Use Supabase JS client directly in the frontend — Rejected because it would expose the Supabase anon key in the browser.
- **ALT-002**: Keep the local JSON file approach and just add the missing file — Rejected because the user explicitly wants Supabase as the data source.
- **ALT-003**: Use server-side rendering to embed module data in HTML — Rejected because the existing JS-based search/filter UI would need a full rewrite.

## 4. Dependencies

- **DEP-001**: `supabase` Python package (already in `requirements.txt` as `supabase==2.15.1`)
- **DEP-002**: `python-dotenv` (already in `requirements.txt`)
- **DEP-003**: Supabase project with `rp_modules` table containing module data with columns: `code`, `name`, `school`, `category`, `description`, `url`, `features`, `suitableFor`, `source`

## 5. Files

- **FILE-001**: `app.py` — Add Supabase init for all environments, add `/api/modules` endpoint, clean up REVIEWS endpoints
- **FILE-002**: `app/static/js/data.js` — Change module data source from local JSON to `/api/modules`

## 6. Testing

- **TEST-001**: Run `python app.py` locally and visit `http://127.0.0.1:5000` — modules should load and display
- **TEST-002**: Visit `http://127.0.0.1:5000/api/modules` — should return JSON array of modules
- **TEST-003**: Search and filter functionality on the home page should work
- **TEST-004**: Comparison page should load modules and allow selecting two to compare
- **TEST-005**: POST a review via the detail modal and verify it saves

## 7. Risks & Assumptions

- **RISK-001**: The `rp_modules` Supabase table may have different column names than expected — the API response must match what the frontend JS expects (`code`, `name`, `school`, etc.)
- **ASSUMPTION-001**: The Supabase table columns use uppercase or lowercase names that match the frontend expectations — TASK-005 will verify this and adjust if needed
- **ASSUMPTION-002**: The Supabase credentials in `.env` are valid and the table has data

## 8. Related Specifications / Further Reading

- [Supabase Python Client Docs](https://supabase.com/docs/reference/python/introduction)
- Current `app.py` structure: `app.py:15-33` (Supabase/SQLite conditional init)
- Current `data.js` broken fetch: `app/static/js/data.js:10`
