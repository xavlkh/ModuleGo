# ---------- Stage 1: generate local data via scraping pipeline ----------
FROM python:3.12-slim AS scraper

# wget/gnupg needed by Playwright's --with-deps flag to fetch Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg \
    && rm -rf /var/lib/apt/lists/*

# Chromium system deps required at runtime by Playwright's headless browser.
# Without these, the scraping pipeline silently fails with "browser not found".
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    libatspi2.0-0 libwayland-client0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install all deps first to maximise layer caching — source code changes
# won't re-trigger the expensive pip install + playwright download.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium

COPY . .

# Runs step1-step5 locally to populate app/static/local-data/data/.
# This data is gitignored and must exist before the app starts in SQLite mode.
RUN python app/static/local-data/run_all.py


# ---------- Stage 2: lean runtime image ----------
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY requirements-runtime.txt .
RUN pip install --no-cache-dir -r requirements-runtime.txt

COPY app/ app/
COPY app.py .

# Pull the generated JSON/CSV data from the scraper stage — the runtime
# image never needs Playwright, crawl4ai, or the scraping scripts.
COPY --from=scraper /app/app/static/local-data/data/ app/static/local-data/data/

# init_db() runs at import time; the directory must exist before gunicorn
# starts or SQLite will throw "unable to open db" when DATABASE_URL is unset.
RUN mkdir -p /app/data
ENV DATABASE_PATH=/app/data/modulego.db

EXPOSE 5000

# Timeout matches GEMINI_TIMEOUT_SECONDS (25s) plus headroom so Gemini
# requests don't get killed mid-flight by the worker.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "30", "app:app"]
