# ModuleGo

A web application for Republic Polytechnic students to explore, search, compare, and review academic modules. Built as an improved alternative to the official RP Module viewer.

## Features

- **Module Search** -- Real-time client-side search across module code, name, description, category, and school with relevance ranking
- **School Filtering** -- Filter results by RP's seven schools (Applied Science, Engineering, Infocomm, etc.)
- **Module Details** -- View full descriptions, school, and all diplomas that include a module
- **Module Comparison** -- Side-by-side comparison of two modules (code, name, school, features, suitability)
- **Student Reviews** -- Submit 1-5 star ratings and comments, persisted in a SQLite database
- **Responsive Design** -- Works across desktop, tablet, and mobile viewports

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla JavaScript, HTML5, Bootstrap 5.3.3 |
| Backend | Python 3.x, Flask 3.0.3 |
| Database | SQLite (auto-initialized) |
| Data | Static JSON files |

## Getting Started

### Prerequisites

- Python 3.x
- Git

### Setup

**1. Clone the repository**

```bash
git clone https://github.com/xavlkh/ModuleGo.git
cd ModuleGo
git checkout dev
```

**2. Create and activate a virtual environment**

<details>
<summary>Windows (VS Code)</summary>

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

**3. Run the server**

```bash
python app.py
```

The SQLite database (`modulego.db`) is created automatically on first run. Navigate to `http://127.0.0.1:5000` in your browser.

> [!NOTE]
> If a Windows Defender Firewall prompt appears, check the **Private** box only.

### Optional: Regenerate Comparison Fields

If you modify the module data and need to regenerate the `features` and `suitableFor` fields:

```bash
node app/static/js/generate-comparison-fields.js
```

Requires Node.js. This is a one-off data processing step.

## Project Structure

```
ModuleGo/
├── app.py                          # Flask backend: REST API for reviews
├── app/
│   ├── data/
│   │   ├── rp-modules-final.json   # Module dataset
│   │   └── diploma.json            # Diploma-to-module mapping
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css          # Custom styling (RP brand theme)
│   │   └── js/
│   │       ├── app.js              # Home page initialization
│   │       ├── data.js             # Data loading and search logic
│   │       ├── search.js           # Search input and filter handling
│   │       ├── ui.js               # Module card rendering
│   │       ├── detail.js           # Module detail modal and reviews
│   │       ├── comparison.js       # Comparison page logic
│   │       └── generate-comparison-fields.js  # Data processing utility
│   └── templates/
│       ├── base.html               # Base layout template
│       └── modules/
│           ├── index.html          # Main search and browse page
│           └── comparison.html     # Module comparison page
├── docs/
│   ├── spec-modulego-design.md     # Design specification
│   └── plan-modulego-implementation.md  # Implementation plan
├── tests/                          # Test files
├── requirements.txt                # Python dependencies
└── .env.example                    # Environment config template
```

## Git Workflow

- Do **not** commit `venv/` or `*.db` -- the `.gitignore` is already configured to block these
- Never merge directly to `main`. Open a Pull Request and have a teammate review first
- Development happens on the `dev` branch

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/reviews` | Submit a new review (rating + optional comment) |
| `GET` | `/api/reviews/<module_code>` | Retrieve reviews for a specific module |
