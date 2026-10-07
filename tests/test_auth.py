"""Unit and integration tests for Google Auth and JWT security."""

from unittest.mock import patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app


@pytest.fixture
def mock_google_user():
    return {
        "sub": "google-user-id-987654",
        "email": "investor.ritel@gmail.com",
        "name": "Budi Hartono",
        "picture": "https://lh3.googleusercontent.com/a/default-avatar",
        "email_verified": True,
    }


@pytest.mark.asyncio
async def test_google_login_success(mock_google_user):
    """Memverifikasi flow login Google berhasil menukarkan ID token menjadi JWT Tilik AI."""
    with patch("app.api.v1.endpoints.verify_google_id_token", return_value=mock_google_user):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/auth/google",
                json={"id_token": "mocked_valid_google_id_token"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert data["user"]["email"] == "investor.ritel@gmail.com"
            assert data["user"]["google_id"] == "google-user-id-987654"
            assert data["user"]["name"] == "Budi Hartono"


@pytest.mark.asyncio
async def test_google_login_invalid_token():
    """Memverifikasi penolakan (401) jika token Google palsu atau kedaluwarsa."""
    with patch(
        "app.api.v1.endpoints.verify_google_id_token",
        side_effect=ValueError("Token Google tidak valid atau kedaluwarsa"),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/auth/google",
                json={"id_token": "fake_expired_token"},
            )
            assert resp.status_code == 401
            assert "tidak valid" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_current_user_profile():
    """Memverifikasi endpoint /api/v1/auth/me mengembalikan profil pengguna yang login."""
    token_payload = {
        "sub": "google-112233",
        "email": "analis@sekuritas.id",
        "name": "Analis Handal",
        "picture": "https://example.com/pic.png",
    }
    jwt_token = create_access_token(token_payload)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Dengan token valid
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["email"] == "analis@sekuritas.id"
        assert data["user"]["google_id"] == "google-112233"

        # 2. Tanpa token (wajib 401)
        resp_unauth = await client.get("/api/v1/auth/me")
        assert resp_unauth.status_code == 401

        # 3. Dengan token rusak (wajib 401)
        resp_bad = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer token.abal.abal"},
        )
        assert resp_bad.status_code == 401
