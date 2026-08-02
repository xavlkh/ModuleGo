# Grafana Monitoring Implementation Log

Date: 2 August 2026  
Branch: `feature/grafana-monitoring`  
Base: `origin/dev` at `fee6c21`  
Status: Local changes only. Nothing has been committed or pushed.

## 1. What this feature means for ModuleGo

Grafana is ModuleGo's operational dashboard. It does not store student data and
does not replace PostgreSQL. It helps the team answer operational questions:

- Is the Flask application online?
- Is PostgreSQL online?
- How many requests is ModuleGo receiving?
- Are server errors increasing?
- Are students waiting longer for responses?
- How many database connections are active?

The monitoring data flow is:

```text
Flask request metrics -----------\
                                  -> Prometheus -> Grafana dashboard
PostgreSQL Exporter metrics -----/
```

Prometheus collects and stores measurements every 15 seconds. Grafana reads
those measurements from Prometheus and presents them as charts.

## 2. Scope chosen for the first reliable version

This implementation monitors application traffic and database health. It does
not add cAdvisor or Node Exporter yet because they require privileged access to
the EC2 host and are not necessary to prove that ModuleGo runtime monitoring
works.

Included:

- Flask request count, response status, exceptions, and latency
- PostgreSQL availability and connection count
- Prometheus collection with 15-day retention
- Automatically provisioned Grafana data source and dashboard
- Local Docker Compose integration
- AWS EC2 Ansible integration
- Private monitoring ports and password-protected Grafana

## 3. File-by-file change log

### `requirements.txt`

Added `prometheus-flask-exporter==0.23.2`.

Meaning: developers and CI can import the Flask monitoring library. It creates
Prometheus-compatible request counters and response-time histograms.

### `requirements-runtime.txt`

Added the same monitoring dependency.

Meaning: the production Docker image also receives the library. Updating only
`requirements.txt` would make tests pass locally but cause the EC2 container to
fail when importing the monitoring code.

### `app.py`

Added Prometheus exporter initialisation.

- Local `python app.py` runs expose `/metrics` for simple development checks.
- Docker/Gunicorn runs use multiprocess metrics because production has four
  Gunicorn worker processes.
- Metrics are grouped by Flask URL rule instead of raw URL.

Meaning: `/api/reviews/A103` and `/api/reviews/C270` are stored under one route
label such as `/api/reviews/<module_code>`. This prevents unbounded labels and
avoids recording individual module or review identifiers unnecessarily.

### `gunicorn.conf.py`

Added Gunicorn settings and Prometheus worker lifecycle hooks.

- Flask remains on port `5000`.
- Aggregated Prometheus metrics use internal port `8000`.
- Dead worker metric files are removed when Gunicorn replaces a worker.
- The Flask application is loaded once before Gunicorn forks its four workers.

Meaning: Prometheus receives one correct total across all four Flask workers
instead of incomplete or duplicated values. Preloading also prevents all four
workers from trying to initialize the same PostgreSQL tables simultaneously.

### `Dockerfile`

Added the Prometheus multiprocess directory and internal metrics port. The
startup command now clears old metric files before starting Gunicorn.

Meaning: a container restart begins with clean counters. Port `8000` is not
published to the public internet; it is used only between Docker containers.

### `monitoring/prometheus.yml`

Added scrape jobs for:

- `app:8000` — Flask request metrics
- `postgres-exporter:9187` — PostgreSQL health metrics
- `prometheus:9090` — Prometheus's own health metrics

Meaning: Prometheus knows where each source is located on the private Docker
network and collects new measurements every 15 seconds.

### `monitoring/grafana/provisioning/datasources/prometheus.yml`

Provisioned Prometheus as Grafana's default data source.

Meaning: the team does not have to click through Grafana settings after every
deployment. Grafana connects to Prometheus automatically when the container
starts.

### `monitoring/grafana/provisioning/dashboards/dashboards.yml`

Configured Grafana to load dashboard JSON files from the container filesystem.

Meaning: the dashboard is version-controlled and repeatable across laptops,
development EC2, and production EC2.

### `monitoring/grafana/dashboards/modulego-overview.json`

Created the initial **ModuleGo Operations Overview** dashboard with:

- Flask application UP/DOWN status
- PostgreSQL UP/DOWN status
- HTTP request rate by method
- HTTP 5xx server-error rate
- 95th-percentile response time
- PostgreSQL connection count
- Traffic grouped by Flask route

Meaning: the dashboard shows both availability and performance. An online site
can still be unhealthy if errors or latency are rising.

### `docker-compose.yml`

Added three services:

- `postgres-exporter`
- `prometheus`
- `grafana`

Added persistent volumes for Prometheus history and Grafana settings.

Meaning: `docker compose up -d --build` now starts ModuleGo and its monitoring
stack together. Grafana and Prometheus bind to `127.0.0.1`, so other computers
cannot access them through the host network.

Local URLs:

```text
ModuleGo:  http://127.0.0.1
Grafana:   http://127.0.0.1:3000
Prometheus http://127.0.0.1:9090/targets
```

If port `9090` or `3000` is already used by another program, choose alternatives
in `.env`, for example `PROMETHEUS_PORT=19090` and `GRAFANA_PORT=13000`.

### `.env.example`

Documented:

- `PROMETHEUS_PORT`
- `GRAFANA_PORT`
- `GRAFANA_ADMIN_USER`
- `GRAFANA_ADMIN_PASSWORD`

Meaning: monitoring configuration is visible to teammates without committing
the real password. The real `.env` remains ignored by Git.

### `ansible/templates/docker-compose.ec2.yml.j2`

Added the same monitoring services to the EC2 deployment template.

Meaning: monitoring is part of the repeatable deployment, not something
manually installed on one server.

Grafana binds to EC2's `127.0.0.1:3000`; Prometheus and PostgreSQL Exporter do
not publish host ports.

### `ansible/templates/env.j2`

Added Grafana settings and reads the administrator password from the Ansible
controller environment.

Meaning: the password comes from GitHub Secrets during CD and is written only
to the protected EC2 `.env` file.

### `ansible/group_vars/all.yml`

Added non-secret Grafana defaults: port `3000` and username `admin`.

Meaning: shared settings are defined once for both development and production.

### `ansible/playbook.yml`

Added two deployment tasks:

1. Reject deployment when `GRAFANA_ADMIN_PASSWORD` is missing or shorter than
   12 characters.
2. Copy the version-controlled monitoring configuration to EC2.

Meaning: deployment fails safely instead of silently starting Grafana with an
unsafe default password or missing dashboard files.

### `.github/workflows/cd.yml`

Made the `GRAFANA_ADMIN_PASSWORD` GitHub environment secret available only to
the Ansible deployment step.

Meaning: the secret is not placed in source code, Docker images, or the build
job.

### `tests/test_monitoring.py`

Added tests that verify:

- The local Flask `/metrics` endpoint is available.
- Request counters and latency histograms exist.
- Dynamic values such as `A103` do not become Prometheus route labels.

Meaning: CI can detect accidental removal or unsafe label grouping.

### `README.md`

Added monitoring setup, local URLs, EC2 SSH-tunnel instructions, project
structure, and technology-stack documentation.

Meaning: another teammate can operate the monitoring feature without relying
only on verbal instructions.

## 4. Security decisions

### Grafana is not public on EC2

The EC2 Compose template uses:

```text
127.0.0.1:3000:3000
```

Access it from a trusted computer with:

```bash
ssh -i your-key.pem -L 3000:localhost:3000 ubuntu@YOUR_EC2_IP
```

Then open `http://127.0.0.1:3000` locally.

### Prometheus and exporters are private

The EC2 deployment does not publish ports `8000`, `9090`, or `9187` to AWS.
Only containers on the same Docker network can use them.

### No student information is used as a metric label

Metrics use HTTP method, route rule, and response status. They do not include
emails, comments, passwords, guest tokens, or review ownership identifiers.

## 5. Required manual GitHub setup before deployment

In the GitHub repository:

1. Open **Settings**.
2. Open **Environments**.
3. Select `development`.
4. Add an environment secret named `GRAFANA_ADMIN_PASSWORD`.
5. Repeat for `production` with a different strong password.

Generate a password locally:

```bash
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

Do not put the generated value in this document or Git.

## 6. Local verification commands

```bash
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs prometheus grafana postgres-exporter
python -m pytest -q
```

Prometheus target verification:

```text
http://127.0.0.1:9090/targets
```

Expected targets:

```text
modulego-flask      UP
modulego-postgres   UP
prometheus          UP
```

Verification completed on 2 August 2026:

- All `91` pytest tests passed.
- Ruff passed for the changed Python files.
- Python compilation and Grafana dashboard JSON validation passed.
- Docker Compose configuration validation passed.
- The complete Docker stack started successfully.
- Prometheus reported `modulego-flask`, `modulego-postgres`, and `prometheus`
  as `UP`.
- Grafana reported a healthy database, automatically loaded the Prometheus
  data source, and loaded **ModuleGo Operations Overview** in the ModuleGo
  folder.
- Live Flask traffic appeared in the aggregated Gunicorn metrics.

This laptop already used port `9090`, so the live verification used test-only
host ports `19090` for Prometheus and `13000` for Grafana. The container ports
and committed defaults remain unchanged.

Generate visible traffic for the dashboard:

```powershell
1..30 | ForEach-Object { Invoke-WebRequest http://127.0.0.1/api/modules | Out-Null }
```

Open Grafana at `http://127.0.0.1:3000`, log in, and choose:

```text
Dashboards -> ModuleGo -> ModuleGo Operations Overview
```

## 7. How to explain this contribution

> I integrated Prometheus and Grafana into ModuleGo's Docker and Ansible EC2
> deployment. Flask exports request and latency metrics, PostgreSQL Exporter
> reports database health, Prometheus stores the measurements, and Grafana
> presents them through a repeatable dashboard. Monitoring services are kept
> private, and the Grafana password is supplied through GitHub Secrets.

## 8. Possible future improvements

These are deliberately outside the first version:

- cAdvisor for per-container CPU and memory
- Node Exporter for EC2 CPU, memory, and disk
- Alertmanager or Grafana alert notifications
- TLS and a private Grafana subdomain
- Longer Prometheus retention or remote metrics storage

The first version should be reviewed and demonstrated before adding them.
