"""Shared test configuration for isolated SQLite API tests."""

import pytest

import app as app_module


@pytest.fixture(autouse=True)
def configure_test_app():
    """Disable CSRF by default; dedicated tests enable it explicitly."""
    previous_testing = app_module.app.config.get("TESTING")
    previous_csrf = app_module.app.config.get("WTF_CSRF_ENABLED", True)
    app_module.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    yield
    app_module.app.config.update(
        TESTING=previous_testing,
        WTF_CSRF_ENABLED=previous_csrf,
    )
