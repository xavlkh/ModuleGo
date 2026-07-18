<div align="center">

# ModuleGo

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=flat-square&logo=supabase&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![Lucide](https://img.shields.io/badge/Lucide-F56565?style=flat-square&logo=lucide&logoColor=white)

[![Vercel](https://img.shields.io/badge/Live%20Demo-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)](https://module-go.vercel.app/)
[![GitHub](https://img.shields.io/badge/Source%20Code-GitHub-100000?style=flat-square&logo=github&logoColor=white)](https://github.com/xavlkh/ModuleGo)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

A better way for Republic Polytechnic students to explore, search, compare, and review academic modules.

[Features](#features) &bull; [Quick Start](#quick-start) &bull; [Deploy](#deploy-to-vercel) &bull; [API](#api-endpoints) &bull; [Tests](#automated-tests)

</div>

---

## Overview

The official RP Module Viewer makes it hard to discover which diplomas offer a given module, compare modules side-by-side, or get peer feedback. ModuleGo solves this with:

- **Instant search** across 500+ modules with real-time client-side filtering and pagination
- **Diploma discovery** showing every program that includes a module
- **Side-by-side comparison** of module features and suitability with infinite scroll search
- **Community reviews** with 1-5 star ratings stored in Supabase

> [!TIP]
> Try the live demo at [module-go.vercel.app](https://module-go.vercel.app/).

## Features

- **Search** -- Real-time client-side search across module code, name, synopsis, school, and comparison fields
- **Filter** -- Filter results by RP's seven schools
- **Pagination** -- Results split across pages with ellipsis navigation and keyboard arrow support
- **Details** -- View full synopsis, school, and all diplomas that include a module
- **Compare** -- Side-by-side comparison of two modules with infinite scroll search
- **Reviews** -- Create, read, edit, and delete validated 1-5 star reviews stored in Supabase
- **Rating summaries** -- View average ratings and review counts on module cards
- **Review dashboard** -- Search, filter, and manage reviews across all modules
- **Dark mode** -- Light/dark/system theme toggle persisted to localStorage
- **Responsive** -- Works across desktop, tablet, and mobile viewports

## Quick Start

### Prerequisites

- Python 3.x
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

## Deploy to Vercel

1. Fork the repository on GitHub
2. Import the project in [Vercel](https://vercel.com/new)
3. Set `SUPABASE_URL` and `SUPABASE_KEY` in the Vercel dashboard
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
python -m pip install -r requirements.txt
python -m pytest -q
```

Tests use an in-memory SQLite database and do not need Supabase credentials. GitHub Actions runs the same suite for pushes and PRs targeting `dev` or `master`.

## Git Workflow

- Development happens on the `dev` branch
- Never merge directly to `master` -- open a Pull Request first
- Do **not** commit `venv/` or `*.db` (`.gitignore` blocks these)
