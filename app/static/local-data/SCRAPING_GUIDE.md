# Module Scraping Guide

## Quick Start

```bash
cd app/static/local-data
python run_all.py
```

Runs all 4 steps sequentially. Step 1 is skipped if `data/tokens.json` already exists. The `data/` directory is auto-created if missing.

### Prerequisites

- Python 3.12+ with dependencies from `requirements.txt`
- [Node.js](https://nodejs.org) 18+ and npm (for `agent-browser`, used by step 1)

## Pipeline

| Step | Script | Purpose |
|------|--------|---------|
| 1 | `scripts/step1_get_tokens.py` | Extract CSRF + moduleVersion tokens via agent-browser |
| 2 | `scripts/step2_scrape_all_modules.py` | Scrape modules from RP API (A-Z prefix iteration) |
| 3 | `scripts/step3_generate_comparison.py` | Generate comparison summary + suitable_for fields |
| 4 | `scripts/step4_scrape_diplomas.py` | Scrape diploma pages via BeautifulSoup |

## Output Files

All output is written to `data/` (gitignored).

| File | Description |
|------|-------------|
| `rp_modules_synopsis.json` | Modules with code, name, synopsis, school, URL |
| `rp_modules_comparison.json` | Summary + suitable_for text per module |
| `rp_diplomas_curriculum.json` | Diplomas with nested module lists |
| `tokens.json` | Auth tokens (auto-generated, session-based) |

CSV equivalents are generated alongside each JSON file.

## Module Schema

| Field | Example | Description |
|-------|---------|-------------|
| `module_code` | `"C126"` | Module code |
| `module_name` | `"Object-Oriented Programming"` | Module title |
| `synopsis` | `"This module covers..."` | Full synopsis text |
| `school_name` | `"School of Applied Science"` | Full school name |
| `school_abbr` | `"SAS"` | Short school code |
| `url` | `"https://www.rp.edu.sg/..."` | RP module page URL |

## Notes

- Tokens expire per session — re-extract if step 2 returns 403
- API returns double-encoded UTF-8 (mojibake) — fixed automatically in step 2
- When the same module code appears under multiple schools, `should_keep()` picks the one matching the prefix's owning school
