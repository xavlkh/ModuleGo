# Module Scraping Guide

## Quick Start

```bash
cd app/static/local-data
python run_all.py
```

Runs all 5 steps sequentially. Step 1 is skipped if `data/tokens.json` already exists. The `data/` directory is auto-created if missing.

### Prerequisites

- Python 3.12+ with dependencies from `requirements.txt`
- Python [Playwright](https://playwright.dev/python/) and either Google Chrome or Playwright Chromium
- [crawl4ai](https://github.com/unclecode/crawl4ai) for steps 3–4 (`pip install crawl4ai && crawl4ai-setup`)

## Pipeline

| Step | Script | Purpose |
|------|--------|---------|
| 1 | `scripts/step1_get_tokens.py` | Extract CSRF + moduleVersion tokens via Playwright |
| 2 | `scripts/step2_scrape_all_modules.py` | Scrape modules from RP API (A-Z prefix iteration) |
| 3 | `scripts/step3_scrape_diplomas.py` | Scrape diploma pages via crawl4ai + BeautifulSoup |
| 4 | `scripts/step4_scrape_minors.py` | Scrape minor programmes via crawl4ai |
| 5 | `scripts/step5_generate_career_paths.py` | Generate career path data from modules, diplomas, and minors |

## Output Files

All output is written to `data/` (gitignored).

| File | Description |
|------|-------------|
| `rp_modules_synopsis.json` | Modules with code, name, synopsis, school, URL |
| `rp_courses.json` | Diplomas with nested module lists |
| `rp_minors.json` | Minor programmes with module lists and eligibility |
| `rp_career_paths.json` | Career paths with matched modules and keywords |
| `tokens.json` | Auth tokens (auto-generated, session-based) |

CSV equivalents are generated alongside each JSON file.

## Module Schema

| Field | Example | Description |
|-------|---------|-------------|
| `module_code` | `"C126"` | Module code |
| `module_name` | `"Object-Oriented Programming"` | Module title |
| `synopsis` | `"This module covers..."` | Full synopsis text |
| `school_name` | `"School of Applied Science"` | Full school name (General for G/P prefix) |
| `school_abbr` | `"SAS"` | Short school code |
| `url` | `"https://www.rp.edu.sg/..."` | RP module page URL (empty if no page exists) |

## Minor Programme Schema

| Field | Example | Description |
|-------|---------|-------------|
| `minor_type` | `"Broad-Based"` | Programme category |
| `minor_name` | `"Minor in Business"` | Programme name |
| `url` | `"https://www.rp.edu.sg/..."` | RP minor programme page URL |
| `modules` | `[{"code": "B110", "name": "..."}]` | Required modules |
| `eligibility` | `"RP students from all Diplomas except..."` | Who can apply |

## Notes

- Tokens expire per session — re-extract if step 2 returns 403
- API returns double-encoded UTF-8 (mojibake) — fixed automatically in step 2
- When the same module code appears under multiple schools, `should_keep()` picks the one matching the prefix's owning school
- G/P prefix modules are always assigned to "General" school regardless of API response
- Module URLs are validated against the RP sitemap — only modules with actual pages get URLs
- "School of Technology for the Arts" is normalized to "School of Technology for Arts, Media and Design"

## Importing to Supabase

After scraping, upsert the JSON output to Supabase:

```bash
cd ../../  # project root
python upsert_to_supabase.py
```

Requires `SUPABASE_URL` and `SUPABASE_SECRET_KEY` in `.env`. Reads the JSON files from `data/` and upserts to `rp_modules` and `rp_courses`.

## Automated Pipeline

The scraping pipeline runs automatically via GitHub Actions every Sunday at 2am UTC. It can also be triggered manually from the Actions tab.

The workflow (`.github/workflows/scrape.yml`) installs Python + Playwright Chromium, runs `run_all.py`, then `upsert_to_supabase.py`. Requires `SUPABASE_URL` and `SUPABASE_SECRET_KEY` as repository secrets.

## Visible Browser Mode

Playwright runs headless by default. To watch the token extraction in a visible browser:

```powershell
$env:PLAYWRIGHT_HEADED = "true"
python run_all.py
Remove-Item Env:PLAYWRIGHT_HEADED
```
