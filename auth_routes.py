"""Supabase authentication routes and secure Flask session handling."""

import base64
import binascii
import json
import secrets
import time

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

from auth_service import (
    AuthServiceError,
    change_user_password,
    delete_user_account,
    refresh_user_session,
    sign_in_user,
    sign_out_user,
    sign_up_user,
    update_display_name,
    user_to_dict,
    verify_access_token,
    verify_user_password,
)
from forms import (
    DeleteAccountForm,
    LoginForm,
    PasswordChangeForm,
    ProfileForm,
    RegistrationForm,
)

auth_bp = Blueprint("auth", __name__)
ACCESS_TOKEN_KEY = "auth_access_token"
REFRESH_TOKEN_KEY = "auth_refresh_token"
USER_KEY = "auth_user"
EXPIRES_AT_KEY = "auth_expires_at"
DELETE_ACCOUNT_TOKEN_KEY = "delete_account_confirmation"
DELETE_ACCOUNT_TOKEN_SECONDS = 120


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


@auth_bp.before_app_request
def load_current_user():
    """Use the fresh login snapshot, then verify or refresh expired tokens."""
    g.current_user = None
    access_token = session.get(ACCESS_TOKEN_KEY)
    refresh_token = session.get(REFRESH_TOKEN_KEY)
    if not access_token:
        return
    if _cached_user_is_current():
        g.current_user = session[USER_KEY]
        return
    try:
        verified_user = verify_access_token(access_token)
        g.current_user = user_to_dict(verified_user)
        session[USER_KEY] = g.current_user
        return
    except AuthServiceError:
        if not refresh_token:
            _clear_auth_session()
            return
    try:
        response = refresh_user_session(access_token, refresh_token)
        refreshed_session = getattr(response, "session", None)
        refreshed_user = getattr(response, "user", None)
        if refreshed_session is None or refreshed_user is None:
            raise AuthServiceError("Supabase could not refresh the session.")
        _store_auth_session(refreshed_session, refreshed_user)
        g.current_user = user_to_dict(refreshed_user)
    except AuthServiceError as error:
        current_app.logger.warning("Supabase session refresh failed: %s", error)
        _clear_auth_session()


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
    redirect_response = _login_required()
    if redirect_response:
        return redirect_response
    profile_form, password_form, delete_form = _profile_forms()
    profile_form.display_name.data = g.current_user["display_name"]
    return render_template(
        "auth/profile.html",
        profile_form=profile_form,
        password_form=password_form,
        delete_form=delete_form,
    )


@auth_bp.route("/profile", methods=["POST"])
def update_profile():
    """Update the current account's display name."""
    redirect_response = _login_required()
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
    redirect_response = _login_required()
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
    redirect_response = _login_required()
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
    redirect_response = _login_required()
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
    if not g.current_user:
        return jsonify({"authenticated": False, "user": None}), 200
    return jsonify({"authenticated": True, "user": g.current_user}), 200
