"""Account bookmark API tests."""

import pytest

import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Return an isolated test client backed by SQLite or PostgreSQL."""
    from app.db import use_postgres
    if use_postgres():
        from app import _init_pg_db
        with app_module.app.app_context():
            _init_pg_db(app_module.app)
    else:
        monkeypatch.setattr(app_module, "db_name", str(tmp_path / "bookmarks-test.db"))
        app_module.init_db()
    return app_module.app.test_client()


def register_and_login(client, email, display_name="Student"):
    """Create and authenticate an account through the public routes."""
    password = "testpass1"
    client.post("/register", data={
        "display_name": display_name,
        "email": email,
        "password": password,
        "confirm_password": password,
    })
    response = client.post("/login", data={
        "email": email,
        "password": password,
    })
    assert response.status_code == 302


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/bookmarks"),
        ("put", "/api/bookmarks/C270"),
        ("delete", "/api/bookmarks/C270"),
        ("delete", "/api/bookmarks"),
    ],
)
def test_bookmark_api_requires_login(client, method, path):
    response = getattr(client, method)(path)

    assert response.status_code == 401
    assert response.get_json() == {"error": "Login required."}


def test_add_bookmark_is_normalized_and_idempotent(client):
    register_and_login(client, "first@example.com")

    first = client.put("/api/bookmarks/%20c270%20")
    duplicate = client.put("/api/bookmarks/C270")

    assert first.status_code == 200
    assert first.get_json() == {"module_code": "C270"}
    assert duplicate.status_code == 200
    assert client.get("/api/bookmarks").get_json() == {
        "module_codes": ["C270"],
    }


def test_clear_bookmarks_removes_every_saved_module(client):
    register_and_login(client, "clear@example.com")
    client.put("/api/bookmarks/C270")
    client.put("/api/bookmarks/C110")

    response = client.delete("/api/bookmarks")

    assert response.status_code == 204
    assert client.get("/api/bookmarks").get_json() == {"module_codes": []}


def test_bookmarks_are_isolated_between_accounts(client):
    register_and_login(client, "first@example.com", "First Student")
    client.put("/api/bookmarks/C270")

    second_client = app_module.app.test_client()
    register_and_login(second_client, "second@example.com", "Second Student")
    second_client.put("/api/bookmarks/C110")

    assert client.get("/api/bookmarks").get_json() == {
        "module_codes": ["C270"],
    }
    assert second_client.get("/api/bookmarks").get_json() == {
        "module_codes": ["C110"],
    }
