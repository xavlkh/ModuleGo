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


def _log_in_test_user(client):
    """Seed a fresh signed account session without contacting Supabase."""
    with client.session_transaction() as session:
        session[auth_routes.ACCESS_TOKEN_KEY] = "access-token"
        session[auth_routes.REFRESH_TOKEN_KEY] = "refresh-token"
        session[auth_routes.EXPIRES_AT_KEY] = int(time.time()) + 3600
        session[auth_routes.USER_KEY] = {
            "id": "11111111-1111-1111-1111-111111111111",
            "email": "student@example.com",
            "display_name": "Jamie",
        }


def test_profile_requires_login(client):
    """Anonymous visitors cannot open account settings."""
    response = client.get("/profile")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_displays_safe_account_details(client):
    """The profile page shows the editable name and read-only email."""
    _log_in_test_user(client)

    response = client.get("/profile")

    assert response.status_code == 200
    assert b"My profile" in response.data
    assert b"Jamie" in response.data
    assert b"student@example.com" in response.data


def test_profile_updates_display_name_and_session(client, monkeypatch):
    """A successful metadata update is reflected in the navigation immediately."""
    _log_in_test_user(client)
    captured = {}

    def fake_update(access_token, refresh_token, display_name):
        captured.update({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "display_name": display_name,
        })
        return SimpleNamespace(user={
            "id": "11111111-1111-1111-1111-111111111111",
            "email": "student@example.com",
            "user_metadata": {"display_name": display_name},
        })

    monkeypatch.setattr(auth_routes, "update_display_name", fake_update)
    monkeypatch.setattr(
        app_module.ReviewRepository,
        "update_author_display_name",
        lambda user_id, display_name: captured.update({
            "synced_user_id": user_id,
            "synced_display_name": display_name,
        }),
    )
    response = client.post(
        "/profile",
        data={"display_name": "Taylor"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert captured["display_name"] == "Taylor"
    assert captured["synced_user_id"] == (
        "11111111-1111-1111-1111-111111111111"
    )
    assert captured["synced_display_name"] == "Taylor"
    assert b"Hi, Taylor" in response.data
    with client.session_transaction() as session:
        assert session[auth_routes.USER_KEY]["display_name"] == "Taylor"


def test_profile_keeps_new_name_when_review_sync_fails(client, monkeypatch):
    """A retryable review-sync failure does not undo the Auth update."""
    _log_in_test_user(client)
    monkeypatch.setattr(
        auth_routes,
        "update_display_name",
        lambda _access, _refresh, display_name: SimpleNamespace(user={
            "id": "11111111-1111-1111-1111-111111111111",
            "email": "student@example.com",
            "user_metadata": {"display_name": display_name},
        }),
    )

    def fail_sync(_user_id, _display_name):
        raise RuntimeError("Database unavailable")

    monkeypatch.setattr(
        app_module.ReviewRepository,
        "update_author_display_name",
        fail_sync,
    )
    response = client.post(
        "/profile",
        data={"display_name": "Taylor"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"older review names could not be refreshed" in response.data
    assert b"Hi, Taylor" in response.data
    with client.session_transaction() as session:
        assert session[auth_routes.USER_KEY]["display_name"] == "Taylor"


def test_password_change_verifies_current_password(client, monkeypatch):
    """Password replacement passes the current password to the provider."""
    _log_in_test_user(client)
    captured = {}

    def fake_change(email, current_password, new_password):
        captured.update({
            "email": email,
            "current_password": current_password,
            "new_password": new_password,
        })

    monkeypatch.setattr(auth_routes, "change_user_password", fake_change)
    response = client.post("/profile/password", data={
        "current_password": "old-password",
        "new_password": "new-password",
        "confirm_password": "new-password",
    })

    assert response.status_code == 302
    assert captured == {
        "email": "student@example.com",
        "current_password": "old-password",
        "new_password": "new-password",
    }


def test_delete_password_verification_returns_clear_error(client, monkeypatch):
    """An incorrect password is rejected before confirmation is displayed."""
    _log_in_test_user(client)
    monkeypatch.setattr(
        auth_routes,
        "verify_user_password",
        lambda *_args: (_ for _ in ()).throw(
            auth_routes.AuthServiceError("Invalid login credentials")
        ),
    )

    response = client.post("/profile/delete/verify", data={
        "current_password": "password1",
    })

    assert response.status_code == 401
    assert response.get_json() == {
        "verified": False,
        "message": "Your current password is incorrect.",
    }


def test_delete_password_verification_issues_short_lived_token(
        client, monkeypatch):
    """A correct password creates the token required by the confirmation step."""
    _log_in_test_user(client)
    monkeypatch.setattr(
        auth_routes,
        "verify_user_password",
        lambda *_args: {"id": "11111111-1111-1111-1111-111111111111"},
    )

    response = client.post("/profile/delete/verify", data={
        "current_password": "password1",
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["verified"] is True
    assert payload["confirmation_token"]
    with client.session_transaction() as session:
        confirmation = session[auth_routes.DELETE_ACCOUNT_TOKEN_KEY]
        assert confirmation["token"] == payload["confirmation_token"]


def test_delete_account_rejects_missing_confirmation_token(
        client, monkeypatch):
    """The final endpoint cannot be called without password verification."""
    _log_in_test_user(client)
    monkeypatch.setattr(
        auth_routes,
        "delete_user_account",
        lambda *_args: pytest.fail("Delete must not be called."),
    )

    response = client.post("/profile/delete", data={"delete_token": ""})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")


def test_delete_account_clears_session(client, monkeypatch):
    """A verified deletion removes local login state."""
    _log_in_test_user(client)
    captured = {}

    def fake_delete(user_id):
        captured["user_id"] = user_id

    monkeypatch.setattr(auth_routes, "delete_user_account", fake_delete)
    with client.session_transaction() as session:
        session[auth_routes.DELETE_ACCOUNT_TOKEN_KEY] = {
            "token": "confirmed-delete-token",
            "expires_at": int(time.time()) + 60,
        }

    response = client.post(
        "/profile/delete",
        data={"delete_token": "confirmed-delete-token"},
    )

    assert response.status_code == 302
    assert captured["user_id"] == "11111111-1111-1111-1111-111111111111"
    with client.session_transaction() as session:
        assert auth_routes.ACCESS_TOKEN_KEY not in session
        assert auth_routes.REFRESH_TOKEN_KEY not in session
