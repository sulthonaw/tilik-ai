"""Unit and integration tests for Verification History endpoints and click-to-detail flow."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app


@pytest.mark.asyncio
async def test_verification_creates_history_and_click_to_detail():
    """Memverifikasi cuitan yang diverifikasi otomatis masuk riwayat dan bisa diklik ke detailnya."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Jalankan verifikasi cuitan
        verify_resp = await client.post(
            "/api/v1/verify",
            json={
                "text": "Si ijo mulai diserok bandar YP di harga gocap to the moon!",
                "source_platform": "x",
            },
        )
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        assert "history_id" in verify_data
        assert verify_data["history_id"] is not None
        hist_id = verify_data["history_id"]

        # 2. Ambil daftar riwayat (GET /api/v1/history)
        list_resp = await client.get("/api/v1/history?limit=10")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["status"] == "success"
        assert list_data["total"] >= 1
        found = any(item["id"] == hist_id for item in list_data["items"])
        assert found, f"ID {hist_id} tidak ditemukan di daftar history"

        # 3. Klik ke detail riwayat (GET /api/v1/history/{history_id})
        detail_resp = await client.get(f"/api/v1/history/{hist_id}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["status"] == "success"
        assert detail_data["id"] == hist_id
        assert "Si ijo" in detail_data["tweet_text"]

        # Validasi Level 1 data di dalam riwayat
        verification = detail_data["verification"]
        assert verification["ticker"] == "GOTO"
        assert len(verification["points"]) >= 1

        # Validasi Level 2 data (Zero Latency data) lengkap di dalam riwayat
        assert "details" in verification
        assert "valuation" in verification["details"]
        assert "broker_flow" in verification["details"]
        assert "financial_health" in verification["details"]


@pytest.mark.asyncio
async def test_user_history_isolation():
    """Memverifikasi pemisahan riwayat antar akun pengguna (User A vs User B)."""
    token_a = create_access_token({"sub": "user-a-111", "email": "usera@gmail.com"})
    token_b = create_access_token({"sub": "user-b-222", "email": "userb@gmail.com"})

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # User A melakukan verifikasi cuitan
        resp_a = await client.post(
            "/api/v1/verify",
            json={"text": "Saham paman ditarik ke langit om pp masuk BREN"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_a.status_code == 200
        hist_id_a = resp_a.json()["history_id"]

        # User A cek history miliknya
        list_a = await client.get("/api/v1/history", headers={"Authorization": f"Bearer {token_a}"})
        assert list_a.status_code == 200
        ids_a = [item["id"] for item in list_a.json()["items"]]
        assert hist_id_a in ids_a

        # User B cek history miliknya -> tidak boleh melihat riwayat User A
        list_b = await client.get("/api/v1/history", headers={"Authorization": f"Bearer {token_b}"})
        assert list_b.status_code == 200
        ids_b = [item["id"] for item in list_b.json()["items"]]
        assert hist_id_a not in ids_b


@pytest.mark.asyncio
async def test_history_deletion_and_404():
    """Memverifikasi penghapusan riwayat individual dan penanganan ID yang tidak ada."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Buat verifikasi
        resp = await client.post(
            "/api/v1/verify",
            json={"text": "Beceha dividen interim cair lagi mantap BBCA"},
        )
        hist_id = resp.json()["history_id"]

        # Hapus riwayat
        del_resp = await client.delete(f"/api/v1/history/{hist_id}")
        assert del_resp.status_code == 200

        # Cek detail setelah dihapus (wajib 404)
        get_deleted = await client.get(f"/api/v1/history/{hist_id}")
        assert get_deleted.status_code == 404

        # Hapus ID yang tidak ada (wajib 404)
        del_fake = await client.delete("/api/v1/history/hist_non_existent_999")
        assert del_fake.status_code == 404
