# Lean runtime image — no scraper, no Playwright
FROM python:3.12-slim

WORKDIR /srv

COPY requirements-runtime.txt .
RUN pip install --no-cache-dir -r requirements-runtime.txt

COPY app/ ./app/
COPY *.py ./
COPY gunicorn.conf.py ./

# Create data directory for scraped JSON files
RUN mkdir -p ./app/static/local-data/data

RUN addgroup --system --gid 10001 modulego \
    && adduser --system --uid 10001 --ingroup modulego \
        --no-create-home modulego \
    && mkdir -p /srv/data \
    && chown -R modulego:modulego /srv/data
ENV DATABASE_PATH=/srv/data/modulego.db \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus \
    PYTHONDONTWRITEBYTECODE=1

USER modulego

EXPOSE 5000 8000

CMD ["sh", "-c", "rm -rf /tmp/prometheus && mkdir -p /tmp/prometheus && exec gunicorn -c gunicorn.conf.py wsgi:app"]
