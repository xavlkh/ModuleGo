"""Flask-WTF forms used by ModuleGo authentication pages."""

from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


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
