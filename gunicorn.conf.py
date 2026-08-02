"""Gunicorn settings and Prometheus multiprocess lifecycle hooks."""

from prometheus_flask_exporter.multiprocess import (
    GunicornPrometheusMetrics,
)

bind = "0.0.0.0:5000"
workers = 4
timeout = 30
preload_app = True


def when_ready(server):
    """Expose aggregated worker metrics only inside the Docker network."""
    GunicornPrometheusMetrics.start_http_server_when_ready(8000)


def child_exit(server, worker):
    """Remove stale metric files when Gunicorn replaces a worker."""
    GunicornPrometheusMetrics.mark_process_dead_on_child_exit(worker.pid)
