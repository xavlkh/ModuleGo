# ModuleGo — Agent Guide

## Quick Start
```bash
pip install -r requirements.txt
python wsgi.py          # → http://127.0.0.1:5000
pytest tests/ -v       # SQLite in tmp_path, no PostgreSQL needed
```

## Architecture
Flask serves Jinja templates + static JS/CSS. Two database backends: PostgreSQL (production) and SQLite (tests/local dev fallback).

**App factory pattern:** `app/__init__.py` contains `create_app()`. Blueprints in `app/routes/`. Repositories and business logic in `app/core.py`.

**Dual-branch pattern:** `ReviewRepository` and `VoteRepository` (`app/core.py`) each check `use_sqlite_reviews()` then `use_postgres()`. Every review and vote method has SQLite and PostgreSQL paths. Don't add review/vote routes outside these classes.

**Module data flow:** `/api/modules` and `/api/courses` try PostgreSQL first, fall back to local JSON files in `app/static/local-data/data/`. Career paths seed from the same JSON into SQLite/PostgreSQL on first boot.

## File Map
```
app/__init__.py         App factory (create_app), backward-compat exports
app/db.py               DB connections, row mappers, init_db schema
app/models.py           Flask-Login User model with bcrypt (SQLite + PostgreSQL)
app/core.py             Ownership, repositories, validation, Gemini, GoBot, data loading
app/routes/auth.py      Auth blueprint (register, login, logout, profile, password, delete)
app/routes/api.py       API blueprint (modules, reviews, votes, bookmarks, ownership, comparison, gobot)
app/routes/pages.py     Page routes (/, /comparison, /bookmarks, /reviews)
wsgi.py                 WSGI entry point for Gunicorn (python wsgi.py for dev)
seed_db.py              PostgreSQL seed script (creates tables, upserts scraped JSON)
app/templates/base.html             Base layout (nav, dark mode, Lucide CDN)
app/templates/_macros.html          Reusable Jinja macros (navLinks, glassCard, modalOverlay, etc.)
app/templates/modules/index.html    Home
app/templates/modules/comparison.html  Side-by-side module comparison
app/templates/modules/reviews.html  Review dashboard
app/templates/modules/bookmarks.html  Bookmarked modules page
app/templates/auth/register.html    Registration form
app/templates/auth/login.html       Login form
app/templates/auth/profile.html     Account profile page
app/static/js/utils.js              escapeHtml, createStars, ownership, profile, share
app/static/js/data.js               Data loading, search, filtering
app/static/js/ui.js                 Home page, pagination, filter panel
app/static/js/detail.js             Module detail modal + review CRUD
app/static/js/comparison.js         Comparison with infinite scroll
app/static/js/reviews.js            Review dashboard + edit modal
app/static/js/gobot.js              Chatbot (Gemini-powered, calls /api/gobot)
app/static/js/bookmark.js           BookmarkManager + bookmarks page
app/static/css/app.css              oklch tokens, glassmorphism vars
app/static/local-data/              Scraping pipeline (scripts/, data/, run_all.py)
tests/                              pytest (SQLite only)
docs/                               spec + implementation plan
Dockerfile                          Lean runtime image (no scraper stage)
docker-compose.yml                  PostgreSQL + Flask app
ansible/setup.yml                   One-time EC2 setup (install Docker, etc.)
ansible/deploy.yml                  Pull image + restart containers
```

## API Routes
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Home page |
| GET | `/comparison` | Comparison page |
| GET | `/bookmarks` | Bookmarked modules page |
| GET | `/reviews` | Reviews page |
| GET | `/api/modules` | All modules (PostgreSQL → local JSON fallback) |
| GET | `/api/courses` | Courses/diplomas (PostgreSQL → local JSON fallback) |
| GET | `/api/minors` | Minor programmes (PostgreSQL → local JSON fallback) |
| GET | `/api/reviews` | All reviews |
| POST | `/api/reviews` | Create review |
| GET | `/api/reviews/<module_code>` | Reviews for module |
| PUT | `/api/reviews/<id>` | Update review (ownership required) |
| DELETE | `/api/reviews/<id>` | Delete review (ownership required) |
| GET | `/api/reviews/<id>/vote` | Get vote score + user's vote |
| POST | `/api/reviews/<id>/vote` | Add/update vote (1 or -1) |
| DELETE | `/api/reviews/<id>/vote` | Remove vote |
| POST | `/api/reviews/votes` | Bulk vote scores for multiple reviews |
| GET | `/api/ratings` | Aggregated ratings |
| POST | `/api/comparison/generate` | Gemini comparison summary |
| GET | `/api/career-paths` | Career path data |
| POST | `/api/gobot` | Chatbot endpoint |
| GET | `/api/bookmarks` | List account bookmarks |
| PUT | `/api/bookmarks/<module_code>` | Add bookmark |
| DELETE | `/api/bookmarks/<module_code>` | Remove bookmark |
| DELETE | `/api/bookmarks` | Clear all bookmarks |
| GET | `/api/ownership/pending` | Count claimable guest activity |
| POST | `/api/ownership/claim` | Transfer guest activity to account |

## Auth Routes (app/routes/auth.py)
| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/register` | Account creation |
| GET/POST | `/login` | Email/password login |
| POST | `/logout` | Clear session |
| GET/POST | `/profile` | Account settings |
| POST | `/profile/password` | Change password |
| POST | `/profile/delete/verify` | Issue deletion confirmation token |
| POST | `/profile/delete` | Delete account |
| GET | `/api/auth/me` | Current user JSON |

## Key Patterns
- **Ownership:** Signed guest cookies (HMAC-SHA256, 30-day) for anonymous users; Flask-Login sessions for accounts. `identity_owns()` checks both.
- **Dark mode:** `darkMode: 'class'` on `<html>`, FOUC prevention script in `<head>`. All dynamic HTML must include `dark:` Tailwind variants
- **Lucide icons:** Call `lucide.createIcons()` after injecting HTML with `data-lucide` attributes
- **Tailwind:** Use `:root` CSS custom properties (oklch colors, `--font-display`, glass shadows). Never hardcode arbitrary CSS
- **Macros first:** Check `_macros.html` before writing new UI components
- **CSRF:** All API endpoints are CSRF-exempt (auth via custom header instead of form tokens)

## Coding Style
- **Lean code:** No unnecessary abstractions, wrappers, or over-engineering. Write the simplest thing that works
- **Comments:** Only comment *why* behind non-obvious logic — never *what* the code does. Self-document through naming instead. If a comment just restates the code, delete it
- **Read this codebase for examples:** `app/core.py` ReviewRepository, `utils.js` escapeHtml — clean, direct, no fluff

## Environment (.env)
```
FLASK_SECRET_KEY=xxx                    # required — signs sessions and cookies
GEMINI_API_KEY=xxx                    # for /api/comparison/generate and /api/gobot
GEMINI_MODEL=gemini-3.1-flash-lite    # optional, default shown
DATABASE_URL=postgresql://...         # optional, use PostgreSQL instead of SQLite
```

## Gotchas
- Scraped data lives in `app/static/local-data/data/` (gitignored). Run `cd app/static/local-data && python run_all.py` to regenerate, then `python seed_db.py` to load into PostgreSQL
- Module comparison data is generated on-demand via Gemini (`/api/comparison/generate`)
- Tests use `monkeypatch` to swap `db_name` to a temp path — never hardcode DB paths
- GoBot uses Gemini API — respect `GEMINI_TIMEOUT_SECONDS = 25`
- Career paths seed from JSON into SQLite/PostgreSQL on first boot — if the DB already has rows, seeding is skipped
