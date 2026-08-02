"""Monitoring endpoint checks for the local single-process Flask app."""

import pytest

import app as app_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_database = tmp_path / "modulego-monitoring-test.db"
    monkeypatch.setattr(app_module, "db_name", str(test_database))
    app_module.init_db()

    with app_module.app.test_client() as test_client:
        yield test_client


def test_metrics_endpoint_exposes_flask_request_metrics(client):
    client.get("/")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.mimetype == "text/plain"
    assert b"flask_http_request_total" in response.data
    assert b"flask_http_request_duration_seconds" in response.data


def test_metrics_group_dynamic_urls_by_route_rule(client):
    client.get("/api/reviews/A103")

    response = client.get("/metrics")

    assert b'/api/reviews/A103' not in response.data
    assert b'/api/reviews/<module_code>' in response.data
