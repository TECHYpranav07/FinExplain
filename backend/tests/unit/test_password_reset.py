import pytest
import time
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.api.routes.v1.auth import PASSWORD_RESET_OTPS, USERS_DB

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_otp_store():
    """Clear in-memory OTP and users store before each test."""
    PASSWORD_RESET_OTPS.clear()
    USERS_DB.clear()
    yield
    PASSWORD_RESET_OTPS.clear()
    USERS_DB.clear()


@pytest.mark.asyncio
async def test_forgot_password_generates_valid_6digit_otp():
    """Test requesting a password reset generates a 6-digit OTP with 5m expiry and 2m cooldown."""
    with patch("app.api.routes.v1.auth.send_brevo_otp_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "borrower@example.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["resend_cooldown_seconds"] == 120
        assert data["expires_in_seconds"] == 300

        # Verify OTP entry in store
        entry = PASSWORD_RESET_OTPS.get("borrower@example.com")
        assert entry is not None
        assert len(entry["otp"]) == 6
        assert entry["otp"].isdigit()
        assert entry["used"] is False
        assert entry["expires_at"] > time.time() + 290
        assert entry["resend_available_at"] > time.time() + 110


def test_forgot_password_enforces_2min_resend_cooldown():
    """Test that requesting an OTP within 2 minutes is rate-limited (HTTP 429)."""
    with patch("app.api.routes.v1.auth.send_brevo_otp_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        # First request succeeds
        res1 = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "cooldown@example.com"}
        )
        assert res1.status_code == 200

        # Immediate second request fails with 429
        res2 = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "cooldown@example.com"}
        )
        assert res2.status_code == 429
        assert "Please wait" in res2.json()["detail"]


def test_resending_otp_after_cooldown_invalidates_old_otp():
    """Test that resending an OTP generates a new code and invalidates the old one."""
    with patch("app.api.routes.v1.auth.send_brevo_otp_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        # First OTP
        client.post("/api/v1/auth/forgot-password", json={"email": "resend@example.com"})
        old_otp = PASSWORD_RESET_OTPS["resend@example.com"]["otp"]

        # Fast-forward time past 2 minutes cooldown
        PASSWORD_RESET_OTPS["resend@example.com"]["resend_available_at"] = time.time() - 5

        # Request new OTP
        client.post("/api/v1/auth/forgot-password", json={"email": "resend@example.com"})
        new_otp = PASSWORD_RESET_OTPS["resend@example.com"]["otp"]

        # Attempt to reset with old OTP -> should fail
        fail_res = client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "resend@example.com",
                "otp": old_otp,
                "new_password": "NewSecurePassword123!"
            }
        )
        assert fail_res.status_code == 400

        # Attempt to reset with new OTP -> succeeds
        success_res = client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "resend@example.com",
                "otp": new_otp,
                "new_password": "NewSecurePassword123!"
            }
        )
        assert success_res.status_code == 200


def test_reset_password_rejects_expired_otp():
    """Test that an OTP older than 5 minutes is rejected."""
    with patch("app.api.routes.v1.auth.send_brevo_otp_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        client.post("/api/v1/auth/forgot-password", json={"email": "expired@example.com"})
        otp_code = PASSWORD_RESET_OTPS["expired@example.com"]["otp"]

        # Simulate 5+ minutes passing
        PASSWORD_RESET_OTPS["expired@example.com"]["expires_at"] = time.time() - 10

        res = client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "expired@example.com",
                "otp": otp_code,
                "new_password": "NewPassword123"
            }
        )
        assert res.status_code == 400
        assert "expired" in res.json()["detail"].lower()


import uuid

def test_reset_password_end_to_end_flow():
    """Test complete flow: Register -> Forgot Password -> Reset with OTP -> Sign In with new password."""
    with patch("app.api.routes.v1.auth.send_brevo_otp_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
        old_pwd = "OldPassword123"
        new_pwd = "BrandNewPassword456!"

        # 1. Register User
        reg_res = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": old_pwd,
            "name": "Test User"
        })
        assert reg_res.status_code == 200

        # 2. Request Forgot Password OTP
        forgot_res = client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert forgot_res.status_code == 200
        otp_code = PASSWORD_RESET_OTPS[email]["otp"]

        # 3. Reset Password with OTP
        reset_res = client.post("/api/v1/auth/reset-password", json={
            "email": email,
            "otp": otp_code,
            "new_password": new_pwd
        })
        assert reset_res.status_code == 200

        # 4. Old password should fail
        old_login_res = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": old_pwd
        })
        assert old_login_res.status_code == 401

        # 5. New password should succeed
        new_login_res = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": new_pwd
        })
        assert new_login_res.status_code == 200
        assert "access_token" in new_login_res.json()
