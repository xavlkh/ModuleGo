"""Tests for the Flask-Login authentication routes."""

import pytest

import app as app_module
from user_model import User


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


def _register_user(client, email="student@example.com", password="password1",
                   display_name="Student"):
    """Register a user through the public API."""
    return client.post("/register", data={
        "display_name": display_name,
        "email": email,
        "password": password,
        "confirm_password": password,
    })


def _login_user(client, email="student@example.com", password="password1"):
    """Log in through the public API."""
    return client.post("/login", data={
        "email": email,
        "password": password,
    })


def test_registration_validates_confirmation(client):
    """Mismatched passwords are rejected without creating a user."""
    response = client.post("/register", data={
        "display_name": "Student",
        "email": "student@example.com",
        "password": "password1",
        "confirm_password": "password2",
    })

    assert response.status_code == 200
    assert b"Passwords must match" in response.data


def test_registration_creates_user(client):
    """Valid registration creates a user and redirects to login."""
    response = _register_user(client, email="jamie@example.com",
                              display_name="Jamie")

    assert response.status_code == 302
    user = User.find_by_email("jamie@example.com")
    assert user is not None
    assert user.display_name == "Jamie"
    assert user.verify_password("password1")


def test_registration_rejects_duplicate_email(client):
    """Cannot register with an existing email."""
    _register_user(client)
    response = _register_user(client)

    assert response.status_code == 200
    assert b"already exists" in response.data


def test_login_stores_session(client):
    """Successful login creates a Flask-Login session."""
    _register_user(client)

    response = _login_user(client)

    assert response.status_code == 302


def test_login_uses_fresh_session_user_on_redirect(client):
    """A successful login renders the account navigation immediately."""
    _register_user(client, display_name="Jamie")

    response = client.post("/login", data={
        "email": "student@example.com",
        "password": "password1",
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Jamie" in response.data
    assert b"Log out" in response.data


def test_login_rejects_wrong_password(client):
    """Wrong password is rejected."""
    _register_user(client)

    response = client.post("/login", data={
        "email": "student@example.com",
        "password": "wrongpassword",
    })

    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


def test_auth_me_returns_safe_user(client):
    """The current-user API exposes no sensitive data."""
    _register_user(client, display_name="Student")

    # Not authenticated
    payload = client.get("/api/auth/me").get_json()
    assert payload["authenticated"] is False

    # Login and check
    _login_user(client)
    payload = client.get("/api/auth/me").get_json()
    assert payload["authenticated"] is True
    assert payload["user"]["display_name"] == "Student"
    assert "password_hash" not in payload["user"]


def test_logout_clears_session(client):
    """Logout clears the Flask-Login session."""
    _register_user(client)
    _login_user(client)

    response = client.post("/logout")

    assert response.status_code == 302
    payload = client.get("/api/auth/me").get_json()
    assert payload["authenticated"] is False


def test_profile_requires_login(client):
    """Anonymous visitors cannot open account settings."""
    response = client.get("/profile")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_displays_safe_account_details(client):
    """The profile page shows the editable name and read-only email."""
    _register_user(client, email="student@example.com", display_name="Jamie")
    _login_user(client)

    response = client.get("/profile")

    assert response.status_code == 200
    assert b"Profile" in response.data
    assert b"Jamie" in response.data
    assert b"student@example.com" in response.data


def test_profile_updates_display_name(client):
    """A successful name update is reflected immediately."""
    _register_user(client, display_name="Jamie")
    _login_user(client)

    response = client.post(
        "/profile",
        data={"display_name": "Taylor"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Taylor" in response.data
    user = User.find_by_email("student@example.com")
    assert user.display_name == "Taylor"


def test_profile_keeps_new_name_when_review_sync_fails(client, monkeypatch):
    """A retryable review-sync failure does not undo the name update."""
    _register_user(client, display_name="Jamie")
    _login_user(client)

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
    user = User.find_by_email("student@example.com")
    assert user.display_name == "Taylor"


def test_password_change_verifies_current_password(client):
    """Password replacement requires correct current password."""
    _register_user(client, password="old-password")
    _login_user(client, password="old-password")

    response = client.post("/profile/password", data={
        "current_password": "wrong-password",
        "new_password": "new-password",
        "confirm_password": "new-password",
    })

    assert response.status_code == 200
    assert b"incorrect" in response.data


def test_password_change_succeeds(client):
    """Password is updated when current password is correct."""
    _register_user(client, password="old-password")
    _login_user(client, password="old-password")

    response = client.post("/profile/password", data={
        "current_password": "old-password",
        "new_password": "new-password-1",
        "confirm_password": "new-password-1",
    })

    assert response.status_code == 302
    user = User.find_by_email("student@example.com")
    assert user.verify_password("new-password-1")
    assert not user.verify_password("old-password")


def test_delete_password_verification_returns_clear_error(client):
    """An incorrect password is rejected before confirmation is displayed."""
    _register_user(client, password="password1")
    _login_user(client)

    response = client.post("/profile/delete/verify", data={
        "current_password": "wrong-password",
    })

    assert response.status_code == 401
    assert response.get_json() == {
        "verified": False,
        "message": "Your current password is incorrect.",
    }


def test_delete_password_verification_issues_short_lived_token(client):
    """A correct password creates the token required by the confirmation step."""
    _register_user(client, password="password1")
    _login_user(client)

    response = client.post("/profile/delete/verify", data={
        "current_password": "password1",
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["verified"] is True
    assert payload["confirmation_token"]


def test_delete_account_rejects_missing_confirmation_token(client):
    """The final endpoint cannot be called without password verification."""
    _register_user(client)
    _login_user(client)

    response = client.post("/profile/delete", data={"delete_token": ""})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")


def test_delete_account_clears_session(client):
    """A verified deletion removes the user and clears login state."""
    _register_user(client, password="password1")
    _login_user(client)

    # Get confirmation token
    verify_response = client.post("/profile/delete/verify", data={
        "current_password": "password1",
    })
    token = verify_response.get_json()["confirmation_token"]

    # Delete
    response = client.post(
        "/profile/delete",
        data={"delete_token": token},
    )

    assert response.status_code == 302
    user = User.find_by_email("student@example.com")
    assert user is None
