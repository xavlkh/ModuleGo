<div align="center">
<img src="app/static/images/logo.png" alt="ModuleGo" width="150">

**A better way for RP students to explore, compare, and review modules.**

[![Live Demo](https://img.shields.io/badge/%F0%9F%9A%80%20Live%20Demo-EC2-FF9900?style=for-the-badge&logo=amazonwebservices&logoColor=white)](http://ec2-47-130-46-184.ap-southeast-1.compute.amazonaws.com/)

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

</div>

---

## What is ModuleGo? 🤔

The official RP Module Viewer makes it hard to discover which diplomas offer a given module, compare modules side-by-side, or get peer feedback. **ModuleGo fixes that.**

It scrapes module data from the RP website, stores it in a database, and lets students search, compare, and review modules through a modern web interface.

## ✨ Features

| Feature | What it does |
|---------|--------------|
| 🔍 **Instant Search** | Search 500+ modules in real-time |
| 🎓 **Advanced Filters** | Filter by school, diploma, rating, and active status |
| ⚖️ **Side-by-Side Compare** | Compare two modules with AI-generated summaries |
| ⭐ **Community Reviews** | Rate modules 1-5 stars, leave comments, upvote/downvote |
| 🔖 **Bookmarks** | Save modules you like (syncs across devices when logged in) |
| 🤖 **GoBot Chatbot** | Ask about modules, careers, and diplomas in plain English |
| 🗺️ **Career Paths** | See which modules match your career goals |
| 🌙 **Dark Mode** | Automatically follows your system theme |
| 📱 **Responsive** | Works on desktop, tablet, and mobile |
| 🔄 **Guest → Account** | Your reviews and bookmarks transfer when you create an account |

---

## 🚀 Quick Start (Docker)

> [!NOTE]
> Docker is the recommended way to run ModuleGo.

### Prerequisites

- [Docker Desktop](https://docs.docker.com/get-docker/)

### Steps

**1. Clone and scrape data**

> [!NOTE]
> Scraping requires Python 3.12+ with dependencies (`pip install -r requirements.txt`).

```bash
git clone https://github.com/xavlkh/ModuleGo.git
cd ModuleGo
cd app/static/local-data && python run_all.py && cd ../..
```

**2. Start the app**

> [!TIP]
> Optional: Create a `.env` file to set your secret key and enable AI features:
> ```bash
> cp .env.example .env
> ```
> - `FLASK_SECRET_KEY` — prevents users from tampering with sessions and cookies. Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
> - `GEMINI_API_KEY` — get from [Google AI Studio](https://aistudio.google.com/apikey) (enables comparisons + chatbot)

```bash
# First time or after code changes (rebuilds image)
docker compose up -d --build

# Subsequent starts (faster, uses cached image)
docker compose up -d
```

**3. Open your browser**

Visit **http://localhost** 🎉

To stop the app:

```bash
docker compose down
```

---

## 🖥️ Running Without Docker

> [!TIP]
> Module data comes from scraped JSON files. Reviews are stored in SQLite.

### Steps

**1. Clone the repo**

```bash
git clone https://github.com/xavlkh/ModuleGo.git
cd ModuleGo
```

**2. Install dependencies**

> [!NOTE]
> Requires Python 3.12+.

<details>
<summary>Linux / macOS</summary>

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

</details>

<details>
<summary>Windows (PowerShell)</summary>

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

</details>

**3. Scrape data**

```bash
cd app/static/local-data
python run_all.py
cd ../..
```

**4. Start the app**

> [!TIP]
> Optional: Create a `.env` file to set your secret key and enable AI features:
> ```bash
> cp .env.example .env
> ```
> - `FLASK_SECRET_KEY` — prevents users from tampering with sessions and cookies. Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
> - `GEMINI_API_KEY` — get from [Google AI Studio](https://aistudio.google.com/apikey) (enables comparisons + chatbot)

```bash
python wsgi.py
```

**5. Open your browser**

Visit **http://127.0.0.1:5000**

📖 See `app/static/local-data/SCRAPING_GUIDE.md` for scraping details.

---

## 🧪 Running Tests

```bash
python -m pytest -q
```

Tests use an in-memory SQLite database — no setup needed.

---

## 📊 Monitoring with Prometheus and Grafana

Docker Compose starts a private monitoring stack together with ModuleGo:

- Flask exports HTTP request counts, errors, and response-time histograms.
- PostgreSQL Exporter publishes database health and connection metrics.
- Prometheus collects the metrics every 15 seconds and retains 15 days locally.
- Grafana provisions the Prometheus data source and ModuleGo dashboard automatically.

Set a local Grafana password in `.env`, then start the stack:

```bash
# Add this line to .env:
GRAFANA_ADMIN_PASSWORD=replace-with-a-strong-password

docker compose up -d --build
```

Open Grafana at `http://127.0.0.1:3000` and Prometheus targets at `http://127.0.0.1:9090/targets`. Both ports bind only to the local machine.

---

## 🚢 Deploying to AWS EC2

ModuleGo can be deployed to AWS EC2 with automated CI/CD.

### How It Works

```
Push to master → GitHub Actions builds Docker → Pushes to GHCR → Ansible deploys to EC2
Push to dev    → Same flow, different server
```

### Setup (One-Time)

1. **Create a GitHub secret:** `EC2_SSH_PRIVATE_KEY` (your SSH private key)
2. **Create GitHub environments:** `production` and `development`
3. **Set `EC2_IP` variable** in each environment with your server's public IP
4. **Enable GHCR:** Settings → Actions → Read and write permissions

### Deploy

```bash
git push origin master    # → Production (port 80)
git push origin dev       # → Development (port 5000)
```

---

## 📁 Project Structure

```
ModuleGo/
├── app/                    Flask app package
│   ├── __init__.py         App factory
│   ├── db.py               Database helpers
│   ├── models.py           User model
│   ├── core.py             Business logic (reviews, bookmarks, Gemini)
│   ├── routes/             API and page routes
│   ├── templates/          HTML pages
│   └── static/             CSS, JS, and scraped data
├── tests/                  Test suite
├── ansible/                Server deployment scripts
├── docker-compose.yml      Docker config
├── Dockerfile              Production image
└── nginx.conf              Reverse proxy config
```

## 🛠️ Tech Stack

| Layer | What we use |
|-------|-------------|
| 🐍 Backend | Flask, Flask-Login, Flask-WTF, Flask-Limiter |
| 🗄️ Database | PostgreSQL 16 (production) / SQLite (dev & tests) |
| 🎨 Frontend | Vanilla JavaScript, Tailwind CSS, Lucide Icons |
| 🤖 AI | Google Gemini (comparisons + chatbot) |
| 🔐 Auth | Flask-Login + bcrypt (accounts) / Signed cookies (guests) |
| 🚀 Deploy | Docker, Nginx, Ansible, GitHub Actions, AWS EC2 |
| 🕷️ Scraping | Playwright, Crawl4AI, BeautifulSoup |

---

<div align="center">
Made with ❤️ for Republic Polytechnic students
</div>
