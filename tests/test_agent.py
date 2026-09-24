"""Tests for LangGraph agent workflow, nodes, and fallback on upstream API failure."""

import asyncio
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.agent.graph import run_verification, verification_graph
from app.agent.nodes import (
    concurrent_fetch_node,
    evaluator_node,
    intent_node,
    ner_slang_node,
    synthesizer_node,
)
from app.models.schemas import VerdictLevel, VerificationResponse
from app.models.state import AgentState


@pytest.mark.asyncio
async def test_full_graph_execution_goto(
    mock_sectors_company_report,
    mock_sectors_quarterly,
    mock_sectors_top_brokers,
    mock_sectors_foreign_flow,
    mock_sectors_suspensions_clean,
):
    """Test full LangGraph execution for GOTO with mocked Sectors API responses."""
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

        tweet = "Si ijo mulai diserok bandar YP di harga gocap, valuasi salah harga to the moon!"
        res: VerificationResponse = await run_verification(tweet)

        assert res.status == "success"
        assert res.ticker == "GOTO"
        assert res.company_name == "GoTo Gojek Tokopedia Tbk"
        assert res.verdict == VerdictLevel.RED  # High valuation + foreign net sell + manipulative hype
        assert res.confidence_score >= 0.8
        assert 1 <= len(res.points) <= 3
        for pt in res.points:
            assert len(pt.fact) <= 150
            assert pt.title

        # Check Level 2 details completeness
        assert res.details.valuation.pbv_ratio == 2.4
        assert res.details.valuation.industry_median_pbv == 1.65
        assert "Lebih Mahal" in res.details.valuation.valuation_status
        assert res.details.broker_flow.foreign_net_idr < 0
        assert len(res.details.broker_flow.top_buyers) >= 1
        assert res.details.financial_health.is_fca is False


@pytest.mark.asyncio
async def test_fallback_on_sectors_api_timeout():
    """Verify that when Sectors API times out or raises an error, the workflow completes gracefully."""
    with (
        patch(
            "app.services.sectors_client.SectorsAPIClient.get_company_report",
            side_effect=httpx.TimeoutException("Connection timed out to sectors.app"),
        ),
        patch(
            "app.services.sectors_client.SectorsAPIClient.get_quarterly_financials",
            side_effect=httpx.ConnectError("Network unreachable"),
        ),
        patch(
            "app.services.sectors_client.SectorsAPIClient.get_top_brokers",
            side_effect=httpx.TimeoutException("Timeout"),
        ),
        patch(
            "app.services.sectors_client.SectorsAPIClient.get_foreign_flow",
            side_effect=httpx.TimeoutException("Timeout"),
        ),
        patch(
            "app.services.sectors_client.SectorsAPIClient.get_suspensions",
            side_effect=httpx.TimeoutException("Timeout"),
        ),
    ):
        tweet = "Si ijo diserok bandar YP to the moon"
        res = await run_verification(tweet)

        # Verification must still succeed using fallbacks, never 500 crash
        assert isinstance(res, VerificationResponse)
        assert res.ticker == "GOTO"
        assert res.verdict in [VerdictLevel.RED, VerdictLevel.YELLOW, VerdictLevel.GREEN]
        assert len(res.points) >= 1
        assert res.details.valuation.valuation_status is not None


@pytest.mark.asyncio
async def test_fca_stock_verdict_red(
    mock_sectors_company_report,
    mock_sectors_quarterly,
    mock_sectors_top_brokers,
    mock_sectors_foreign_flow,
    mock_sectors_suspensions_fca,
):
    """Verify that any stock on FCA / Special Monitoring Board receives a RED verdict."""
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
        m_s.return_value = mock_sectors_suspensions_fca

        tweet = "Beli GOTO sekarang prospek cerah!"
        res = await run_verification(tweet)

        assert res.verdict == VerdictLevel.RED
        assert res.details.financial_health.is_fca is True


@pytest.mark.asyncio
async def test_agent_node_state_transitions(
    mock_sectors_company_report,
    mock_sectors_quarterly,
    mock_sectors_top_brokers,
    mock_sectors_foreign_flow,
    mock_sectors_suspensions_clean,
):
    """Verify individual node state transitions in LangGraph."""
    initial_state: AgentState = {
        "raw_text": "Saham paman ditarik ke langit",
        "source_platform": "x",
    }

    # Node 1
    ner_out = await ner_slang_node(initial_state)
    assert ner_out["detected_ticker"] == "BREN"
    assert "paman" in ner_out["detected_slangs"]

    # Node 2
    state_after_ner = {**initial_state, **ner_out}
    intent_out = await intent_node(state_after_ner)
    assert len(intent_out["claims"]) > 0

    # Node 3 with mocked Sectors API
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

        state_after_intent = {**state_after_ner, **intent_out}
        fetch_out = await concurrent_fetch_node(state_after_intent)
        assert "sectors_data" in fetch_out

        # Node 4
        state_after_fetch = {**state_after_intent, **fetch_out}
        eval_out = await evaluator_node(state_after_fetch)
        assert "evaluation" in eval_out
        assert eval_out["evaluation"]["verdict"] in [VerdictLevel.RED, VerdictLevel.YELLOW, VerdictLevel.GREEN]

        # Node 5
        state_after_eval = {**state_after_fetch, **eval_out}
        synth_out = await synthesizer_node(state_after_eval)
        assert "response" in synth_out
        assert isinstance(synth_out["response"], VerificationResponse)
