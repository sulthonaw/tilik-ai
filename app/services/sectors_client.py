"""Asynchronous Client for communicating with Sectors API v2."""

import logging
import time
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

    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0,
    ) -> httpx.Response:
        """Melakukan HTTP request dengan pencatatan log terstruktur dan pesan error yang rapi."""
        method_upper = method.upper()
        logger.info(
            f"[SectorsAPI] ==> Mengirim {method_upper} ke {url} | Params: {params or {}}"
        )
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(
                    method=method_upper,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json_data,
                )
                duration_ms = (time.perf_counter() - start_time) * 1000
                resp.raise_for_status()

                logger.info(
                    f"[SectorsAPI] <== Berhasil {method_upper} {url} | Status: {resp.status_code} ({duration_ms:.1f}ms)"
                )
                return resp

        except httpx.HTTPStatusError as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_detail = exc.response.text
            try:
                err_json = exc.response.json()
                error_detail = err_json.get("detail") or err_json.get("error") or str(err_json)
            except Exception:
                pass
            logger.error(
                f"[SectorsAPI] [X] HTTP Error {exc.response.status_code} pada {method_upper} {url} "
                f"({duration_ms:.1f}ms) | Pesan: {error_detail}"
            )
            raise

        except httpx.TimeoutException:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[SectorsAPI] [X] Timeout Error pada {method_upper} {url} "
                f"({duration_ms:.1f}ms) | Permintaan melebihi batas waktu ({timeout}s)"
            )
            raise

        except httpx.RequestError as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[SectorsAPI] [X] Network Error pada {method_upper} {url} "
                f"({duration_ms:.1f}ms) | Penyebab: {type(exc).__name__}: {str(exc)}"
            )
            raise

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[SectorsAPI] [X] Unexpected Error pada {method_upper} {url} "
                f"({duration_ms:.1f}ms) | Detail: {type(exc).__name__}: {str(exc)}"
            )
            raise

    async def get(
        self,
        endpoint_or_url: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """Melakukan generic GET request ke Sectors API."""
        url = (
            endpoint_or_url
            if endpoint_or_url.startswith("http")
            else f"{self.base_url}/{endpoint_or_url.lstrip('/')}"
        )
        resp = await self._request("GET", url, params=params, timeout=timeout)
        return resp.json()

    async def post(
        self,
        endpoint_or_url: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """Melakukan generic POST request ke Sectors API."""
        url = (
            endpoint_or_url
            if endpoint_or_url.startswith("http")
            else f"{self.base_url}/{endpoint_or_url.lstrip('/')}"
        )
        resp = await self._request("POST", url, params=params, json_data=data, timeout=timeout)
        return resp.json()

    async def get_company_report(
        self, symbol: str, sections: str = "overview,valuation,financials,peers"
    ) -> Dict[str, Any]:
        """Mengambil laporan ringkas emiten dengan optimasi 4 credits."""
        url = f"{self.base_url}/v2/company/report/{symbol.upper()}/"
        resp = await self._request("GET", url, params={"sections": sections})
        return resp.json()

    async def get_quarterly_financials(
        self, symbol: str, n_quarters: int = 4
    ) -> List[Dict[str, Any]]:
        """Mengambil laporan keuangan kuartalan (biaya 1 credit)."""
        url = f"{self.base_url}/v2/financials/quarterly/{symbol.upper()}/"
        resp = await self._request(
            "GET", url, params={"n_quarters": n_quarters, "approx": "true"}
        )
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
        resp = await self._request("GET", url, params=params)
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
        resp = await self._request("GET", url, params=params)
        return resp.json()

    async def get_suspensions(self, symbol: str) -> Dict[str, Any]:
        """Mengecek apakah saham sedang disuspensi / notasi khusus oleh BEI."""
        url = f"{self.base_url}/v2/suspensions/"
        resp = await self._request(
            "GET", url, params={"symbol": symbol.upper(), "limit": 5}
        )
        return resp.json()

    async def get_filings(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """Mengambil keterbukaan informasi dan aksi insider trading emiten."""
        url = f"{self.base_url}/v2/filings/"
        resp = await self._request(
            "GET", url, params={"symbol": symbol.upper(), "limit": limit}
        )
        return resp.json()
