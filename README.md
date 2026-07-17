<div align="center">

# ModuleGo

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=flat-square&logo=supabase&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-533B78?style=flat-square&logo=bootstrap&logoColor=white)

[![Vercel](https://img.shields.io/badge/Live%20Demo-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)](https://module-go.vercel.app/)
[![GitHub](https://img.shields.io/badge/Source%20Code-GitHub-100000?style=flat-square&logo=github&logoColor=white)](https://github.com/xavlkh/ModuleGo)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

A better way for Republic Polytechnic students to explore, search, compare, and review academic modules.

[Features](#features) &bull; [Quick Start](#quick-start) &bull; [Deploy](#deploy-to-vercel) &bull; [API](#api-endpoints) &bull; [Tests](#automated-tests)

</div>

---

## Overview

The official RP Module Viewer makes it hard to discover which diplomas offer a given module, compare modules side-by-side, or get peer feedback. ModuleGo solves this with:

- **Instant search** across 400+ modules with client-side filtering
- **Diploma discovery** showing every program that includes a module
- **Side-by-side comparison** of module features and suitability
- **Community reviews** with 1-5 star ratings stored in Supabase

> [!TIP]
> Try the live demo at [module-go.vercel.app](https://module-go.vercel.app/).

## Features

- **Search** -- Real-time client-side search across module code, name, description, category, and school
- **Filter** -- Filter results by RP's seven schools
- **Details** -- View full descriptions, school, and all diplomas that include a module
- **Compare** -- Side-by-side comparison of two modules
- **Reviews** -- Create, read, edit, and delete validated 1-5 star reviews stored in Supabase
- **Rating summaries** -- View average ratings and review counts on module cards
- **Review dashboard** -- Search, filter, and manage reviews across all modules
- **Responsive** -- Works across desktop, tablet, and mobile viewports

## Quick Start

### Prerequisites

- Python 3.x
- Git
- A Supabase project with the `rp_modules` and `reviews` tables

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
> so the secret key stays on the server.

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
| `GET`  | `/api/modules` | List all modules from Supabase |
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
