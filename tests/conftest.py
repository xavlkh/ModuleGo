"""Shared test configuration and fixtures for SQLite/PostgreSQL API tests."""

import pytest

import app as app_module


@pytest.fixture(autouse=True)
def configure_test_app():
    """Disable CSRF by default; dedicated tests enable it explicitly."""
    previous_testing = app_module.app.config.get("TESTING")
    previous_csrf = app_module.app.config.get("WTF_CSRF_ENABLED", True)
    app_module.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    yield
    app_module.app.config.update(
        TESTING=previous_testing,
        WTF_CSRF_ENABLED=previous_csrf,
    )


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Return an isolated Flask test client backed by SQLite or PostgreSQL."""
    from app.db import use_postgres
    if use_postgres():
        from app import _init_pg_db
        with app_module.app.app_context():
            _init_pg_db(app_module.app)
    else:
        monkeypatch.setattr(app_module, "db_name", str(tmp_path / "test.db"))
        app_module.init_db()
    with app_module.app.test_client() as test_client:
        yield test_client


def create_review(client, module_code="C270", rating=5, comment="Good", **extra):
    """Create a review via the API. Accepts arbitrary extra payload fields."""
    payload = {
        "module_code": module_code,
        "rating": rating,
        "comment": comment,
        **extra,
    }
    return client.post("/api/reviews", json=payload)


def create_review_as_new_guest(client, module_code="C270", rating=5, comment="Good"):
    """Create a review from a fresh signed guest identity."""
    client.delete_cookie("modulego_guest")
    return create_review(client, module_code, rating, comment)


def register_and_login(client, email="student@example.com", password="testpass1",
                       display_name="Student"):
    """Register a user and log in. Idempotent — safe to call multiple times."""
    client.post("/register", data={
        "display_name": display_name,
        "email": email,
        "password": password,
        "confirm_password": password,
    })
    client.post("/login", data={
        "email": email,
        "password": password,
    })
