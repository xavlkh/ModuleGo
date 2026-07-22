import pytest

import app as app_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_database = tmp_path / "modulego-test.db"
    monkeypatch.setattr(app_module, "db_name", str(test_database))
    app_module.init_db()
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as test_client:
        yield test_client


def create_review(client, module_code="C270", rating=5, comment="Very useful"):
    return client.post(
        "/api/reviews",
        json={
            "module_code": module_code,
            "rating": rating,
            "comment": comment,
        },
    )


def test_pages_are_available(client):
    assert client.get("/").status_code == 200
    assert client.get("/comparison").status_code == 200
    assert client.get("/bookmarks").status_code == 200
    assert client.get("/reviews").status_code == 200


def test_create_and_read_review(client):
    response = create_review(client)

    assert response.status_code == 201
    created = response.get_json()
    assert created["id"] > 0
    assert created["module_code"] == "C270"
    assert created["rating"] == 5
    assert created["comment"] == "Very useful"
    assert created["created_at"] is not None

    response = client.get("/api/reviews/C270")
    assert response.status_code == 200
    assert response.get_json() == [created]


def test_module_code_and_comment_are_normalized(client):
    response = create_review(
        client,
        module_code=" c270 ",
        comment="  Clear explanations.  ",
    )

    assert response.status_code == 201
    review = response.get_json()
    assert review["module_code"] == "C270"
    assert review["comment"] == "Clear explanations."


@pytest.mark.parametrize("rating", [0, 6, -1, "5", True, None])
def test_invalid_ratings_are_rejected(client, rating):
    response = create_review(client, rating=rating)

    assert response.status_code == 400
    assert "Rating" in response.get_json()["error"]


def test_missing_or_invalid_json_is_rejected(client):
    response = client.post("/api/reviews")
    assert response.status_code == 400
    assert response.get_json()["error"] == "A JSON request body is required."

    response = client.post("/api/reviews", json={"rating": 4})
    assert response.status_code == 400
    assert response.get_json()["error"] == "Module code is required."


def test_comment_validation(client):
    response = create_review(client, comment=123)
    assert response.status_code == 400
    assert response.get_json()["error"] == "Comment must be text."

    response = create_review(client, comment="x" * 501)
    assert response.status_code == 400
    assert "500 characters or fewer" in response.get_json()["error"]


def test_rating_summaries(client):
    create_review(client, rating=5, comment="Excellent")
    create_review(client, rating=4, comment="Good")
    create_review(client, module_code="C110", rating=3, comment="Okay")

    response = client.get("/api/ratings")
    assert response.status_code == 200
    summaries = response.get_json()
    assert summaries["C270"] == {
        "average_rating": 4.5,
        "review_count": 2,
        "distribution": {
            "5": 1,
            "4": 1,
            "3": 0,
            "2": 0,
            "1": 0,
        },
    }
    assert summaries["C110"] == {
        "average_rating": 3.0,
        "review_count": 1,
        "distribution": {
            "5": 0,
            "4": 0,
            "3": 1,
            "2": 0,
            "1": 0,
        },
    }


def test_rating_distribution_reveals_disagreement(client):
    for _ in range(5):
        create_review(client, rating=5)
        create_review(client, rating=1)

    summary = client.get("/api/ratings").get_json()["C270"]

    assert summary == {
        "average_rating": 3.0,
        "review_count": 10,
        "distribution": {
            "5": 5,
            "4": 0,
            "3": 0,
            "2": 0,
            "1": 5,
        },
    }


def test_rating_distribution_tracks_update_and_delete(client):
    five_star_id = create_review(client, rating=5).get_json()["id"]
    one_star_id = create_review(client, rating=1).get_json()["id"]

    update_response = client.put(
        f"/api/reviews/{five_star_id}",
        json={"rating": 3, "comment": "Updated rating"},
    )
    assert update_response.status_code == 200

    updated_summary = client.get("/api/ratings").get_json()["C270"]
    assert updated_summary["average_rating"] == 2.0
    assert updated_summary["review_count"] == 2
    assert updated_summary["distribution"] == {
        "5": 0,
        "4": 0,
        "3": 1,
        "2": 0,
        "1": 1,
    }

    delete_response = client.delete(f"/api/reviews/{one_star_id}")
    assert delete_response.status_code == 204

    deleted_summary = client.get("/api/ratings").get_json()["C270"]
    assert deleted_summary == {
        "average_rating": 3.0,
        "review_count": 1,
        "distribution": {
            "5": 0,
            "4": 0,
            "3": 1,
            "2": 0,
            "1": 0,
        },
    }


def test_list_all_reviews_for_dashboard(client):
    create_review(client, module_code="C270", rating=5)
    create_review(client, module_code="C110", rating=3)

    response = client.get("/api/reviews")
    assert response.status_code == 200
    assert {review["module_code"] for review in response.get_json()} == {
        "C270",
        "C110",
    }


def test_update_review(client):
    review_id = create_review(client).get_json()["id"]
    response = client.put(
        f"/api/reviews/{review_id}",
        json={"rating": 2, "comment": "Changed my mind"},
    )

    assert response.status_code == 200
    updated = response.get_json()
    assert updated["rating"] == 2
    assert updated["comment"] == "Changed my mind"
    assert updated["updated_at"] is not None

    stored = client.get("/api/reviews/C270").get_json()[0]
    assert stored["rating"] == 2


def test_delete_review(client):
    review_id = create_review(client).get_json()["id"]

    response = client.delete(f"/api/reviews/{review_id}")
    assert response.status_code == 204
    assert client.get("/api/reviews/C270").get_json() == []


def test_update_and_delete_unknown_review_return_404(client):
    update_response = client.put(
        "/api/reviews/9999",
        json={"rating": 4, "comment": "Missing"},
    )
    delete_response = client.delete("/api/reviews/9999")

    assert update_response.status_code == 404
    assert delete_response.status_code == 404

