"""Flask-Login User model with bcrypt password hashing.

Stores users in SQLite (tests) or PostgreSQL (production) depending on
the active database backend.
"""

import uuid
from datetime import datetime, timezone

import bcrypt
import psycopg2
import psycopg2.extras
from flask_login import UserMixin


class User(UserMixin):
    """User model for Flask-Login authentication."""

    def __init__(self, id, email, display_name, password_hash, created_at=None):
        self.id = str(id)
        self.email = email
        self.display_name = display_name
        self.password_hash = password_hash
        self.created_at = created_at

    def verify_password(self, password):
        """Check a plaintext password against the stored bcrypt hash."""
        return bcrypt.checkpw(
            password.encode("utf-8"),
            self.password_hash.encode("utf-8"),
        )

    def to_dict(self):
        """Return safe user fields for templates and APIs."""
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
        }

    @staticmethod
    def _get_backend():
        """Return 'sqlite', 'postgres', or None."""
        try:
            import flask
            if flask.current_app.config.get("TESTING"):
                return "sqlite"
        except RuntimeError:
            pass
        import os
        if os.environ.get("DATABASE_URL"):
            return "postgres"
        return "sqlite"

    @classmethod
    def _pg_conn(cls):
        import os
        return psycopg2.connect(os.environ["DATABASE_URL"])

    @classmethod
    def create(cls, email, password, display_name):
        """Create a new user. Returns the User instance."""
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        email = email.strip().lower()
        display_name = display_name.strip()[:50]

        if cls._get_backend() == "postgres":
            conn = cls._pg_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO users (id, email, display_name, password_hash, created_at)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (user_id, email, display_name, password_hash, now),
                    )
                conn.commit()
            finally:
                conn.close()
        else:
            import app as app_module
            conn = app_module.get_db()
            try:
                conn.execute(
                    """INSERT INTO users (id, email, display_name, password_hash, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, email, display_name, password_hash, now),
                )
                conn.commit()
            finally:
                conn.close()

        return cls(user_id, email, display_name, password_hash, now)

    @staticmethod
    def _row_val(row, dict_key, sqlite_key):
        """Read a value from a dict (PostgreSQL) or sqlite3.Row (SQLite)."""
        if isinstance(row, dict):
            return row.get(dict_key)
        try:
            return row[sqlite_key]
        except (KeyError, IndexError):
            return None

    @classmethod
    def _from_row(cls, row):
        """Build a User from a database row (dict or sqlite3.Row)."""
        if row is None:
            return None
        return cls(
            id=row["id"] if isinstance(row, dict) else row["ID"],
            email=row["email"] if isinstance(row, dict) else row["EMAIL"],
            display_name=row["display_name"] if isinstance(row, dict) else row["DISPLAY_NAME"],
            password_hash=row["password_hash"] if isinstance(row, dict) else row["PASSWORD_HASH"],
            created_at=cls._row_val(row, "created_at", "CREATED_AT"),
        )

    @classmethod
    def find_by_email(cls, email):
        """Look up a user by email (case-insensitive). Returns User or None."""
        email = email.strip().lower()
        if cls._get_backend() == "postgres":
            conn = cls._pg_conn()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                    row = cur.fetchone()
            finally:
                conn.close()
        else:
            import app as app_module
            conn = app_module.get_db()
            try:
                row = conn.execute(
                    "SELECT * FROM users WHERE email = ?", (email,)
                ).fetchone()
            finally:
                conn.close()

        return cls._from_row(row)

    @classmethod
    def find_by_id(cls, user_id):
        """Look up a user by ID. Returns User or None."""
        user_id = str(user_id)
        if cls._get_backend() == "postgres":
            conn = cls._pg_conn()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                    row = cur.fetchone()
            finally:
                conn.close()
        else:
            import app as app_module
            conn = app_module.get_db()
            try:
                row = conn.execute(
                    "SELECT * FROM users WHERE id = ?", (user_id,)
                ).fetchone()
            finally:
                conn.close()

        return cls._from_row(row)

    def update_display_name(self, display_name):
        """Update the display name and return self."""
        display_name = display_name.strip()[:50]
        self.display_name = display_name
        if self._get_backend() == "postgres":
            conn = self._pg_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET display_name = %s WHERE id = %s",
                        (display_name, self.id),
                    )
                conn.commit()
            finally:
                conn.close()
        else:
            import app as app_module
            conn = app_module.get_db()
            try:
                conn.execute(
                    "UPDATE users SET display_name = ? WHERE id = ?",
                    (display_name, self.id),
                )
                conn.commit()
            finally:
                conn.close()
        return self

    def change_password(self, new_password):
        """Hash and store a new password."""
        self.password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        if self._get_backend() == "postgres":
            conn = self._pg_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET password_hash = %s WHERE id = %s",
                        (self.password_hash, self.id),
                    )
                conn.commit()
            finally:
                conn.close()
        else:
            import app as app_module
            conn = app_module.get_db()
            try:
                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (self.password_hash, self.id),
                )
                conn.commit()
            finally:
                conn.close()
        return self

    def delete(self):
        """Permanently delete this user. Cascade deletes reviews/votes/bookmarks."""
        if self._get_backend() == "postgres":
            conn = self._pg_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM review_votes WHERE user_id = %s", (self.id,))
                    cur.execute("DELETE FROM reviews WHERE user_id = %s", (self.id,))
                    cur.execute("DELETE FROM bookmarks WHERE user_id = %s", (self.id,))
                    cur.execute("DELETE FROM users WHERE id = %s", (self.id,))
                conn.commit()
            finally:
                conn.close()
        else:
            import app as app_module
            conn = app_module.get_db()
            try:
                conn.execute("DELETE FROM REVIEW_VOTES WHERE USER_ID = ?", (self.id,))
                conn.execute("DELETE FROM REVIEWS WHERE USER_ID = ?", (self.id,))
                conn.execute("DELETE FROM BOOKMARKS WHERE USER_ID = ?", (self.id,))
                conn.execute("DELETE FROM USERS WHERE ID = ?", (self.id,))
                conn.commit()
            finally:
                conn.close()
