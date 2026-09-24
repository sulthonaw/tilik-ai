"""Integration tests for FastAPI endpoints (POST /api/v1/verify, GET /api/v1/health)."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.core.cache import cache
from app.models.schemas import VerdictLevel


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear verification cache before each API test."""
    cache.clear()


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """Test GET /api/v1/health returns healthy status and RAG count."""
    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "Tilik AI Backend"
    assert data["version"] == "2.0.0"
    assert data["gemini_api"] in ["connected", "disconnected"]
    assert data["sectors_api"] == "connected"
    assert data["slang_rag_records"] >= 50


@pytest.mark.asyncio
async def test_root_health_alias(async_client: AsyncClient):
    """Test GET /health alias endpoint."""
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_verify_tweet_full_payload_structure(
    async_client: AsyncClient,
    mock_sectors_company_report,
    mock_sectors_quarterly,
    mock_sectors_top_brokers,
    mock_sectors_foreign_flow,
    mock_sectors_suspensions_clean,
):
    """Test POST /api/v1/verify ensures Level 1 and Level 2 fields are completely populated."""
    with (
        patch("app.services.sectors_client.SectorsAPIClient.get_company_report", new_callable=AsyncMock) as m_rep,
        patch("app.services.sectors_client.SectorsAPIClient.get_quarterly_financials", new_callable=AsyncMock) as m_q,
        patch("app.services.sectors_client.SectorsAPIClient.get_top_brokers", new_callable=AsyncMock) as m_b,
        patch("app.services.sectors_client.SectorsAPIClient.get_foreign_flow", new_callable=AsyncMock) as m_f,
        patch("app.services.sectors_client.SectorsAPIClient.get_suspensions", new_callable=AsyncMock) as m_s,
    ):
        m_rep.return_value = mock_sectors_company_report
        m_q.return_value = mock_sectors_quarterly
        m_b.return_value = mock_sectors_top_brokers
        m_f.return_value = mock_sectors_foreign_flow
        m_s.return_value = mock_sectors_suspensions_clean

        payload = {
            "text": "Si ijo mulai diserok bandar YP di harga gocap, valuasi salah harga to the moon!",
            "source_platform": "x",
        }
        resp = await async_client.post("/api/v1/verify", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        # Root fields
        assert data["status"] == "success"
        assert data["ticker"] == "GOTO"
        assert data["company_name"] == "GoTo Gojek Tokopedia Tbk"
        assert data["verdict"] in ["RED", "YELLOW", "GREEN"]
        assert 0.0 <= data["confidence_score"] <= 1.0
        assert data["is_cached"] is False

        # LEVEL 1: Summary Facts
        assert isinstance(data["points"], list)
        assert 1 <= len(data["points"]) <= 3
        for pt in data["points"]:
            assert "title" in pt
            assert "fact" in pt
            assert len(pt["fact"]) <= 150
            assert isinstance(pt["is_favorable"], bool)
        assert "cooling_off_prompt" in data
        assert len(data["cooling_off_prompt"]) > 10

        # LEVEL 2: Expanded Data
        details = data["details"]
        assert "valuation" in details
        assert "broker_flow" in details
        assert "financial_health" in details

        # Valuation sub-model
        val = details["valuation"]
        assert val["pbv_ratio"] == 2.4
        assert val["industry_median_pbv"] == 1.65
        assert "valuation_status" in val

        # Broker Flow sub-model
        flow = details["broker_flow"]
        assert flow["foreign_net_idr"] < 0
        assert len(flow["top_buyers"]) >= 1
        assert len(flow["top_sellers"]) >= 1
        assert flow["top_buyers"][0]["broker_code"] == "YP"
        assert "summary_verdict" in flow

        # Financial Health sub-model
        fin = details["financial_health"]
        assert fin["is_fca"] is False
        assert isinstance(fin["special_notations"], list)


@pytest.mark.asyncio
async def test_verify_tweet_sha256_cache_hit(
    async_client: AsyncClient,
    mock_sectors_company_report,
    mock_sectors_quarterly,
    mock_sectors_top_brokers,
    mock_sectors_foreign_flow,
    mock_sectors_suspensions_clean,
):
    """Test that second identical request returns cached result with is_cached=True."""
    with (
        patch("app.services.sectors_client.SectorsAPIClient.get_company_report", new_callable=AsyncMock) as m_rep,
        patch("app.services.sectors_client.SectorsAPIClient.get_quarterly_financials", new_callable=AsyncMock) as m_q,
        patch("app.services.sectors_client.SectorsAPIClient.get_top_brokers", new_callable=AsyncMock) as m_b,
        patch("app.services.sectors_client.SectorsAPIClient.get_foreign_flow", new_callable=AsyncMock) as m_f,
        patch("app.services.sectors_client.SectorsAPIClient.get_suspensions", new_callable=AsyncMock) as m_s,
    ):
        m_rep.return_value = mock_sectors_company_report
        m_q.return_value = mock_sectors_quarterly
        m_b.return_value = mock_sectors_top_brokers
        m_f.return_value = mock_sectors_foreign_flow
        m_s.return_value = mock_sectors_suspensions_clean

        payload = {"text": "Saham paman ditarik ke langit to the moon"}

        # First call -> cache miss
        resp1 = await async_client.post("/api/v1/verify", json=payload)
        assert resp1.status_code == 200
        assert resp1.json()["is_cached"] is False
        assert m_rep.call_count == 1

        # Second call with slightly different spacing -> cache hit (normalized text)
        payload_same = {"text": "  Saham  paman   ditarik ke langit to the moon  "}
        resp2 = await async_client.post("/api/v1/verify", json=payload_same)
        assert resp2.status_code == 200
        assert resp2.json()["is_cached"] is True
        # Verify Sectors API was not called again
        assert m_rep.call_count == 1


@pytest.mark.asyncio
async def test_verify_input_validation(async_client: AsyncClient):
    """Test input length constraints (< 5 chars or empty)."""
    # Too short
    resp_short = await async_client.post("/api/v1/verify", json={"text": "yo"})
    assert resp_short.status_code == 422

    # Whitespace only
    resp_space = await async_client.post("/api/v1/verify", json={"text": "      "})
    assert resp_space.status_code == 422
