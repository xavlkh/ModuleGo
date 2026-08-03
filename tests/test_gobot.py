"""Tests for the GoBot chatbot API and additional API route coverage."""


import pytest

import app as app_module
from tests.conftest import create_review

TEST_MODULES = [
    {"code": "C270", "name": "Mobile App Development",
     "synopsis": "Build mobile apps using Flutter and React Native",
     "school": "School of Infocomm", "school_abbr": "SOC",
     "url": "https://example.com"},
    {"code": "C110", "name": "Web Development",
     "synopsis": "Build websites using HTML CSS JavaScript",
     "school": "School of Infocomm", "school_abbr": "SOC",
     "url": "https://example.com"},
    {"code": "C273", "name": "Advanced Web Development",
     "synopsis": "Full-stack web applications with databases",
     "school": "School of Infocomm", "school_abbr": "SOC",
     "url": "https://example.com"},
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "db_name", str(tmp_path / "gobot-test.db"))
    app_module.init_db()
    monkeypatch.setitem(app_module._modules_cache, "data", TEST_MODULES)
    monkeypatch.setattr('app.routes.api._build_modules_list', lambda: TEST_MODULES)
    with app_module.app.test_client() as c:
        yield c


class TestGoBotChat:

    def test_empty_message(self, client):
        response = client.post("/api/gobot", json={"message": ""})
        assert response.status_code == 200
        data = response.get_json()
        assert "Ask me about careers" in data["reply"]

    def test_no_message(self, client):
        response = client.post("/api/gobot", json={})
        assert response.status_code == 200
        data = response.get_json()
        assert "Ask me about careers" in data["reply"]

    def test_module_lookup(self, client):
        response = client.post("/api/gobot", json={"message": "C270"})
        assert response.status_code == 200
        data = response.get_json()
        assert "C270" in data["reply"]
        assert "Mobile App Development" in data["reply"]

    def test_module_lookup_case_insensitive(self, client):
        response = client.post("/api/gobot", json={"message": "c270"})
        assert response.status_code == 200
        data = response.get_json()
        assert "C270" in data["reply"]

    def test_greeting(self, client):
        response = client.post("/api/gobot", json={"message": "hello there"})
        assert response.status_code == 200
        data = response.get_json()
        assert "Hi!" in data["reply"]
        assert len(data["suggestions"]) > 0

    def test_reviews_lookup(self, client):
        create_review(client, module_code="C270", rating=5, comment="Great")
        response = client.post("/api/gobot", json={
            "message": "reviews for C270"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "C270" in data["reply"]

    def test_reviews_lookup_no_reviews(self, client):
        response = client.post("/api/gobot", json={
            "message": "reviews for C110"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "no reviews yet" in data["reply"].lower() or "C110" in data["reply"]

    def test_reviews_unknown_module(self, client):
        response = client.post("/api/gobot", json={
            "message": "reviews for Z999"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "Couldn't find" in data["reply"]

    def test_navigation_help(self, client):
        response = client.post("/api/gobot", json={
            "message": "how do I navigate this site"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "Search Modules" in [link["text"] for link in data["links"]]

    def test_modulego_mention(self, client):
        response = client.post("/api/gobot", json={
            "message": "what is modulego"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "Republic Polytechnic" in data["reply"]

    def test_modulego_space_variant(self, client):
        response = client.post("/api/gobot", json={
            "message": "tell me about module go"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "Republic Polytechnic" in data["reply"]

    def test_career_recommendation(self, client, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "")
        response = client.post("/api/gobot", json={
            "message": "I want to be a Data Analyst"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "reply" in data

    def test_history_is_truncated(self, client):
        history = [{"role": "user", "text": "x" * 600}] * 10
        response = client.post("/api/gobot", json={
            "message": "hello",
            "history": history,
        })
        assert response.status_code == 200

    def test_module_not_in_catalogue(self, client):
        response = client.post("/api/gobot", json={"message": "Z999"})
        assert response.status_code == 200
        data = response.get_json()
        assert "Tell me about" in data["reply"]

    def test_fallback_message(self, client):
        response = client.post("/api/gobot", json={
            "message": "asdfghjkl"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "interests" in data["reply"].lower() or "career" in data["reply"].lower()


class TestModulesEndpoint:

    def test_modules_returns_list(self, client):
        response = client.get("/api/modules")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_modules_with_cache(self, client):
        app_module._modules_cache["data"] = [{"code": "C270"}]
        app_module._modules_cache["timestamp"] = 9999999999
        response = client.get("/api/modules")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1


class TestCoursesEndpoint:

    def test_courses_returns_list(self, client):
        response = client.get("/api/courses")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list) or isinstance(data, dict)

    def test_courses_with_cache(self, client):
        app_module._courses_cache["data"] = [{"course_code": "RS12"}]
        app_module._courses_cache["timestamp"] = 9999999999
        response = client.get("/api/courses")
        assert response.status_code == 200


class TestMinorsEndpoint:

    def test_minors_returns_data(self, client):
        response = client.get("/api/minors")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list) or isinstance(data, dict)

    def test_minors_with_cache(self, client):
        app_module._minors_cache["data"] = [{"minor_name": "AI"}]
        app_module._minors_cache["timestamp"] = 9999999999
        response = client.get("/api/minors")
        assert response.status_code == 200


class TestCareerPathsEndpoint:

    def test_career_paths_returns_list(self, client):
        response = client.get("/api/career-paths")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) > 0


class TestBulkVotesEndpoint:

    def test_bulk_votes_requires_array(self, client):
        response = client.post("/api/reviews/votes", json={})
        assert response.status_code == 400

    def test_bulk_votes_rejects_non_array(self, client):
        response = client.post("/api/reviews/votes", json={
            "review_ids": "not an array"
        })
        assert response.status_code == 400

    def test_bulk_votes_returns_empty(self, client):
        response = client.post("/api/reviews/votes", json={
            "review_ids": []
        })
        assert response.status_code == 200
        assert response.get_json() == {}


class TestVoteEndpoints:

    def test_get_votes(self, client):
        review_id = create_review(client).get_json()["id"]
        response = client.get(f"/api/reviews/{review_id}/vote")
        assert response.status_code == 200
        data = response.get_json()
        assert data["score"] == 0
        assert data["user_vote"] == 0

    def test_vote_requires_vote_type(self, client):
        review_id = create_review(client).get_json()["id"]
        response = client.post(f"/api/reviews/{review_id}/vote", json={})
        assert response.status_code == 400

    def test_vote_invalid_type(self, client):
        review_id = create_review(client).get_json()["id"]
        response = client.post(
            f"/api/reviews/{review_id}/vote",
            json={"vote_type": 5}
        )
        assert response.status_code == 400

    def test_upvote(self, client):
        other = app_module.app.test_client()
        review_id = create_review(other).get_json()["id"]
        response = client.post(
            f"/api/reviews/{review_id}/vote",
            json={"vote_type": 1}
        )
        assert response.status_code == 200
        assert response.get_json()["action"] == "added"

    def test_remove_vote(self, client):
        other = app_module.app.test_client()
        review_id = create_review(other).get_json()["id"]
        client.post(
            f"/api/reviews/{review_id}/vote",
            json={"vote_type": 1}
        )
        response = client.delete(f"/api/reviews/{review_id}/vote")
        assert response.status_code == 204


class TestRatingSummaries:

    def test_ratings_empty(self, client):
        response = client.get("/api/ratings")
        assert response.status_code == 200
        assert response.get_json() == {}

    def test_ratings_with_reviews(self, client):
        create_review(client, rating=5)
        response = client.get("/api/ratings")
        assert response.status_code == 200
        data = response.get_json()
        assert "C270" in data
        assert data["C270"]["average_rating"] == 5.0
        assert data["C270"]["review_count"] == 1
