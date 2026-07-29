<div align="center">
<img src="app/static/images/logo.png" alt="ModuleGo" width="150">
<br>

**A better way for Republic Polytechnic students to explore, search, compare, and review academic modules.**

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=flat-square&logo=supabase&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)](https://module-go.vercel.app/)
[![Source Code](https://img.shields.io/badge/Source%20Code-GitHub-100000?style=flat-square&logo=github&logoColor=white)](https://github.com/xavlkh/ModuleGo)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)
</div>

---

## About

The official RP Module Viewer makes it hard to discover which diplomas offer a given module, compare modules side-by-side, or get peer feedback. ModuleGo fixes that.

## What Makes It Different

- **Instant search** across 500+ modules with real-time client-side filtering
- **Advanced filtering** by school, diploma, rating, and active status
- **Side-by-side comparison** with AI-generated summaries via Gemini
- **Community reviews** with 1-5 star ratings
- **Career paths** mapped to modules, diplomas, and minors
- **Dark mode** with system theme detection
- **Responsive** across desktop, tablet, and mobile

## Self-Hosting (Docker)

Docker is the recommended way to run ModuleGo.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- A Supabase project (free tier works)

### Setup

1. Clone and enter the project:

```bash
git clone https://github.com/xavlkh/ModuleGo.git
cd ModuleGo
```

2. Copy `.env.example` to `.env` and fill in your credentials:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-service-role-key
GEMINI_API_KEY=your-gemini-api-key
```

> [!NOTE]
> `GEMINI_API_KEY` enables AI-generated module comparisons and the chatbot. The app works without it — those features degrade gracefully.

3. Start with Docker Compose:

```bash
docker compose up -d
```

This runs Flask via Gunicorn on port 5000, with a PostgreSQL container for local data.

> [!NOTE]
> The frontend never calls Supabase directly. All requests go through Flask so the secret key stays on the server.

### With Minikube (Kubernetes)

For local Kubernetes deployment (requires [minikube](https://minikube.sigs.k8s.io/) and [kubectl](https://kubernetes.io/docs/tasks/tools/)):

<details>
<summary>Linux / macOS</summary>

```bash
./deploy.sh
kubectl -n modulego port-forward svc/modulego 5000:5000
```

</details>

<details>
<summary>Windows (PowerShell)</summary>

```powershell
bash ./deploy.sh
kubectl -n modulego port-forward svc/modulego 5000:5000
```

> [!NOTE]
> `deploy.sh` is a bash script. On Windows, run it via Git Bash, WSL, or `bash` from the project root.

</details>

Then open `http://localhost:5000`.

### Without Docker

<details>
<summary>Linux / macOS</summary>

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

</details>

<details>
<summary>Windows (PowerShell)</summary>

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

</details>

Navigate to `http://127.0.0.1:5000`.

## Populating Data

ModuleGo needs module and diploma data in your Supabase database.

### Option A: Run the scraping pipeline

```bash
cd app/static/local-data
python run_all.py
```

Then upsert to Supabase:

```bash
cd ../../
python upsert_to_supabase.py
```

Requires Python 3.12+, Playwright, and crawl4ai. See `app/static/local-data/SCRAPING_GUIDE.md` for details.

### Option B: Import CSV manually

1. Run the scraping pipeline (above) to generate CSV files
2. In Supabase SQL Editor, create the tables (see `.env.example` for schema hints)
3. Import `rp_modules_synopsis.csv` → `rp_modules` and `rp_courses.csv` → `rp_courses`

## Running Tests

```bash
python -m pytest -q
```

Tests use an in-memory SQLite database — no Supabase credentials needed.
