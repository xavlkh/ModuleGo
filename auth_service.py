"""Request-scoped Supabase Auth helpers for ModuleGo."""

import os
from typing import Any

from supabase import create_client


class AuthServiceError(RuntimeError):
    """Raised when Supabase Auth is unavailable or rejects an operation."""


def create_auth_client():
    """Create a fresh publishable-key Supabase client for one auth operation."""
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    publishable_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not supabase_url or not publishable_key:
        raise AuthServiceError(
            "Supabase authentication is not configured on this server."
        )
    if not supabase_url.startswith(("https://", "http://")):
        raise AuthServiceError("SUPABASE_URL must be a complete HTTP(S) URL.")
    if publishable_key.startswith(("sb_secret_", "eyJ")):
        raise AuthServiceError(
            "SUPABASE_PUBLISHABLE_KEY must be a publishable key."
        )
    try:
        return create_client(supabase_url, publishable_key)
    except Exception as exc:
        raise AuthServiceError("Could not connect to Supabase Auth.") from exc


def create_admin_auth_client():
    """Create a backend-only client for account deletion."""
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    secret_key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    if not supabase_url or not secret_key:
        raise AuthServiceError(
            "Supabase administrator access is not configured on this server."
        )
    if secret_key.startswith("sb_publishable_"):
        raise AuthServiceError(
            "SUPABASE_SECRET_KEY must be a backend-only secret key."
        )
    try:
        return create_client(supabase_url, secret_key)
    except Exception as exc:
        raise AuthServiceError("Could not connect to Supabase Auth.") from exc


def sign_up_user(email, password, display_name, email_redirect_to=None):
    """Create an account and ask Supabase to send its confirmation email."""
    options: dict[str, Any] = {"data": {"display_name": display_name}}
    if email_redirect_to:
        options["email_redirect_to"] = email_redirect_to
    try:
        return create_auth_client().auth.sign_up({
            "email": email,
            "password": password,
            "options": options,
        })
    except AuthServiceError:
        raise
    except Exception as exc:
        raise AuthServiceError(str(exc)) from exc


def sign_in_user(email, password):
    """Authenticate an email/password account."""
    try:
        return create_auth_client().auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
    except AuthServiceError:
        raise
    except Exception as exc:
        raise AuthServiceError(str(exc)) from exc


def verify_access_token(access_token):
    """Validate an access token and return its Supabase user."""
    try:
        response = create_auth_client().auth.get_user(access_token)
    except AuthServiceError:
        raise
    except Exception as exc:
        raise AuthServiceError(str(exc)) from exc
    user = getattr(response, "user", None)
    if user is None:
        raise AuthServiceError("The authentication session is invalid.")
    return user


def refresh_user_session(access_token, refresh_token):
    """Refresh an expired Supabase session."""
    try:
        return create_auth_client().auth.set_session(
            access_token,
            refresh_token,
        )
    except AuthServiceError:
        raise
    except Exception as exc:
        raise AuthServiceError(str(exc)) from exc


def sign_out_user(access_token, refresh_token):
    """Revoke the Supabase session when tokens are available."""
    if not access_token or not refresh_token:
        return
    try:
        client = create_auth_client()
        client.auth.set_session(access_token, refresh_token)
        client.auth.sign_out()
    except AuthServiceError:
        raise
    except Exception as exc:
        raise AuthServiceError(str(exc)) from exc


def update_display_name(access_token, refresh_token, display_name):
    """Update the signed-in user's public display-name metadata."""
    try:
        client = create_auth_client()
        client.auth.set_session(access_token, refresh_token)
        return client.auth.update_user({
            "data": {"display_name": display_name},
        })
    except AuthServiceError:
        raise
    except Exception as exc:
        raise AuthServiceError(str(exc)) from exc


def change_user_password(email, current_password, new_password):
    """Verify the current password before replacing it."""
    try:
        client = create_auth_client()
        client.auth.sign_in_with_password({
            "email": email,
            "password": current_password,
        })
        client.auth.update_user({"password": new_password})
    except AuthServiceError:
        raise
    except Exception as exc:
        raise AuthServiceError(str(exc)) from exc


def verify_user_password(user_id, email, current_password):
    """Confirm that a password belongs to the current signed-in account."""
    try:
        client = create_auth_client()
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": current_password,
        })
        verified_user = user_to_dict(getattr(response, "user", None))
        if verified_user["id"] != user_id:
            raise AuthServiceError("The authenticated account does not match.")
        return verified_user
    except AuthServiceError:
        raise
    except Exception as exc:
        raise AuthServiceError(str(exc)) from exc


def delete_user_account(user_id):
    """Permanently delete an account after route-level password verification."""
    try:
        create_admin_auth_client().auth.admin.delete_user(user_id)
    except AuthServiceError:
        raise
    except Exception as exc:
        raise AuthServiceError(str(exc)) from exc


def user_to_dict(user):
    """Return only safe user fields used by templates and APIs."""
    if isinstance(user, dict):
        user_id = user.get("id")
        email = user.get("email")
        metadata = user.get("user_metadata") or {}
    else:
        user_id = getattr(user, "id", None)
        email = getattr(user, "email", None)
        metadata = getattr(user, "user_metadata", None) or {}
    safe_email = str(email or "")
    display_name = str(metadata.get("display_name") or "").strip()
    if not display_name:
        display_name = safe_email.split("@", maxsplit=1)[0] or "Student"
    return {
        "id": str(user_id or ""),
        "email": safe_email,
        "display_name": display_name[:50],
    }
