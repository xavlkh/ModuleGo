# ModuleGo — Agent Guide

## Quick Start
```bash
pip install -r requirements.txt
python app.py          # → http://127.0.0.1:5000
pytest tests/ -v       # SQLite in tmp_path, no Supabase needed
```

## Architecture
Flask serves Jinja templates + static JS/CSS. Three database backends: Supabase (production), PostgreSQL (self-hosted), SQLite (tests/fallback).

**Triple-branch pattern:** `ReviewRepository` and `VoteRepository` (app.py) each check `use_sqlite_reviews()` then `use_postgres()` — falling through to Supabase. Every review and vote method has SQLite, PostgreSQL, and Supabase paths. Don't add review/vote routes outside these classes.

**Module data flow:** `/api/modules` and `/api/courses` try Supabase first, fall back to local JSON files in `app/static/local-data/data/`. Career paths seed from the same JSON into SQLite/PostgreSQL on first boot.

## File Map
```
app.py                              Flask app, routes, ReviewRepository, VoteRepository, init_db()
app/data/                           SQLite runtime directory (modulego.db)
app/templates/base.html             Base layout (nav, dark mode, Lucide CDN)
app/templates/_macros.html          Reusable Jinja macros (navLinks, glassCard, modalOverlay, etc.)
app/templates/modules/index.html    Home
app/templates/modules/comparison.html  Side-by-side module comparison
app/templates/modules/reviews.html  Review dashboard
app/static/js/utils.js              escapeHtml, createStars, getOwnerToken, createModalController
app/static/js/data.js               Data loading, search, filtering
app/static/js/ui.js                 Home page, pagination, filter panel
app/static/js/detail.js             Module detail modal + review CRUD
app/static/js/comparison.js         Comparison with infinite scroll
app/static/js/reviews.js            Review dashboard + edit modal
app/static/js/gobot.js              Chatbot (Gemini-powered, calls /api/gobot)
app/static/js/bookmark.js           Favorites (localStorage)
app/static/js/share.js              Share functionality
app/static/css/app.css              oklch tokens, glassmorphism vars
app/static/local-data/              Scraping pipeline (scripts/, data/, run_all.py)
tests/                              pytest (SQLite only)
docs/                               spec + implementation plan
upsert_to_supabase.py               Imports scraped JSON into Supabase tables
Dockerfile                          Lean runtime image (no scraper stage)
docker-compose.yml                  PostgreSQL + Flask app
ansible/setup.yml                   One-time EC2 setup (install Docker, etc.)
ansible/deploy.yml                  Pull image + restart containers
```

## API Routes (app.py)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Home page |
| GET | `/comparison` | Comparison page |
| GET | `/reviews` | Reviews page |
| GET | `/api/modules` | All modules (Supabase → local JSON fallback) |
| GET | `/api/courses` | Courses/diplomas (Supabase → local JSON fallback) |
| GET | `/api/minors` | Minor programmes (Supabase → local JSON fallback) |
| GET | `/api/reviews` | All reviews |
| POST | `/api/reviews` | Create review |
| GET | `/api/reviews/<module_code>` | Reviews for module |
| PUT | `/api/reviews/<id>` | Update review (owner_token required) |
| DELETE | `/api/reviews/<id>` | Delete review (owner_token required) |
| GET | `/api/reviews/<id>/vote` | Get vote score + user's vote |
| POST | `/api/reviews/<id>/vote` | Add/update vote (1 or -1) |
| DELETE | `/api/reviews/<id>/vote` | Remove vote |
| POST | `/api/reviews/votes` | Bulk vote scores for multiple reviews |
| GET | `/api/ratings` | Aggregated ratings |
| POST | `/api/comparison/generate` | Gemini comparison summary |
| GET | `/api/career-paths` | Career path data |
| POST | `/api/gobot` | Chatbot endpoint |

## Key Patterns
- **Owner token:** UUID hex in localStorage, sent as `X-Owner-Token` header for review write operations
- **Dark mode:** `darkMode: 'class'` on `<html>`, FOUC prevention script in `<head>`. All dynamic HTML must include `dark:` Tailwind variants
- **Lucide icons:** Call `lucide.createIcons()` after injecting HTML with `data-lucide` attributes
- **Tailwind:** Use `:root` CSS custom properties (oklch colors, `--font-display`, glass shadows). Never hardcode arbitrary CSS
- **Macros first:** Check `_macros.html` before writing new UI components
- **CSRF:** All API endpoints are CSRF-exempt (auth via custom header instead of form tokens)
- **Rate limiting:** 200/hour default; 20/hour for review creation, 10/hour for review update/delete, 30/hour for voting, 15/hour for comparison generation

## Coding Style
- **Lean code:** No unnecessary abstractions, wrappers, or over-engineering. Write the simplest thing that works
- **Comments:** Only comment *why* behind non-obvious logic — never *what* the code does. Self-document through naming instead. If a comment just restates the code, delete it
- **Read this codebase for examples:** `app.py` ReviewRepository, `utils.js` escapeHtml — clean, direct, no fluff

## Environment (.env)
```
GEMINI_API_KEY=xxx                    # for /api/comparison/generate and /api/gobot
GEMINI_MODEL=gemini-3.1-flash-lite    # optional, default shown
DATABASE_URL=postgresql://...         # optional, use PostgreSQL instead of SQLite
DATABASE_PATH=/path/to/modulego.db    # optional, SQLite path (default: modulego.db in project root)
```

## Gotchas
- Scraped data lives in `app/static/local-data/data/` (gitignored). Run `cd app/static/local-data && python run_all.py` to regenerate, then `python upsert_to_supabase.py` to push to Supabase
- Module comparison data is generated on-demand via Gemini (`/api/comparison/generate`) — no longer pre-scraped
- Flask static folder is `app/static`, templates is `app/templates` (set in app.py:29-31)
- Tests use `monkeypatch` to swap `db_name` to a temp path — never hardcode DB paths
- GoBot uses Gemini API — respect `GEMINI_TIMEOUT_SECONDS = 25`
- Career paths seed from JSON into SQLite/PostgreSQL on first boot via `_seed_career_paths()` — if the DB already has rows, seeding is skipped
- Supabase free tier has query limits — ratings are aggregated in Python, not via SQL GROUP BY
