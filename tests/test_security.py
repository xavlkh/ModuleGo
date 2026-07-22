"""Security-focused tests for ModuleGo Flask application.

Covers input sanitisation, SQL injection, XSS storage, mass assignment,
and boundary conditions.
"""
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


def _create_review(client, **overrides):
    payload = {"module_code": "C270", "rating": 5, "comment": "Good"}
    payload.update(overrides)
    return client.post("/api/reviews", json=payload)


class TestMassAssignment:
    """Verify extra payload fields are stripped (anti-mass-assignment)."""

    def test_extra_fields_are_ignored(self, client):
        response = _create_review(client, extra_field="should_not_exist", malicious="data")
        assert response.status_code == 201
        review = response.get_json()
        assert "extra_field" not in review
        assert "malicious" not in review


class TestSQLInjection:
    """Verify parameterised queries prevent SQL injection."""

    @pytest.mark.parametrize("payload", [
        {"module_code": "C270'; DROP TABLE REVIEWS; --"},
        {"module_code": "C270\" OR 1=1; --"},
        {"module_code": "C270 UNION SELECT * FROM REVIEWS"},
        {"module_code": "C270'/*"},  # unclosed comment
        {"module_code": "' OR '1'='1"},
        {"module_code": "C270; SELECT * FROM sqlite_master; --"},
    ])
    def test_sql_injection_in_module_code_is_rejected_or_safe(self, client, payload):
        response = _create_review(client, **payload)
        assert response.status_code in (201, 400)
        if response.status_code == 201:
            review = response.get_json()
            assert review["module_code"] == payload["module_code"].strip().upper()[:20]

    def test_injection_in_comment_does_not_corrupt_db(self, client):
        payload = {"comment": "'; DROP TABLE REVIEWS; --"}
        response = _create_review(client, **payload)
        assert response.status_code == 201
        response = client.get("/api/reviews")
        assert response.status_code == 200
        assert len(response.get_json()) == 1

    def test_injection_in_module_code_does_not_break_listing(self, client):
        _create_review(client, module_code="A' OR '1'='1")
        response = client.get("/api/reviews")
        assert response.status_code == 200
        assert len(response.get_json()) == 1


class TestXSSStorage:
    """Verify XSS payloads are stored as-is (escaping is client-side)."""

    XSS_PAYLOADS = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert(1)",
        "<svg onload=alert(1)>",
        "\"><script>alert(1)</script>",
        "&lt;script&gt;alert(1)&lt;/script&gt;",
    ]

    @pytest.mark.parametrize("xss", XSS_PAYLOADS)
    def test_xss_in_comment_is_stored_verbatim(self, client, xss):
        response = _create_review(client, comment=xss)
        assert response.status_code == 201
        review = response.get_json()
        assert review["comment"] == xss

    @pytest.mark.parametrize("xss", XSS_PAYLOADS)
    def test_xss_in_module_code_is_truncated_or_stored(self, client, xss):
        response = _create_review(client, module_code=xss)
        assert response.status_code in (201, 400)
        if response.status_code == 201:
            review = response.get_json()
            stored = review["module_code"]
            assert "<" not in stored and ">" not in stored


class TestBoundaryConditions:
    """Edge-case input boundaries."""

    def test_module_code_exactly_20_chars(self, client):
        code = "A" * 20
        response = _create_review(client, module_code=code)
        assert response.status_code == 201
        assert response.get_json()["module_code"] == code

    def test_module_code_21_chars_is_rejected(self, client):
        response = _create_review(client, module_code="A" * 21)
        assert response.status_code == 400
        assert "too long" in response.get_json()["error"].lower()

    def test_comment_exactly_500_chars(self, client):
        comment = "x" * 500
        response = _create_review(client, comment=comment)
        assert response.status_code == 201
        assert response.get_json()["comment"] == comment

    def test_empty_comment_is_allowed(self, client):
        response = _create_review(client, comment="")
        assert response.status_code == 201
        assert response.get_json()["comment"] == ""

    def test_comment_with_only_whitespace_is_stored_empty(self, client):
        response = _create_review(client, comment="   ")
        assert response.status_code == 201
        assert response.get_json()["comment"] == ""

    def test_null_bytes_in_comment(self, client):
        response = _create_review(client, comment="safe\x00malicious")
        assert response.status_code == 201
        review = response.get_json()
        assert "\x00" in review["comment"]

    def test_unicode_in_comment(self, client):
        comment = "★ 5 stars — très bien! 日本語"
        response = _create_review(client, comment=comment)
        assert response.status_code == 201
        assert response.get_json()["comment"] == comment

    def test_module_code_with_hyphens(self, client):
        response = _create_review(client, module_code="A-B-C-D-E")
        assert response.status_code == 201
        assert response.get_json()["module_code"] == "A-B-C-D-E"


class TestURLParameterValidation:
    """Verify invalid review_id falls through to string route (405)."""

    def test_non_integer_review_id_on_update_returns_405(self, client):
        response = client.put("/api/reviews/abc", json={"rating": 3})
        assert response.status_code == 405

    def test_non_integer_review_id_on_delete_returns_405(self, client):
        response = client.delete("/api/reviews/abc")
        assert response.status_code == 405

    def test_negative_review_id_returns_405(self, client):
        response = client.put("/api/reviews/-1", json={"rating": 3})
        assert response.status_code == 405

    def test_float_review_id_returns_405(self, client):
        response = client.put("/api/reviews/1.5", json={"rating": 3})
        assert response.status_code == 405


class TestHTTPMethodEnforcement:
    """Verify wrong HTTP methods are rejected."""

    def test_put_on_collection_returns_405(self, client):
        response = client.put("/api/reviews")
        assert response.status_code == 405

    def test_delete_on_collection_returns_405(self, client):
        response = client.delete("/api/reviews")
        assert response.status_code == 405

    def test_post_on_single_review_returns_405(self, client):
        response = client.post("/api/reviews/1")
        assert response.status_code == 405
