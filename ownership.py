"""Server-controlled account and signed guest identity helpers."""

import hashlib
import hmac
import secrets

from flask import current_app, g, request
from flask_login import current_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

GUEST_COOKIE_NAME = "modulego_guest"
GUEST_COOKIE_MAX_AGE = 30 * 24 * 60 * 60


def _serializer():
    """Return the signer dedicated to guest identity cookies."""
    return URLSafeTimedSerializer(
        current_app.secret_key,
        salt="modulego-guest-ownership-v1",
    )


def _hash_guest_id(guest_id):
    """Create the irreversible value stored in the database."""
    return hmac.new(
        current_app.secret_key.encode("utf-8"),
        guest_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def current_guest_hash():
    """Return the valid guest hash from the signed cookie, if present."""
    signed_value = request.cookies.get(GUEST_COOKIE_NAME, "")
    if not signed_value:
        return None
    try:
        guest_id = _serializer().loads(
            signed_value,
            max_age=GUEST_COOKIE_MAX_AGE,
        )
    except (BadSignature, SignatureExpired):
        return None
    return _hash_guest_id(guest_id)


def request_identity(create_guest=False):
    """Return the verified account identity or signed guest identity."""
    if current_user.is_authenticated:
        return {
            "kind": "account",
            "user_id": current_user.id,
            "guest_owner_hash": None,
            "display_name": getattr(current_user, "display_name", "Student")[:50],
        }

    guest_hash = current_guest_hash()
    if not guest_hash and create_guest:
        guest_id = secrets.token_urlsafe(32)
        guest_hash = _hash_guest_id(guest_id)
        g.pending_guest_cookie = _serializer().dumps(guest_id)
    if guest_hash:
        return {
            "kind": "guest",
            "user_id": None,
            "guest_owner_hash": guest_hash,
            "display_name": None,
        }
    return None


def rotate_guest_cookie():
    """Queue a fresh guest identity after a successful ownership claim."""
    guest_id = secrets.token_urlsafe(32)
    g.pending_guest_cookie = _serializer().dumps(guest_id)


def set_pending_guest_cookie(response):
    """Attach a queued secure guest cookie to the outgoing response."""
    signed_value = getattr(g, "pending_guest_cookie", None)
    if signed_value:
        response.set_cookie(
            GUEST_COOKIE_NAME,
            signed_value,
            max_age=GUEST_COOKIE_MAX_AGE,
            httponly=True,
            secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
            samesite="Lax",
            path="/",
        )
    return response


def identity_owns(row, identity):
    """Return whether a database row belongs to the request identity."""
    if not identity:
        return False
    if identity["kind"] == "account":
        if row.get("user_id") and str(row["user_id"]) == identity["user_id"]:
            return True
        # Guest-to-account: logged-in user claiming a guest review via cookie
        guest_hash = current_guest_hash()
        if guest_hash and row.get("guest_owner_hash"):
            return hmac.compare_digest(row["guest_owner_hash"], guest_hash)
        return False
    return bool(
        row.get("guest_owner_hash")
        and hmac.compare_digest(
            row["guest_owner_hash"],
            identity["guest_owner_hash"],
        )
    )
