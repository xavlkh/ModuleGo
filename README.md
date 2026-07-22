<div align="center">

# ModuleGo

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=flat-square&logo=supabase&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![Lucide](https://img.shields.io/badge/Lucide-F56565?style=flat-square&logo=lucide&logoColor=white)

[![Vercel](https://img.shields.io/badge/Live%20Demo-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)](https://module-go.vercel.app/)
[![GitHub](https://img.shields.io/badge/Source%20Code-GitHub-100000?style=flat-square&logo=github&logoColor=white)](https://github.com/xavlkh/ModuleGo)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

A better way for Republic Polytechnic students to explore, search, compare, and review academic modules.

[Features](#features) &bull; [Quick Start](#quick-start) &bull; [Self-Hosting](#self-hosting-guide) &bull; [API](#api-endpoints) &bull; [Tests](#automated-tests)

</div>

---

## Overview

The official RP Module Viewer makes it hard to discover which diplomas offer a given module, compare modules side-by-side, or get peer feedback. ModuleGo solves this with:

- **Instant search** across 537 modules with real-time client-side filtering and pagination
- **Advanced filtering** by school, diploma, minimum rating, and active status (modules in at least one diploma)
- **Diploma discovery** showing every program that includes a module
- **Side-by-side comparison** of module summary and suitability
- **Community reviews** with 1-5 star ratings stored in Supabase

> [!TIP]
> Try the live demo at [module-go.vercel.app](https://module-go.vercel.app/).

## Features

- **Search** -- Real-time client-side search across module code, name, synopsis, school, and comparison fields
- **Filter panel** -- Collapsible panel with school, diploma, rating, and active filters; state persisted in URL params
- **Pagination** -- Results split across pages with ellipsis navigation and keyboard arrow support
- **Details** -- View full synopsis, school, and all diplomas that include a module
- **Compare** -- Side-by-side comparison of two modules with search
- **Reviews** -- Create, read, edit, and delete validated 1-5 star reviews stored in Supabase
- **Rating summaries** -- View average ratings and review counts on module cards
- **Review dashboard** -- Search, filter, and manage reviews across all modules
- **Dark mode** -- Light/dark/system theme toggle persisted to localStorage
- **Responsive** -- Works across desktop, tablet, and mobile viewports

## Quick Start

### Prerequisites

- Python 3.12+
- Git
- A Supabase project with `rp_modules`, `rp_modules_comparision`, `rp_courses`, and `reviews` tables

### Setup

```bash
git clone https://github.com/xavlkh/ModuleGo.git
cd ModuleGo
git checkout dev
```

<details>
<summary>Windows</summary>

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

</details>

<details>
<summary>Linux / macOS</summary>

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

</details>

Copy `.env.example` to `.env` and fill in your Supabase credentials.

> [!IMPORTANT]
> The frontend never calls Supabase directly. All requests go through Flask
> so the secret key stays on the server. SQLite is used only for automated tests.

### Run

```bash
python app.py
```

Navigate to `http://127.0.0.1:5000`.

## Self-Hosting Guide

This guide covers setting up ModuleGo from scratch, including populating your Supabase database with module and diploma data.

### 1. Create Supabase Project

1. Sign up at [supabase.com](https://supabase.com) and create a new project
2. Note your **Project URL** and **Service Role Key** (Settings → API)

### 2. Create Database Tables

Run these SQL queries in the Supabase SQL Editor:

<details>
<summary>Click to expand SQL</summary>

```sql
-- Modules table
CREATE TABLE rp_modules (
    module_code text PRIMARY KEY,
    module_name text NOT NULL,
    module_description text,
    school text,
    link text
);

-- Modules comparison table
CREATE TABLE rp_modules_comparision (
    module_code text PRIMARY KEY,
    summary text,
    suitable_for text
);

-- Courses/diplomas table
CREATE TABLE rp_courses (
    course_code text PRIMARY KEY,
    course_name text NOT NULL,
    school_name text,
    school_abbr text,
    url text,
    general_modules jsonb DEFAULT '[]'::jsonb,
    major_modules jsonb DEFAULT '[]'::jsonb,
    discipline_modules jsonb DEFAULT '[]'::jsonb,
    elective_modules jsonb DEFAULT '[]'::jsonb,
    industry_modules jsonb DEFAULT '[]'::jsonb
);

-- Reviews table
CREATE TABLE reviews (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    module_code text NOT NULL,
    rating integer NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment text NOT NULL DEFAULT '',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz,
    owner_token text
);

CREATE INDEX idx_reviews_module_code ON reviews (module_code);

ALTER TABLE reviews
    ADD CONSTRAINT fk_reviews_module
    FOREIGN KEY (module_code) REFERENCES rp_modules(module_code);
```

</details>

### 3. Scrape Module Data

The scraping pipeline extracts module data from RP's internal API and diploma pages.

#### Prerequisites

- [Node.js](https://nodejs.org) 18+ and npm (for token extraction)
- Python dependencies already installed

#### Run the Pipeline

```bash
cd app/static/local-data
python run_all.py
```

This runs 4 steps sequentially:

| Step | Script | Purpose |
|------|--------|---------|
| 1 | `step1_get_tokens.py` | Extract CSRF + moduleVersion tokens via agent-browser |
| 2 | `step2_scrape_all_modules.py` | Scrape 537 modules from RP API |
| 3 | `step3_generate_comparison.py` | Generate comparison summary fields |
| 4 | `step4_scrape_diplomas.py` | Scrape diploma pages for curriculum data |

Step 1 is skipped if `data/tokens.json` already exists. The `data/` directory is auto-created if missing.

> [!NOTE]
> Tokens expire per session. Re-run the pipeline if step 2 returns 403 errors.

#### Import to Supabase

After scraping, import the CSV files into Supabase:

1. Go to Supabase → Table Editor → `rp_modules`
2. Click "Insert" → "Import from CSV"
3. Upload `app/static/local-data/data/rp_modules_synopsis.csv`
4. Repeat for `rp_modules_comparison.csv` → `rp_modules_comparision` table
5. Repeat for `rp_courses.csv` → `rp_courses` table

### 4. Configure Environment

Copy `.env.example` to `.env` and fill in:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-service-role-key
```

### 5. Run the App

```bash
python app.py
```

## Deploy to Vercel

1. Fork the repository on GitHub
2. Import the project in [Vercel](https://vercel.com/new)
3. Set `SUPABASE_URL` and `SUPABASE_SECRET_KEY` in the Vercel dashboard
4. Deploy

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/modules` | List all modules from Supabase with comparison fields |
| `GET`  | `/api/courses` | List all courses (diplomas) from Supabase |
| `GET`  | `/api/reviews` | List all reviews for the dashboard |
| `POST` | `/api/reviews` | Submit a validated review |
| `GET`  | `/api/reviews/<module_code>` | Get reviews for a module |
| `PUT`  | `/api/reviews/<review_id>` | Update a review |
| `DELETE` | `/api/reviews/<review_id>` | Delete a review |
| `GET`  | `/api/ratings` | Get average rating and count per module |

## Automated Tests

```bash
python -m pytest -q
```

Tests use an in-memory SQLite database and do not need Supabase credentials.

## Project Structure

```
ModuleGo/
├── app/
│   ├── templates/
│   │   ├── base.html              # Layout with navbar, footer, theme toggle
│   │   ├── _macros.html           # Shared Jinja macros
│   │   └── modules/
│   │       ├── index.html          # Home page with search + filter panel
│   │       ├── comparison.html     # Module comparison page
│   │       └── reviews.html        # Review dashboard
│   ├── static/
│   │   ├── css/app.css             # Tailwind CSS + glassmorphism tokens
│   │   ├── js/
│   │   │   ├── utils.js            # Shared utilities
│   │   │   ├── data.js             # Data loading + filtering
│   │   │   ├── ui.js               # Home page rendering + pagination
│   │   │   ├── detail.js           # Module detail modal + review CRUD
│   │   │   ├── comparison.js       # Comparison logic
│   │   │   └── reviews.js          # Review dashboard + CRUD
│   │   └── local-data/
│   │       ├── scripts/            # Scraping pipeline scripts
│   │       ├── data/               # Scraping output (gitignored)
│   │       └── run_all.py          # Run all scraping steps
│   └── data/                       # Supabase data (gitignored)
├── tests/                          # Pytest test suite
├── docs/                           # Design spec + implementation plan
├── app.py                          # Flask backend
├── requirements.txt                # Python dependencies
└── .env.example                    # Supabase credential template
```

## Git Workflow

- Development happens on the `dev` branch
- Never merge directly to `master` -- open a Pull Request first
- Do **not** commit `venv/`, `*.db`, or `app/static/local-data/data/` (`.gitignore` blocks these)
