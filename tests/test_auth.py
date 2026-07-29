"""Small, provider-free tests for the Supabase authentication routes."""

import base64
import json
import time
from types import SimpleNamespace

import pytest

import app as app_module
import auth_routes


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Return an isolated Flask client."""
    monkeypatch.setattr(
        app_module,
        "db_name",
        str(tmp_path / "auth-test.db"),
    )
    app_module.init_db()
    return app_module.app.test_client()


def test_registration_validates_confirmation(client):
    """Mismatched passwords never call Supabase."""
    response = client.post("/register", data={
        "display_name": "Student",
        "email": "student@example.com",
        "password": "password1",
        "confirm_password": "password2",
    })

    assert response.status_code == 200
    assert b"Passwords must match" in response.data


def test_registration_requests_email_confirmation(client, monkeypatch):
    """Valid registration passes only safe account metadata."""
    captured = {}

    def fake_signup(email, password, display_name, redirect):
        captured.update({
            "email": email,
            "password": password,
            "display_name": display_name,
            "redirect": redirect,
        })
        return SimpleNamespace()

    monkeypatch.setattr(auth_routes, "sign_up_user", fake_signup)
    response = client.post("/register", data={
        "display_name": "Jamie",
        "email": "JAMIE@example.com",
        "password": "password1",
        "confirm_password": "password1",
    })

    assert response.status_code == 302
    assert captured["email"] == "jamie@example.com"
    assert captured["display_name"] == "Jamie"
    assert captured["redirect"].endswith("/login?confirmed=1")


def test_login_stores_provider_tokens(client, monkeypatch):
    """Successful login stores tokens but never returns them to JavaScript."""
    auth_session = SimpleNamespace(
        access_token="access-token",
        refresh_token="refresh-token",
    )
    monkeypatch.setattr(
        auth_routes,
        "sign_in_user",
        lambda _email, _password: SimpleNamespace(session=auth_session),
    )

    response = client.post("/login", data={
        "email": "student@example.com",
        "password": "password1",
    })

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session[auth_routes.ACCESS_TOKEN_KEY] == "access-token"
        assert session[auth_routes.REFRESH_TOKEN_KEY] == "refresh-token"


def test_login_uses_fresh_session_user_on_redirect(client, monkeypatch):
    """A successful login renders the account navigation immediately."""
    auth_session = SimpleNamespace(
        access_token="access-token",
        refresh_token="refresh-token",
        expires_at=int(time.time()) + 3600,
    )
    monkeypatch.setattr(
        auth_routes,
        "sign_in_user",
        lambda _email, _password: SimpleNamespace(
            session=auth_session,
            user={
                "id": "user-1",
                "email": "student@example.com",
                "user_metadata": {"display_name": "Jamie"},
            },
        ),
    )
    monkeypatch.setattr(
        auth_routes,
        "verify_access_token",
        lambda _token: pytest.fail("Fresh session should not re-verify immediately."),
    )

    response = client.post("/login", data={
        "email": "student@example.com",
        "password": "password1",
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Hi, Jamie" in response.data
    assert b"Log out" in response.data


def test_login_reads_user_snapshot_from_access_token(client, monkeypatch):
    """A normal Supabase JWT still works if response.user is unavailable."""
    payload = base64.urlsafe_b64encode(json.dumps({
        "sub": "user-1",
        "email": "student@example.com",
        "user_metadata": {"display_name": "Jamie"},
        "exp": int(time.time()) + 3600,
    }).encode()).decode().rstrip("=")
    auth_session = SimpleNamespace(
        access_token=f"header.{payload}.signature",
        refresh_token="refresh-token",
    )
    monkeypatch.setattr(
        auth_routes,
        "sign_in_user",
        lambda _email, _password: SimpleNamespace(session=auth_session, user=None),
    )
    monkeypatch.setattr(
        auth_routes,
        "verify_access_token",
        lambda _token: pytest.fail("Fresh JWT should not re-verify immediately."),
    )

    response = client.post("/login", data={
        "email": "student@example.com",
        "password": "password1",
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Hi, Jamie" in response.data


def test_auth_me_returns_safe_user(client, monkeypatch):
    """The current-user API exposes no access or refresh token."""
    monkeypatch.setattr(
        auth_routes,
        "verify_access_token",
        lambda _token: {
            "id": "user-1",
            "email": "student@example.com",
            "user_metadata": {"display_name": "Student"},
        },
    )
    with client.session_transaction() as session:
        session[auth_routes.ACCESS_TOKEN_KEY] = "access-token"
        session[auth_routes.REFRESH_TOKEN_KEY] = "refresh-token"

    payload = client.get("/api/auth/me").get_json()

    assert payload["authenticated"] is True
    assert payload["user"]["display_name"] == "Student"
    assert "access_token" not in payload
    assert "refresh_token" not in payload


def test_logout_clears_local_session(client, monkeypatch):
    """Logout clears local tokens even if provider revocation fails."""
    monkeypatch.setattr(
        auth_routes,
        "sign_out_user",
        lambda _access, _refresh: None,
    )
    with client.session_transaction() as session:
        session[auth_routes.ACCESS_TOKEN_KEY] = "access-token"
        session[auth_routes.REFRESH_TOKEN_KEY] = "refresh-token"

    response = client.post("/logout")

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert auth_routes.ACCESS_TOKEN_KEY not in session
        assert auth_routes.REFRESH_TOKEN_KEY not in session
