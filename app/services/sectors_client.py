"""Asynchronous Client for communicating with Sectors API v2."""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("sectors_client")


class SectorsAPIClient:
    """Asynchronous Client untuk komunikasi dengan Sectors API v2."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.SECTORS_API_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.SECTORS_API_KEY or ""
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

    async def get_company_report(
        self, symbol: str, sections: str = "overview,valuation,financials,peers"
    ) -> Dict[str, Any]:
        """Mengambil laporan ringkas emiten dengan optimasi 4 credits."""
        url = f"{self.base_url}/v2/company/report/{symbol.upper()}/"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self.headers, params={"sections": sections})
            resp.raise_for_status()
            return resp.json()

    async def get_quarterly_financials(
        self, symbol: str, n_quarters: int = 4
    ) -> List[Dict[str, Any]]:
        """Mengambil laporan keuangan kuartalan (biaya 1 credit)."""
        url = f"{self.base_url}/v2/financials/quarterly/{symbol.upper()}/"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url, headers=self.headers, params={"n_quarters": n_quarters, "approx": "true"}
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            return []

    async def get_top_brokers(
        self,
        symbol: str,
        n_brokers: int = 10,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mengambil ringkasan Top Buyers dan Top Sellers broker (biaya 1 credit)."""
        url = f"{self.base_url}/v2/broker-summary/{symbol.upper()}/top/"
        params: Dict[str, Any] = {"n_brokers": n_brokers}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_foreign_flow(
        self,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mengambil arus dana investor asing harian (biaya 1 credit)."""
        url = f"{self.base_url}/v2/foreign-flow/{symbol.upper()}/"
        params: Dict[str, Any] = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_suspensions(self, symbol: str) -> Dict[str, Any]:
        """Mengecek apakah saham sedang disuspensi / notasi khusus oleh BEI."""
        url = f"{self.base_url}/v2/suspensions/"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url, headers=self.headers, params={"symbol": symbol.upper(), "limit": 5}
            )
            resp.raise_for_status()
            return resp.json()

    async def get_filings(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """Mengambil keterbukaan informasi dan aksi insider trading emiten."""
        url = f"{self.base_url}/v2/filings/"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url, headers=self.headers, params={"symbol": symbol.upper(), "limit": limit}
            )
            resp.raise_for_status()
            return resp.json()
