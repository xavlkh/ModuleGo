# Lean runtime image — no scraper, no Playwright
FROM python:3.12-slim

WORKDIR /app

COPY requirements-runtime.txt .
RUN pip install --no-cache-dir -r requirements-runtime.txt

COPY app/ app/
COPY *.py .

RUN addgroup --system --gid 10001 modulego \
    && adduser --system --uid 10001 --ingroup modulego \
        --no-create-home modulego \
    && mkdir -p /app/data \
    && chown -R modulego:modulego /app/data
ENV DATABASE_PATH=/app/data/modulego.db \
    PYTHONDONTWRITEBYTECODE=1

USER modulego

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "30", "app:app"]
