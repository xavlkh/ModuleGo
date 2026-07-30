"""Supabase authentication routes, session handling, and account management."""

import base64
import binascii
import json
import os
import secrets
import time
from typing import Any

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_wtf import FlaskForm
from supabase import create_client
from wtforms import EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------


def _strip_text(value):
    """Trim surrounding whitespace."""
    return value.strip() if isinstance(value, str) else value


def _normalise_email(value):
    """Trim and lowercase an email address."""
    return value.strip().lower() if isinstance(value, str) else value


class RegistrationForm(FlaskForm):
    """Validate public account registration."""

    display_name = StringField(
        "Display name",
        filters=[_strip_text],
        validators=[
            DataRequired(message="Display name is required."),
            Length(min=2, max=50,
                   message="Display name must be between 2 and 50 characters."),
        ],
    )
    email = EmailField(
        "Email",
        filters=[_normalise_email],
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Enter a valid email address."),
            Length(max=254),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(min=8, max=128,
                   message="Password must be between 8 and 128 characters."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(message="Confirm your password."),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    """Validate email/password login."""

    email = EmailField(
        "Email",
        filters=[_normalise_email],
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Enter a valid email address."),
            Length(max=254),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required."), Length(max=128)],
    )
    submit = SubmitField("Log In")


class ProfileForm(FlaskForm):
    """Validate an account display-name change."""

    display_name = StringField(
        "Display name",
        filters=[_strip_text],
        validators=[
            DataRequired(message="Display name is required."),
            Length(
                min=2,
                max=50,
                message="Display name must be between 2 and 50 characters.",
            ),
        ],
    )
    submit = SubmitField("Update Profile")


class PasswordChangeForm(FlaskForm):
    """Validate a password change."""

    current_password = PasswordField(
        "Current password",
        validators=[DataRequired(message="Current password is required.")],
    )
    new_password = PasswordField(
        "New password",
        validators=[
            DataRequired(message="New password is required."),
            Length(
                min=8,
                max=128,
                message="Password must be between 8 and 128 characters.",
            ),
        ],
    )
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[
            DataRequired(message="Confirm your new password."),
            EqualTo("new_password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Change Password")


class DeleteAccountForm(FlaskForm):
    """Require the current password before account deletion."""

    current_password = PasswordField(
        "Current password",
        validators=[DataRequired(message="Current password is required.")],
    )
    submit = SubmitField("Delete Account")


# ---------------------------------------------------------------------------
# Auth Service
# ---------------------------------------------------------------------------


class AuthServiceError(RuntimeError):
    """Raised when Supabase Auth is unavailable or rejects an operation."""


def _create_auth_client():
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


def _create_admin_auth_client():
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
        return _create_auth_client().auth.sign_up({
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
        return _create_auth_client().auth.sign_in_with_password({
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
        response = _create_auth_client().auth.get_user(access_token)
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
        return _create_auth_client().auth.set_session(
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
        client = _create_auth_client()
        client.auth.set_session(access_token, refresh_token)
        client.auth.sign_out()
    except AuthServiceError:
        raise
    except Exception as exc:
        raise AuthServiceError(str(exc)) from exc


def update_display_name(access_token, refresh_token, display_name):
    """Update the signed-in user's public display-name metadata."""
    try:
        client = _create_auth_client()
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
        client = _create_auth_client()
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
        client = _create_auth_client()
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
        _create_admin_auth_client().auth.admin.delete_user(user_id)
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


# ---------------------------------------------------------------------------
# Blueprint + constants
# ---------------------------------------------------------------------------

auth_bp = Blueprint("auth", __name__)
ACCESS_TOKEN_KEY = "auth_access_token"
REFRESH_TOKEN_KEY = "auth_refresh_token"
USER_KEY = "auth_user"
EXPIRES_AT_KEY = "auth_expires_at"
DELETE_ACCOUNT_TOKEN_KEY = "delete_account_confirmation"
DELETE_ACCOUNT_TOKEN_SECONDS = 120


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _access_token_claims(access_token):
    """Read safe claims from a token that Flask already stored in its signer."""
    try:
        payload = access_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (
        AttributeError,
        IndexError,
        ValueError,
        UnicodeDecodeError,
        binascii.Error,
    ):
        return {}
    return claims if isinstance(claims, dict) else {}


def _store_auth_session(auth_session, user=None):
    """Store the Supabase session and its safe user snapshot."""
    access_token = getattr(auth_session, "access_token", None)
    refresh_token = getattr(auth_session, "refresh_token", None)
    if not access_token or not refresh_token:
        raise AuthServiceError("Supabase did not return a complete session.")
    session.clear()
    session[ACCESS_TOKEN_KEY] = access_token
    session[REFRESH_TOKEN_KEY] = refresh_token
    if user is None:
        user = getattr(auth_session, "user", None)
    claims = _access_token_claims(access_token)
    if user is None and claims:
        user = {
            "id": claims.get("sub"),
            "email": claims.get("email"),
            "user_metadata": claims.get("user_metadata"),
        }
    if user is not None:
        safe_user = user_to_dict(user)
        if safe_user["id"]:
            session[USER_KEY] = safe_user
    expires_at = getattr(auth_session, "expires_at", None)
    if not expires_at:
        expires_at = claims.get("exp")
    if expires_at:
        session[EXPIRES_AT_KEY] = int(expires_at)
    session.permanent = True


def _clear_auth_session():
    """Remove local authentication state."""
    session.pop(ACCESS_TOKEN_KEY, None)
    session.pop(REFRESH_TOKEN_KEY, None)
    session.pop(USER_KEY, None)
    session.pop(EXPIRES_AT_KEY, None)


def _cached_user_is_current():
    """Return whether the signed cached user can be used before refresh."""
    cached_user = session.get(USER_KEY)
    expires_at = session.get(EXPIRES_AT_KEY)
    if not cached_user or not expires_at:
        return False
    return int(expires_at) > int(time.time()) + 60


def _friendly_auth_error(error, action):
    """Return a useful message without exposing provider details."""
    detail = str(error).lower()
    if "invalid login credentials" in detail:
        return "Invalid email or password."
    if "email not confirmed" in detail:
        return "Confirm your email address before logging in."
    if "rate limit" in detail or "too many requests" in detail:
        return "Too many attempts. Please wait before trying again."
    if "not configured" in detail:
        return "Account services are not configured on this server."
    return (
        "We could not create the account. Please try again."
        if action == "register"
        else "We could not log you in. Please try again."
    )


def _friendly_profile_error(error):
    """Return a safe message for account-management failures."""
    detail = str(error).lower()
    if "invalid login credentials" in detail:
        return "Your current password is incorrect."
    if "same password" in detail:
        return "Choose a new password that is different from your current password."
    if "rate limit" in detail or "too many requests" in detail:
        return "Too many attempts. Please wait before trying again."
    if "not configured" in detail:
        return "Account services are not configured on this server."
    return "We could not update your account. Please try again."


def _profile_forms():
    """Create the three independent forms displayed on the profile page."""
    return ProfileForm(), PasswordChangeForm(), DeleteAccountForm()


def _login_required():
    """Redirect anonymous visitors away from account settings."""
    if not g.current_user:
        flash("Log in to manage your profile.", "error")
        return redirect(url_for("auth.login"))
    return None


def _confirmation_redirect_url():
    """Build the allowed local or deployed login confirmation URL."""
    scheme = "https" if current_app.config["SESSION_COOKIE_SECURE"] else "http"
    return url_for("auth.login", confirmed="1", _external=True, _scheme=scheme)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@auth_bp.before_app_request
def load_current_user():
    """Load user from cached session data only — no network calls."""
    g.current_user = None
    cached_user = session.get(USER_KEY)
    if cached_user:
        g.current_user = cached_user


def verify_auth():
    """Verify or refresh the access token. Call from protected endpoints only."""
    if g.current_user:
        return None
    access_token = session.get(ACCESS_TOKEN_KEY)
    refresh_token = session.get(REFRESH_TOKEN_KEY)
    if not access_token:
        flash("Log in to manage your profile.", "error")
        return redirect(url_for("auth.login"))
    if _cached_user_is_current():
        g.current_user = session[USER_KEY]
        return None
    try:
        verified_user = verify_access_token(access_token)
        g.current_user = user_to_dict(verified_user)
        session[USER_KEY] = g.current_user
        return None
    except AuthServiceError:
        if not refresh_token:
            _clear_auth_session()
            flash("Log in to manage your profile.", "error")
            return redirect(url_for("auth.login"))
    try:
        response = refresh_user_session(access_token, refresh_token)
        refreshed_session = getattr(response, "session", None)
        refreshed_user = getattr(response, "user", None)
        if refreshed_session is None or refreshed_user is None:
            raise AuthServiceError("Supabase could not refresh the session.")
        _store_auth_session(refreshed_session, refreshed_user)
        g.current_user = user_to_dict(refreshed_user)
        return None
    except AuthServiceError as error:
        current_app.logger.warning("Supabase session refresh failed: %s", error)
        _clear_auth_session()
        flash("Log in to manage your profile.", "error")
        return redirect(url_for("auth.login"))


@auth_bp.app_context_processor
def inject_current_user():
    """Expose the safe current user to all Jinja templates."""
    return {"current_user": getattr(g, "current_user", None)}


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Create an account and request email confirmation."""
    if g.current_user:
        return redirect(url_for("serve_index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            sign_up_user(
                form.email.data,
                form.password.data,
                form.display_name.data,
                _confirmation_redirect_url(),
            )
        except AuthServiceError as error:
            flash(_friendly_auth_error(error, "register"), "error")
        else:
            flash(
                "Account created. Check your email to confirm it, then log in.",
                "success",
            )
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate an account."""
    if g.current_user:
        return redirect(url_for("serve_index"))
    form = LoginForm()
    if request.method == "GET" and request.args.get("confirmed") == "1":
        flash("Email confirmed. You can now log in.", "success")
    if form.validate_on_submit():
        try:
            response = sign_in_user(form.email.data, form.password.data)
            auth_session = getattr(response, "session", None)
            if auth_session is None:
                raise AuthServiceError("Supabase did not return a session.")
            _store_auth_session(auth_session, getattr(response, "user", None))
        except AuthServiceError as error:
            flash(_friendly_auth_error(error, "login"), "error")
        else:
            flash("Welcome back. You are now logged in.", "success")
            return redirect(url_for("serve_index"))
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Revoke provider state and clear the local session."""
    try:
        sign_out_user(
            session.get(ACCESS_TOKEN_KEY),
            session.get(REFRESH_TOKEN_KEY),
        )
    except AuthServiceError:
        pass
    finally:
        _clear_auth_session()
    flash("You have been logged out.", "success")
    return redirect(url_for("serve_index"))


@auth_bp.route("/profile", methods=["GET"])
def profile():
    """Display account settings for the signed-in user."""
    redirect_response = verify_auth()
    if redirect_response:
        return redirect_response
    profile_form, password_form, delete_form = _profile_forms()
    profile_form.display_name.data = g.current_user["display_name"]

    from app import BookmarkRepository, ReviewRepository

    user_id = g.current_user["id"]
    review_count = ReviewRepository.count_by_user(user_id)
    bookmark_count = len(BookmarkRepository.list_for_user(user_id))

    return render_template(
        "auth/profile.html",
        profile_form=profile_form,
        password_form=password_form,
        delete_form=delete_form,
        review_count=review_count,
        bookmark_count=bookmark_count,
    )


@auth_bp.route("/profile", methods=["POST"])
def update_profile():
    """Update the current account's display name."""
    redirect_response = verify_auth()
    if redirect_response:
        return redirect_response
    profile_form, password_form, delete_form = _profile_forms()
    if profile_form.validate_on_submit():
        display_name = profile_form.display_name.data
        try:
            response = update_display_name(
                session[ACCESS_TOKEN_KEY],
                session[REFRESH_TOKEN_KEY],
                display_name,
            )
            safe_user = user_to_dict(getattr(response, "user", None))
            if not safe_user["id"]:
                safe_user = {
                    **g.current_user,
                    "display_name": display_name,
                }
            session[USER_KEY] = safe_user
            g.current_user = safe_user
        except AuthServiceError as error:
            flash(_friendly_profile_error(error), "error")
        else:
            try:
                current_app.extensions[
                    "review_repository"
                ].update_author_display_name(
                    g.current_user["id"],
                    display_name,
                )
            except Exception:
                current_app.logger.exception(
                    "Could not synchronize review author names for user %s",
                    g.current_user["id"],
                )
                flash(
                    "Your profile was updated, but older review names could "
                    "not be refreshed. Save your profile again to retry.",
                    "error",
                )
            else:
                flash(
                    "Your profile and review names have been updated.",
                    "success",
                )
            return redirect(url_for("auth.profile"))
    return render_template(
        "auth/profile.html",
        profile_form=profile_form,
        password_form=password_form,
        delete_form=delete_form,
    )


@auth_bp.route("/profile/password", methods=["POST"])
def change_password():
    """Verify the current password and save a replacement."""
    redirect_response = verify_auth()
    if redirect_response:
        return redirect_response
    profile_form, password_form, delete_form = _profile_forms()
    profile_form.display_name.data = g.current_user["display_name"]
    if password_form.validate_on_submit():
        try:
            change_user_password(
                g.current_user["email"],
                password_form.current_password.data,
                password_form.new_password.data,
            )
        except AuthServiceError as error:
            flash(_friendly_profile_error(error), "error")
        else:
            flash("Your password has been changed.", "success")
            return redirect(url_for("auth.profile"))
    return render_template(
        "auth/profile.html",
        profile_form=profile_form,
        password_form=password_form,
        delete_form=delete_form,
    )


@auth_bp.route("/profile/delete/verify", methods=["POST"])
def verify_account_deletion():
    """Verify the password and issue a short-lived deletion confirmation."""
    redirect_response = verify_auth()
    if redirect_response:
        return redirect_response
    delete_form = DeleteAccountForm()
    if not delete_form.validate_on_submit():
        message = next(
            (
                error
                for errors in delete_form.errors.values()
                for error in errors
            ),
            "Enter your current password.",
        )
        return jsonify({"verified": False, "message": message}), 400
    try:
        verify_user_password(
            g.current_user["id"],
            g.current_user["email"],
            delete_form.current_password.data,
        )
    except AuthServiceError as error:
        return jsonify({
            "verified": False,
            "message": _friendly_profile_error(error),
        }), 401

    confirmation_token = secrets.token_urlsafe(32)
    session[DELETE_ACCOUNT_TOKEN_KEY] = {
        "token": confirmation_token,
        "expires_at": int(time.time()) + DELETE_ACCOUNT_TOKEN_SECONDS,
    }
    return jsonify({
        "verified": True,
        "confirmation_token": confirmation_token,
    }), 200


@auth_bp.route("/profile/delete", methods=["POST"])
def delete_account():
    """Delete an account only after password verification and confirmation."""
    redirect_response = verify_auth()
    if redirect_response:
        return redirect_response
    provided_token = request.form.get("delete_token", "")
    confirmation = session.pop(DELETE_ACCOUNT_TOKEN_KEY, None) or {}
    expected_token = confirmation.get("token", "")
    expires_at = confirmation.get("expires_at", 0)
    if (
        not provided_token
        or not expected_token
        or not secrets.compare_digest(provided_token, expected_token)
        or expires_at < int(time.time())
    ):
        flash("Deletion confirmation expired. Verify your password again.", "error")
        return redirect(url_for("auth.profile"))
    try:
        delete_user_account(g.current_user["id"])
    except AuthServiceError as error:
        flash(_friendly_profile_error(error), "error")
        return redirect(url_for("auth.profile"))

    _clear_auth_session()
    flash("Your account has been permanently deleted.", "success")
    return redirect(url_for("serve_index"))


@auth_bp.route("/api/auth/me", methods=["GET"])
def current_user():
    """Return only safe verified account information."""
    redirect_response = verify_auth()
    if redirect_response:
        return jsonify({"authenticated": False, "user": None}), 200
    if not g.current_user:
        return jsonify({"authenticated": False, "user": None}), 200
    return jsonify({"authenticated": True, "user": g.current_user}), 200
