"""Tests for transient Gemini-powered module comparisons."""

import pytest

import app as app_module

MODULES = [
    {
        "code": "C270",
        "name": "DevOps",
        "school": "School of Infocomm",
        "synopsis": "Learn deployment automation through practical projects.",
    },
    {
        "code": "C273",
        "name": "Advanced Web Development",
        "school": "School of Infocomm",
        "synopsis": "Build full-stack web applications in project teams.",
    },
]


@pytest.fixture()
def client(monkeypatch):
    """Provide a client with a deterministic in-memory module catalogue."""
    monkeypatch.setitem(app_module._modules_cache, "data", MODULES)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    with app_module.app.test_client() as test_client:
        yield test_client


def test_dynamic_comparison_returns_gemini_content(client, monkeypatch):
    """Return transient generated fields for the selected modules."""
    generated = [
        {
            "module_code": "C270",
            "summary": (
                "Covers deployment automation and collaborative delivery "
                "practices through practical project-based work."
            ),
            "suitable_for": (
                "Students interested in cloud platforms, automation, and "
                "software delivery."
            ),
            "workload": {
                "level": "Moderate",
                "confidence": "Medium",
                "reason": "The synopsis explicitly includes practical project work.",
            },
        },
        {
            "module_code": "C273",
            "summary": (
                "Covers advanced full-stack development through collaborative "
                "implementation of modern web applications."
            ),
            "suitable_for": (
                "Students interested in web engineering, application "
                "development, and teamwork."
            ),
            "workload": {
                "level": "High",
                "confidence": "Medium",
                "reason": (
                    "Full-stack team projects suggest sustained "
                    "implementation work."
                ),
            },
        },
    ]
    monkeypatch.setattr(
        app_module,
        "generate_gemini_comparison",
        lambda modules: generated,
    )

    response = client.post(
        "/api/comparison/generate",
        json={"module_codes": ["c270", " C273 "]},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["provider"] == "Gemini"
    assert payload["modules"] == generated


@pytest.mark.parametrize(
    "payload,error",
    [
        (None, "A JSON request body is required."),
        ({}, "Exactly two module codes are required."),
        ({"module_codes": ["C270"]}, "Exactly two module codes are required."),
        (
            {"module_codes": ["C270", "C270"]},
            "Choose two different modules.",
        ),
        (
            {"module_codes": ["C270", 273]},
            "Each module code must be non-empty text.",
        ),
    ],
)
def test_dynamic_comparison_validates_payload(client, payload, error):
    """Reject malformed or duplicate module selections before calling Gemini."""
    response = client.post("/api/comparison/generate", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == error


def test_dynamic_comparison_rejects_unknown_module(client):
    """Only allow Gemini requests for modules in the server-side catalogue."""
    response = client.post(
        "/api/comparison/generate",
        json={"module_codes": ["C270", "C999"]},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "Unknown module code: C999."


def test_dynamic_comparison_handles_missing_configuration(client, monkeypatch):
    """Return a safe service error when the Gemini key is missing."""
    monkeypatch.delenv("GEMINI_API_KEY")

    response = client.post(
        "/api/comparison/generate",
        json={"module_codes": ["C270", "C273"]},
    )

    assert response.status_code == 503
    assert response.get_json()["error"] == (
        "Dynamic comparison is not configured."
    )


def test_dynamic_comparison_handles_provider_failure(client, monkeypatch):
    """Keep upstream Gemini failures private and return a stable API error."""
    def raise_service_error(modules):
        raise app_module.GeminiServiceError()

    monkeypatch.setattr(
        app_module,
        "generate_gemini_comparison",
        raise_service_error,
    )

    response = client.post(
        "/api/comparison/generate",
        json={"module_codes": ["C270", "C273"]},
    )

    assert response.status_code == 502
    assert response.get_json()["error"] == (
        "Dynamic comparison is temporarily unavailable."
    )
