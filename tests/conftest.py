"""Pytest fixtures and configuration for Tilik AI test suite."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any, Dict, List

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.rag.slang_store import slang_store


@pytest.fixture(scope="session", autouse=True)
def init_test_slang_store():
    """Ensure slang dictionary and vector store are loaded before tests."""
    slang_store.initialize_store()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP test client for the FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_sectors_company_report() -> Dict[str, Any]:
    """Mock payload for /v2/company/report/{symbol}/."""
    return {
        "symbol": "GOTO",
        "company_name": "GoTo Gojek Tokopedia Tbk",
        "overview": {
            "sector": "Technology",
            "sub_industry": "Internet & Direct Marketing",
            "market_cap": 82000000000000,
        },
        "valuation": {
            "pe_ratio": None,
            "pb_ratio": 2.4,
            "ps_ratio": 5.8,
        },
        "peers": {
            "median_pe": 18.5,
            "median_pb": 1.65,
        },
        "financials": {
            "revenue": 14500000000000,
            "net_income": -1200000000000,
        },
    }


@pytest.fixture
def mock_sectors_quarterly() -> List[Dict[str, Any]]:
    """Mock payload for /v2/financials/quarterly/{symbol}/."""
    return [
        {
            "period": "2024-Q3",
            "revenue": 3800000000000,
            "earnings": -320000000000,
            "earnings_growth_yoy": 12.4,
            "operating_cash_flow": -450000000000,
        },
        {
            "period": "2024-Q2",
            "revenue": 3600000000000,
            "earnings": -450000000000,
            "earnings_growth_yoy": 8.1,
            "operating_cash_flow": -520000000000,
        },
    ]


@pytest.fixture
def mock_sectors_top_brokers() -> Dict[str, Any]:
    """Mock payload for /v2/broker-summary/{symbol}/top/."""
    return {
        "symbol": "GOTO",
        "top_buyers": [
            {"broker_code": "YP", "net_value_idr": 15200000000.0, "lot": 250000},
            {"broker_code": "PD", "net_value_idr": 8400000000.0, "lot": 140000},
        ],
        "top_sellers": [
            {"broker_code": "AK", "net_value_idr": 24100000000.0, "lot": 400000},
            {"broker_code": "BK", "net_value_idr": 18700000000.0, "lot": 310000},
        ],
    }


@pytest.fixture
def mock_sectors_foreign_flow() -> Dict[str, Any]:
    """Mock payload for /v2/foreign-flow/{symbol}/."""
    return {
        "symbol": "GOTO",
        "data": [
            {
                "date": "2026-09-24",
                "net_foreign_inflow": -12500000000.0,
                "foreign_buy_value": 4500000000.0,
                "foreign_sell_value": 17000000000.0,
                "foreign_share": 0.32,
            }
        ],
    }


@pytest.fixture
def mock_sectors_suspensions_clean() -> Dict[str, Any]:
    """Mock payload for normal trading / non-FCA emiten."""
    return {
        "symbol": "GOTO",
        "results": [],
    }


@pytest.fixture
def mock_sectors_suspensions_fca() -> Dict[str, Any]:
    """Mock payload for stock under FCA / Special Monitoring Board."""
    return {
        "symbol": "GOTO",
        "results": [
            {
                "symbol": "GOTO",
                "reason": "Kriteria Papan Pemantauan Khusus (FCA) Tahap II",
                "suspension_date": "2026-08-01",
                "notation": "X",
            }
        ],
    }
