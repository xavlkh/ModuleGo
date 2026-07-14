<div align="center">

# ModuleGo

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-533B78?style=flat-square&logo=bootstrap&logoColor=white)

[![Vercel](https://img.shields.io/badge/Live%20Demo-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)](https://module-go.vercel.app/)
[![GitHub](https://img.shields.io/badge/Source-Code-100000?style=flat-square&logo=github&logoColor=white)](https://github.com/xavlkh/ModuleGo)

A better way for Republic Polytechnic students to explore, search, compare, and review academic modules.

</div>

---

## Features

- **Search** -- Real-time client-side search across module code, name, description, category, and school with relevance ranking
- **Filter** -- Filter results by RP's seven schools (Applied Science, Engineering, Infocomm, etc.)
- **Details** -- View full descriptions, school, and all diplomas that include a module
- **Compare** -- Side-by-side comparison of two modules (code, name, school, features, suitability)
- **Reviews** -- Create, read, edit, and delete validated 1-5 star reviews in SQLite
- **Rating summaries** -- View average ratings and review counts directly on module cards
- **Review dashboard** -- Search, filter, and manage reviews across all modules
- **Responsive** -- Works across desktop, tablet, and mobile viewports

## Quick Start

### Prerequisites

- Python 3.x
- Git

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

### Run

```bash
python app.py
```

Navigate to `http://127.0.0.1:5000`. The SQLite database (`modulego.db`) is created automatically on first run.

> [!NOTE]
> If a Windows Defender Firewall prompt appears, check the **Private** box only.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla JavaScript, HTML5, Bootstrap 5.3.3 |
| Backend | Python 3.x, Flask 3.0.3 |
| Database | SQLite (auto-initialized) |
| Data | Static JSON files |

## Project Structure

```
ModuleGo/
├── app.py                          # Flask backend
├── app/
│   ├── static/
│   │   ├── css/styles.css          # Custom styling (RP brand theme)
│   │   ├── data/
│   │   │   ├── rp-modules-final.json
│   │   │   └── diploma.json
│   │   └── js/
│   │       ├── app.js              # Home page initialization
│   │       ├── data.js             # Data loading and search logic
│   │       ├── search.js           # Search input and filter handling
│   │       ├── ui.js               # Module card rendering
│   │       ├── detail.js           # Module detail modal and reviews
│   │       ├── comparison.js       # Comparison page logic
│   │       └── reviews.js          # Review dashboard logic
│   └── templates/
│       ├── base.html               # Layout template
│       └── modules/
│           ├── index.html          # Main search page
│           ├── comparison.html     # Comparison page
│           └── reviews.html        # Review dashboard
├── docs/                           # Design specs and implementation plans
├── tests/
├── requirements.txt
└── vercel.json
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/reviews` | List all reviews for the dashboard |
| `POST` | `/api/reviews` | Submit a validated review |
| `GET`  | `/api/reviews/<module_code>` | Get reviews for a module |
| `PUT`  | `/api/reviews/<review_id>` | Update a review |
| `DELETE` | `/api/reviews/<review_id>` | Delete a review |
| `GET`  | `/api/ratings` | Get average rating and count per module |

## Automated Tests

Install the development dependencies and run the API test suite:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

GitHub Actions runs the same tests automatically for pushes and pull requests targeting `dev` or `master`.

## Git Workflow

- Do **not** commit `venv/` or `*.db` -- the `.gitignore` is already configured to block these
- Never merge directly to `master`. Open a Pull Request and have a teammate review first
- Development happens on the `dev` branch

### Optional: Regenerate Comparison Fields

If you modify the module data and need to regenerate the `features` and `suitableFor` fields:

```bash
node app/static/js/generate-comparison-fields.js
```

Requires Node.js. This is a one-off data processing step.
