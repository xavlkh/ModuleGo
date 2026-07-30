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
SUPABASE_PUBLISHABLE_KEY=your-publishable-key
FLASK_SECRET_KEY=your-stable-random-secret
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

### Account ownership setup

Account support uses Supabase Auth while Flask remains the only database
client. Before testing the `account` branch:

1. Export the existing `reviews` and `review_votes` tables.
2. Run `docs/sql/account_ownership.sql` in Supabase SQL Editor.
3. Enable the Email provider, new-user signups and Confirm Email.
4. Add `http://127.0.0.1:5000/login?confirmed=1` and the exact Vercel
   login URL to Supabase Auth redirect URLs.
5. Add `SUPABASE_PUBLISHABLE_KEY` and a stable `FLASK_SECRET_KEY` locally
   and in Vercel, then redeploy.

Guests use a signed HTTP-only ownership cookie for 30 days. Guest bookmarks
remain in `moduleGoBookmarks` localStorage. Logged-in reviews, votes and
bookmarks belong to the verified Supabase user and can be explicitly claimed
from the current browser after login.

## Deploying to AWS EC2

ModuleGo can be deployed to AWS EC2 using Ansible for infrastructure provisioning and GitHub Actions for CI/CD.

### Architecture

- **GitHub Actions** builds Docker images on push to `main` or `dev` branches
- **GHCR** (GitHub Container Registry) stores the pre-built images
- **Ansible** provisions EC2 instances and pulls images from GHCR
- Two environments: **production** (`main` branch) and **development** (`dev` branch)

### Prerequisites

- AWS account with IAM user that has EC2 permissions
- Python 3.12+ with `boto3` installed (`pip install boto3`)
- Ansible installed (`pip install ansible`)
- SSH key pair for EC2 access

### First-time setup

1. **Provision EC2 instances:**

```bash
cd ansible

# Provision production instance
ansible-playbook -i inventory/prod.ini playbook.yml --tags setup

# Provision development instance
ansible-playbook -i inventory/dev.ini playbook.yml --tags setup
```

2. **Update inventory files** with the EC2 public IPs from the setup output:

```ini
# inventory/prod.ini
[ec2]
modulego-prod ansible_host=YOUR_PROD_EC2_IP

# inventory/dev.ini
[ec2]
modulego-dev ansible_host=YOUR_DEV_EC2_IP
```

3. **Create GitHub repository secrets:**

| Secret | Description |
|--------|-------------|
| `EC2_SSH_PRIVATE_KEY` | Private key content for SSH access to EC2 |

4. **Create GitHub environments:**

- Go to Settings → Environments → New environment
- Create `production` and `development` environments
- Add environment variables: `EC2_IP` with the respective EC2 public IPs

5. **Enable GHCR:**

- Go to Settings → Actions → General → Workflow permissions
- Select **Read and write permissions**

### Deployment flow

Once configured, deployments happen automatically:

```bash
# Push to main → deploys to production (port 5000)
git push origin main

# Push to dev → deploys to development (port 5001)
git push origin dev
```

### Manual deployment

```bash
cd ansible

# Deploy to production
ansible-playbook -i inventory/prod.ini playbook.yml --tags deploy

# Deploy to development
ansible-playbook -i inventory/dev.ini playbook.yml --tags deploy
```

### Updating environment variables

Edit the files in `ansible/group_vars/`:

- `all.yml` — shared settings (AWS region, instance type)
- `prod/all.yml` — production-specific (ports, image tags)
- `dev/all.yml` — development-specific

For secrets, create `ansible/secrets.yml` (gitignored):

```yaml
supabase_url: ""
supabase_secret_key: ""
gemini_api_key: ""
```

## Without Docker

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
