<div align="center">
<img src="app/static/images/logo.png" alt="ModuleGo" width="150">
<br>

**A better way for Republic Polytechnic students to explore, search, compare, and review academic modules.**

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)

[![Live Demo](https://img.shields.io/badge/Live%20Demo-EC2-FF9900?style=flat-square&logo=amazonwebservices&logoColor=white)](http://ec2-52-77-236-110.ap-southeast-1.compute.amazonaws.com/)
[![Source Code](https://img.shields.io/badge/Source%20Code-GitHub-100000?style=flat-square&logo=github&logoColor=white)](https://github.com/xavlkh/ModuleGo)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)
</div>

---

## What is ModuleGo?

The official RP Module Viewer makes it hard to discover which diplomas offer a given module, compare modules side-by-side, or get peer feedback. ModuleGo fixes that.

It scrapes module data from the RP website, stores it in a database, and lets students search, compare, and review modules through a modern web interface.

## Features

- **Instant search** across 500+ modules with real-time filtering
- **Advanced filters** by school, diploma, rating, and active status
- **Side-by-side comparison** with AI-generated summaries (powered by Gemini)
- **Community reviews** with 1-5 star ratings and upvote/downvote
- **Bookmarks** — save modules you're interested in (server-side for logged-in users, local for guests)
- **GoBot chatbot** — ask questions about modules, careers, and diplomas in natural language
- **Career paths** mapped to modules, diplomas, and minors
- **Dark mode** with system theme detection
- **Responsive** across desktop, tablet, and mobile
- **Guest-to-account transfer** — your reviews and bookmarks follow you when you create an account

## Quick Start (Docker)

Docker is the recommended way to run ModuleGo.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

### Setup

1. Clone the repo:

```bash
git clone https://github.com/xavlkh/ModuleGo.git
cd ModuleGo
```

2. Copy `.env.example` to `.env` and fill in your credentials:

```
FLASK_SECRET_KEY=your-stable-random-secret
GEMINI_API_KEY=your-gemini-api-key
```

> [!NOTE]
> `GEMINI_API_KEY` enables AI-generated module comparisons and the chatbot. The app works without it — those features degrade gracefully.

3. Start the app:

```bash
docker compose up -d
```

This starts three containers:
- **app** — the Flask web server (port 80)
- **postgres** — the database
- **nginx** — reverse proxy in front of Flask

Visit `http://localhost` in your browser.

## Running Without Docker

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

> [!TIP]
> Without Docker, the app falls back to a local SQLite database automatically. No PostgreSQL setup needed for local development.

## Populating Data

ModuleGo ships with scraped module and diploma data in `app/static/local-data/data/`. To load this into PostgreSQL:

```bash
python seed_db.py
```

To re-scrape fresh data from the RP website:

```bash
cd app/static/local-data
python run_all.py
cd ../../
python seed_db.py
```

See `app/static/local-data/SCRAPING_GUIDE.md` for details on the scraping pipeline.

## Running Tests

```bash
python -m pytest -q
```

Tests use an in-memory SQLite database — no PostgreSQL credentials needed.

## Deploying to AWS EC2

ModuleGo can be deployed to AWS EC2 using Ansible for infrastructure and GitHub Actions for CI/CD.

### How It Works

- **GitHub Actions** builds Docker images on push to `master` (production) or `dev` (development)
- **GHCR** (GitHub Container Registry) stores the pre-built images
- **Ansible** provisions EC2 instances and pulls images from GHCR

### Prerequisites

- AWS account with an IAM user that has EC2 permissions
- Python 3.12+ with `boto3` (`pip install boto3`)
- Ansible (`pip install ansible`)
- SSH key pair for EC2 access

### First-Time Setup

1. **Provision the EC2 instance** (run once):

```bash
cd ansible
ansible-playbook -i inventory/prod.ini playbook.yml -e "ansible_host=YOUR_EC2_IP env=prod"
```

2. **Update the inventory file** with the EC2 public IP:

```ini
# inventory/prod.ini
[ec2]
modulego-prod ansible_host=YOUR_PROD_EC2_IP
```

3. **Create a GitHub repository secret:**

| Secret | Description |
|--------|-------------|
| `EC2_SSH_PRIVATE_KEY` | Private key content for SSH access to EC2 |

4. **Create GitHub environments:**

- Go to Settings > Environments > New environment
- Create `production` and `development` environments
- Add environment variable `EC2_IP` with the respective EC2 public IPs

5. **Enable GHCR:**

- Go to Settings > Actions > General > Workflow permissions
- Select **Read and write permissions**

### Deployment

Once configured, deployments happen automatically:

```bash
# Push to master → deploys to production (port 80)
git push origin master

# Push to dev → deploys to development (port 5001)
git push origin dev
```

### Manual Deployment

```bash
cd ansible
ansible-playbook -i inventory/prod.ini playbook.yml -e "ansible_host=YOUR_IP env=prod"
```

### Environment Variables

Edit the files in `ansible/group_vars/`:

- `all.yml` — shared settings (AWS region, instance type)
- `prod/all.yml` — production-specific (ports, image tags)
- `dev/all.yml` — development-specific

Secrets are passed via GitHub Secrets and extra vars (`-e`) at runtime.

## Project Structure

```
ModuleGo/
├── app.py                  Flask app, routes, API endpoints
├── auth_routes.py          Login, register, profile, password, delete account
├── user_model.py           User model with bcrypt password hashing
├── ownership.py            Guest cookie identity, ownership checks
├── db.py                   Database helpers (SQLite + PostgreSQL)
├── seed_db.py              Load scraped JSON into PostgreSQL
├── app/
│   ├── templates/          Jinja2 HTML templates
│   │   ├── modules/        Home, comparison, reviews, bookmarks pages
│   │   └── auth/           Login, register, profile pages
│   └── static/
│       ├── js/             Client-side JavaScript
│       ├── css/            Tailwind CSS
│       └── local-data/     Scraping pipeline and scraped JSON/CSV
├── tests/                  pytest test suite (SQLite, no PostgreSQL needed)
├── ansible/                EC2 provisioning and deployment playbooks
├── docker-compose.yml      Docker Compose config (app + postgres + nginx)
├── Dockerfile              Production Docker image
└── nginx.conf              Reverse proxy config
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask, Flask-Login, Flask-WTF, Flask-Limiter |
| Database | PostgreSQL 16 (production), SQLite (development/tests) |
| Frontend | Vanilla JavaScript, Tailwind CSS, Lucide Icons |
| AI | Google Gemini (module comparisons, chatbot) |
| Auth | Flask-Login + bcrypt (accounts), HMAC-SHA256 signed cookies (guests) |
| Deployment | Docker, Nginx, Ansible, GitHub Actions, AWS EC2 |
| Scraping | Playwright, Crawl4AI, BeautifulSoup |
