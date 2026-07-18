# Module Scraping Guide

## Quick Reference

### RP Module Synopsis API

**Endpoint:** `POST https://lcs.rp.edu.sg/RPModuleSynopsis/screenservices/RPModuleSynopsis/MainFlow/ModuleSynopsis/ScreenDataSetGetSynopsis?lXamMASFpg1bQfatzeulEg`

**Status:** Working (as of July 2026)

### Getting Auth Tokens

```bash
# 1. Open page
npx.cmd agent-browser open "https://lcs.rp.edu.sg/RPModuleSynopsis/"

# 2. Get CSRF token
npx.cmd agent-browser eval "document.cookie"
# Parse crf=... from nr2Users cookie

# 3. Trigger search to capture moduleVersion
npx.cmd agent-browser network requests --clear
npx.cmd agent-browser click "@e2"  # Search button
npx.cmd agent-browser network requests --filter "ScreenDataSet" --json
# Parse moduleVersion from postData
```

Or use `step1_get_tokens.py` in `scrape modules/` which automates this.

### Fetching Modules

```python
payload = {
    "versionInfo": {"moduleVersion": "{MV}", "apiVersion": "lXamMASFpg1bQfatzeulEg"},
    "viewName": "MainFlow.ModuleSynopsis",
    "screenData": {"variables": {
        "searchModuleCode": "C",  # Single letter or prefix
        "searchModuleDescription": "",  # BROKEN - don't use
        "StartIndex": 0,
        "MaxRecords": 500
    }},
    "inputParameters": {"StartIndex": 0, "MaxRecords": 500}
}
```

### Key Facts

- Empty search returns 0 results (must use code prefix)
- Name search (`searchModuleDescription`) is broken
- `Count` is at `data.Count` (not `data.List.Count`)
- Tokens expire per session (re-extract if 403)
- Use `npx.cmd` on Windows (not `npx`)
- API returns double-encoded UTF-8 (mojibake) — fixed in `scrape_all_modules.py`
- Also cleans: vertical tabs (`U+000B`), non-breaking spaces (`U+00A0`), zero-width spaces (`U+200B`)
- **Deduplication:** When same module code appears under multiple schools, `should_keep()` picks the one matching the prefix's owning school (defined in `PREFIX_SCHOOL`)

### Scripts

All scripts live in `scrape modules/`. Pipeline: **step1 → step2 → step3**

| Script | Purpose |
|--------|---------|
| `step1_get_tokens.py` | Refresh expired auth tokens |
| `step2_scrape_all_modules.py` | Main scraper — runs A-Z prefix iteration, outputs synopsis JSON + CSV |
| `step3_generate_comparison.py` | Reads synopsis JSON, generates comparison data (summary + suitable_for) |
| `scrape_diplomas.py` | Diploma page scraper (sitemap-based, BeautifulSoup) |

### Output

**step2 — `rp_modules_synopsis.json` / `.csv`** — 537 modules with:
- `module_code` — e.g. "C126"
- `module_name` — module title
- `synopsis` — full synopsis text
- `school_name` — full school name (e.g. "School of Applied Science")
- `school_abbr` — short code (SAS, SEG, SSH, SOH, SOI, STA, SBZ, General)
- `url` — RP module page URL
- `active` — always true

**step3 — `rp_modules_comparison.json` / `.csv`** — 537 rows with:
- `module_code`
- `summary` — features text (e.g. "Covers X through Y")
- `suitable_for` — interest text (e.g. "Students interested in X and Y")
