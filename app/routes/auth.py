"""Authentication blueprint: registration, login, profile, account deletion."""

import secrets
import time

from flask import (
    Blueprint,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

from app.models import User

auth_bp = Blueprint("auth", __name__)
DELETE_ACCOUNT_TOKEN_KEY = "delete_account_confirmation"
DELETE_ACCOUNT_TOKEN_SECONDS = 120
_ENDPOINT_LOGIN = "auth.login"
_ENDPOINT_PROFILE = "auth.profile"
_TEMPLATE_PROFILE = "auth/profile.html"


def _strip_text(value):
    return value.strip() if isinstance(value, str) else value


def _normalise_email(value):
    return value.strip().lower() if isinstance(value, str) else value


class RegistrationForm(FlaskForm):
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
    current_password = PasswordField(
        "Current password",
        validators=[DataRequired(message="Current password is required.")],
    )
    submit = SubmitField("Delete Account")


def _profile_forms():
    return ProfileForm(), PasswordChangeForm(), DeleteAccountForm()


def _login_required():
    if not current_user.is_authenticated:
        flash("Log in to manage your profile.", "error")
        return redirect(url_for(_ENDPOINT_LOGIN))
    return None


@auth_bp.before_app_request
def load_current_user():
    g.current_user = current_user if current_user.is_authenticated else None


@auth_bp.app_context_processor
def inject_globals():
    user = current_user if current_user.is_authenticated else None
    return {"current_user": user}


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("serve_index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        existing = User.find_by_email(form.email.data)
        if existing:
            flash("An account with that email already exists.", "error")
        else:
            try:
                User.create(
                    form.email.data,
                    form.password.data,
                    form.display_name.data,
                )
            except (ValueError, RuntimeError):
                flash("We could not create the account. Please try again.", "error")
            else:
                flash("Account created. You can now log in.", "success")
                return redirect(url_for(_ENDPOINT_LOGIN))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("serve_index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.find_by_email(form.email.data)
        if user and user.verify_password(form.password.data):
            login_user(user, remember=True)
            flash(f"Welcome back, {user.display_name}. You are now logged in.", "success")
            return redirect(url_for("serve_index"))
        flash("Invalid email or password.", "error")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("serve_index"))


@auth_bp.route("/profile", methods=["GET"])
def profile():
    redirect_response = _login_required()
    if redirect_response:
        return redirect_response
    profile_form, password_form, delete_form = _profile_forms()
    profile_form.display_name.data = current_user.display_name

    from app.core import BookmarkRepository, ReviewRepository
    user_id = current_user.id
    review_count = ReviewRepository.count_by_user(user_id)
    bookmark_count = len(BookmarkRepository.list_for_user(user_id))

    return render_template(
        _TEMPLATE_PROFILE,
        profile_form=profile_form,
        password_form=password_form,
        delete_form=delete_form,
        review_count=review_count,
        bookmark_count=bookmark_count,
    )


@auth_bp.route("/profile", methods=["POST"])
def update_profile():
    redirect_response = _login_required()
    if redirect_response:
        return redirect_response
    profile_form, password_form, delete_form = _profile_forms()
    if profile_form.validate_on_submit():
        display_name = profile_form.display_name.data
        try:
            current_user.update_display_name(display_name)
        except (ValueError, RuntimeError):
            flash("We could not update your account. Please try again.", "error")
        else:
            try:
                from app.core import ReviewRepository
                ReviewRepository.update_author_display_name(
                    current_user.id,
                    display_name,
                )
            except (ValueError, RuntimeError):
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
            return redirect(url_for(_ENDPOINT_PROFILE))
    return render_template(
        _TEMPLATE_PROFILE,
        profile_form=profile_form,
        password_form=password_form,
        delete_form=delete_form,
    )


@auth_bp.route("/profile/password", methods=["POST"])
def change_password():
    redirect_response = _login_required()
    if redirect_response:
        return redirect_response
    profile_form, password_form, delete_form = _profile_forms()
    profile_form.display_name.data = current_user.display_name
    if password_form.validate_on_submit():
        if not current_user.verify_password(password_form.current_password.data):
            flash("Your current password is incorrect.", "error")
        elif password_form.current_password.data == password_form.new_password.data:
            flash("Choose a new password that is different from your current password.", "error")
        else:
            try:
                current_user.change_password(password_form.new_password.data)
            except (ValueError, RuntimeError):
                flash("We could not update your account. Please try again.", "error")
            else:
                flash("Your password has been changed.", "success")
                return redirect(url_for(_ENDPOINT_PROFILE))
    return render_template(
        _TEMPLATE_PROFILE,
        profile_form=profile_form,
        password_form=password_form,
        delete_form=delete_form,
    )


@auth_bp.route("/profile/delete/verify", methods=["POST"])
def verify_account_deletion():
    if not current_user.is_authenticated:
        return jsonify({"verified": False, "message": "Log in first."}), 401
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

    if not current_user.verify_password(delete_form.current_password.data):
        return jsonify({
            "verified": False,
            "message": "Your current password is incorrect.",
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
    if not current_user.is_authenticated:
        flash("Log in to manage your profile.", "error")
        return redirect(url_for(_ENDPOINT_LOGIN))
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
        return redirect(url_for(_ENDPOINT_PROFILE))
    try:
        current_user.delete()
    except (ValueError, RuntimeError):
        flash("We could not delete your account. Please try again.", "error")
        return redirect(url_for(_ENDPOINT_PROFILE))

    logout_user()
    flash("Your account has been permanently deleted.", "success")
    return redirect(url_for("serve_index"))


@auth_bp.route("/api/auth/me", methods=["GET"])
def current_user_api():
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False, "user": None}), 200
    return jsonify({
        "authenticated": True,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "display_name": current_user.display_name,
        },
    }), 200
