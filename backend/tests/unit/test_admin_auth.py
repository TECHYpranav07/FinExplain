from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.routes.v1.auth import USERS_DB
from app.core.config import settings
from app.main import app


client = TestClient(app)


def test_configured_admin_login_returns_admin_token(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "configured-admin@example.com")
    monkeypatch.setattr(settings, "ADMIN_PS", "strong-test-password")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "")
    USERS_DB.clear()

    with patch("app.api.routes.v1.auth.get_user_by_email", return_value=None), patch(
        "app.api.routes.v1.auth.ensure_user_exists", return_value=None
    ):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": " CONFIGURED-ADMIN@EXAMPLE.COM ", "password": "strong-test-password"},
        )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "admin"
    USERS_DB.clear()


def test_admin_login_is_disabled_without_configured_password(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setattr(settings, "ADMIN_PS", None)
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "")
    USERS_DB.clear()

    with patch("app.api.routes.v1.auth.get_user_by_email", return_value=None):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin123"},
        )

    assert response.status_code == 401
