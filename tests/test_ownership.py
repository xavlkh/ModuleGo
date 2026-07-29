"""Hybrid guest/account ownership and CSRF tests."""

import re

import pytest

import app as app_module
import auth_routes


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Return an isolated SQLite test client."""
    test_database = tmp_path / "ownership-test.db"
    monkeypatch.setattr(app_module, "db_name", str(test_database))
    app_module.init_db()
    return app_module.app.test_client()


def create_review(client, module_code="C270", rating=5, **extra):
    """Create a review through the public API."""
    payload = {
        "module_code": module_code,
        "rating": rating,
        "comment": extra.pop("comment", "Helpful"),
        **extra,
    }
    return client.post("/api/reviews", json=payload)


def login_as(client, monkeypatch, user_id="user-1", name="A Student"):
    """Install a verified test account in the Flask session."""
    monkeypatch.setattr(
        auth_routes,
        "verify_access_token",
        lambda _token: {
            "id": user_id,
            "email": f"{user_id}@example.test",
            "user_metadata": {"display_name": name},
        },
    )
    with client.session_transaction() as session:
        session[auth_routes.ACCESS_TOKEN_KEY] = f"access-{user_id}"
        session[auth_routes.REFRESH_TOKEN_KEY] = f"refresh-{user_id}"


def test_public_reviews_hide_private_ownership_fields(client):
    created = create_review(client).get_json()

    assert created["is_owner"] is True
    assert created["author"] == {
        "anonymous": True,
        "label": "Anonymous student",
    }
    assert "user_id" not in created
    assert "guest_owner_hash" not in created
    assert "owner_token" not in created


def test_other_guest_cannot_change_review(client):
    review_id = create_review(client).get_json()["id"]
    other_guest = app_module.app.test_client()

    assert other_guest.put(
        f"/api/reviews/{review_id}",
        json={"rating": 1, "comment": "Changed"},
    ).status_code == 403
    assert other_guest.delete(f"/api/reviews/{review_id}").status_code == 403


def test_backend_rejects_self_vote(client):
    review_id = create_review(client).get_json()["id"]

    response = client.post(
        f"/api/reviews/{review_id}/vote",
        json={"vote_type": 1},
    )

    assert response.status_code == 403
    assert "own review" in response.get_json()["error"]


def test_account_review_visibility_and_bookmarks(client, monkeypatch):
    login_as(client, monkeypatch, name="Jamie Tan")

    anonymous = create_review(client, is_anonymous=True).get_json()
    assert anonymous["author"]["label"] == "Anonymous student"

    updated = client.put(
        f"/api/reviews/{anonymous['id']}",
        json={
            "rating": 4,
            "comment": "Named feedback",
            "is_anonymous": False,
        },
    ).get_json()
    assert updated["author"] == {
        "anonymous": False,
        "label": "Jamie Tan",
    }

    assert client.put("/api/bookmarks/C270").status_code == 200
    assert client.get("/api/bookmarks").get_json() == {
        "module_codes": ["C270"]
    }
    assert client.delete("/api/bookmarks/C270").status_code == 204
    assert client.get("/api/bookmarks").get_json() == {"module_codes": []}


def test_guest_claim_keeps_account_review_on_conflict(client, monkeypatch):
    guest_review = create_review(client, rating=2).get_json()
    other_guest = app_module.app.test_client()
    other_review = create_review(other_guest, "C110", rating=4).get_json()
    assert client.post(
        f"/api/reviews/{other_review['id']}/vote",
        json={"vote_type": 1},
    ).status_code == 200

    login_as(client, monkeypatch, name="Account Owner")
    account_review = create_review(client, rating=5).get_json()
    response = client.post(
        "/api/ownership/claim",
        json={"bookmark_codes": ["C270", "C110", "C270"]},
    )

    assert response.status_code == 200
    result = response.get_json()
    assert result["legacy_reviews"] == 1
    assert result["claimed_reviews"] == 0
    assert result["claimed_votes"] == 1
    assert result["bookmarks"] == 2

    reviews = client.get("/api/reviews/C270").get_json()
    account_row = next(row for row in reviews if row["id"] == account_review["id"])
    guest_row = next(row for row in reviews if row["id"] == guest_review["id"])
    assert account_row["is_owner"] is True
    assert guest_row["is_owner"] is False


def test_missing_csrf_token_rejects_mutation(client):
    app_module.app.config["WTF_CSRF_ENABLED"] = True
    page = client.get("/")
    token = re.search(
        rb'<meta name="csrf-token" content="([^"]+)"',
        page.data,
    ).group(1).decode()

    rejected = client.post(
        "/api/reviews",
        json={"module_code": "C270", "rating": 5, "comment": "No token"},
    )
    accepted = client.post(
        "/api/reviews",
        headers={"X-CSRFToken": token},
        json={"module_code": "C270", "rating": 5, "comment": "Protected"},
    )

    assert rejected.status_code == 400
    assert accepted.status_code == 201
