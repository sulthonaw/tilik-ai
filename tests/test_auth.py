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


@pytest.mark.asyncio
async def test_user_role_setting_update_and_persistence():
    """Memverifikasi update settingan role (PEMULA vs EXPERT), case-insensitivity, dan persistensi."""
    token_payload = {
        "sub": "google-role-test-9988",
        "email": "trader.pro@sekuritas.id",
        "name": "Trader Pro",
    }
    jwt_token = create_access_token(token_payload)
    headers = {"Authorization": f"Bearer {jwt_token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Default role sebelum diset adalah PEMULA
        resp_initial = await client.get("/api/v1/auth/me", headers=headers)
        assert resp_initial.status_code == 200
        assert resp_initial.json()["user"]["user_role"] == "PEMULA"

        # 2. Update role ke EXPERT
        resp_update = await client.put(
            "/api/v1/user/settings",
            json={"user_role": "EXPERT"},
            headers=headers,
        )
        assert resp_update.status_code == 200
        assert resp_update.json()["user"]["user_role"] == "EXPERT"

        # 3. Cek kembali via /api/v1/auth/me (harus tetap EXPERT)
        resp_after = await client.get("/api/v1/auth/me", headers=headers)
        assert resp_after.status_code == 200
        assert resp_after.json()["user"]["user_role"] == "EXPERT"

        # 4. Tes toleransi huruf kecil (case-insensitive "pemula")
        resp_lower = await client.put(
            "/api/v1/user/settings",
            json={"user_role": "pemula"},
            headers=headers,
        )
        assert resp_lower.status_code == 200
        assert resp_lower.json()["user"]["user_role"] == "PEMULA"

        # 5. Nilai role tidak valid wajib ditolak (422)
        resp_invalid = await client.put(
            "/api/v1/user/settings",
            json={"user_role": "MASTER"},
            headers=headers,
        )
        assert resp_invalid.status_code == 422


@pytest.mark.asyncio
async def test_verify_tweet_respects_user_role_setting_and_guest_fallback():
    """Memverifikasi endpoint /api/v1/verify mengadopsi preferensi role user dan fallback guest."""
    # 1. Tes Guest tanpa menyertakan user_role -> Otomatis PEMULA, tidak crash NoneType
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        guest_resp = await client.post(
            "/api/v1/verify",
            json={"text": "Si ijo mulai diserok bandar YP di harga gocap to the moon"},
        )
        assert guest_resp.status_code == 200
        assert guest_resp.json()["user_role"] == "PEMULA"
        # Memastikan poin fakta Level 1 menggunakan judul ramah pemula
        point_titles = [p["title"] for p in guest_resp.json()["points"]]
        assert "Kewajaran Harga Saham" in point_titles or "Arus Dana Asing" in point_titles

        # 2. Tes Logged in User dengan settingan EXPERT
        token_payload = {
            "sub": "google-expert-user-777",
            "email": "analyst@hedgefund.com",
            "name": "Senior Analyst",
        }
        jwt_token = create_access_token(token_payload)
        auth_headers = {"Authorization": f"Bearer {jwt_token}"}

        # Set user setting ke EXPERT
        await client.put(
            "/api/v1/user/settings",
            json={"user_role": "EXPERT"},
            headers=auth_headers,
        )

        # Hit verifikasi tanpa menyertakan field user_role
        user_resp = await client.post(
            "/api/v1/verify",
            json={"text": "Si ijo mulai diserok bandar YP di harga gocap to the moon"},
            headers=auth_headers,
        )
        assert user_resp.status_code == 200
        assert user_resp.json()["user_role"] == "EXPERT"
        # Memastikan format fakta Level 1 menggunakan istilah metrik industri
        expert_titles = [p["title"] for p in user_resp.json()["points"]]
        assert "Valuasi Relatif" in expert_titles or "Arus Transaksi Asing" in expert_titles
