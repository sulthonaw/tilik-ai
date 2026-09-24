"""Pydantic v2 data contracts and response schemas for Tilik AI."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class VerdictLevel(str, Enum):
    """Traffic light verdict status."""
    RED = "RED"          # Klaim palsu / Hype manipulatif / Valuasi ekstrem / Papan FCA
    YELLOW = "YELLOW"    # Fakta separuh / Ada risiko tersembunyi
    GREEN = "GREEN"      # Klaim terkonfirmasi data fundamental riil


# LEVEL 1: Summary Facts (Maksimal 25 kata / 150 karakter per poin)
class FactCheckPoint(BaseModel):
    title: str = Field(..., description="Parameter fakta, misal: 'Valuasi PER'")
    fact: str = Field(..., max_length=150, description="Uraian komparasi data, maks 25 kata")
    is_favorable: bool = Field(..., description="True jika mendukung fundamental sehat")


# LEVEL 2: Expanded Data (Untuk tombol 'Lihat Data Lengkap' - Zero Latency)
class ValuationPeerDetail(BaseModel):
    pe_ratio: Optional[float] = Field(None, description="Price to Earnings Ratio emiten")
    pbv_ratio: Optional[float] = Field(None, description="Price to Book Value Ratio emiten")
    industry_median_pe: Optional[float] = Field(None, description="Median PE industri sejenis")
    industry_median_pbv: Optional[float] = Field(None, description="Median PBV industri sejenis")
    valuation_status: str = Field(..., json_schema_extra={"example": "45% Lebih Mahal dari Sektor"})


class BrokerDetail(BaseModel):
    broker_code: str = Field(..., json_schema_extra={"example": "YP"})
    broker_type: str = Field(..., json_schema_extra={"example": "Ritel Domestik | Asing"})
    net_value_idr: float = Field(..., description="Nilai transaksi bersih dalam Rupiah")
    action: str = Field(..., json_schema_extra={"example": "NET_BUY | NET_SELL"})


class BrokerFlowDetail(BaseModel):
    foreign_net_idr: float = Field(..., description="Total akumulasi bersih asing hari ini")
    top_buyers: List[BrokerDetail] = Field(default_factory=list)
    top_sellers: List[BrokerDetail] = Field(default_factory=list)
    summary_verdict: str = Field(..., json_schema_extra={"example": "Asing net sell Rp 12M, pembeli didominasi ritel"})


class FinancialHealthDetail(BaseModel):
    net_profit_growth_yoy: Optional[float] = Field(None, description="Pertumbuhan laba bersih YoY (%)")
    operating_cash_flow_idr: Optional[float] = Field(None, description="Arus kas operasional")
    is_fca: bool = Field(..., description="True jika masuk Papan Pemantauan Khusus")
    special_notations: List[str] = Field(default_factory=list, description="Daftar tato bursa, misal: ['X']")


class ExpandedDetails(BaseModel):
    valuation: ValuationPeerDetail
    broker_flow: BrokerFlowDetail
    financial_health: FinancialHealthDetail


# REQUEST & RESPONSE UNIFIED
class VerifyTweetRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        json_schema_extra={"example": "Si ijo mulai diserok bandar YP, valuasi salah harga to the moon!"},
    )
    source_platform: Optional[str] = Field("x", json_schema_extra={"example": "x | threads | telegram"})


class VerificationResponse(BaseModel):
    status: str = Field("success", json_schema_extra={"example": "success"})
    ticker: Optional[str] = Field(None, json_schema_extra={"example": "GOTO"})
    company_name: Optional[str] = Field(None, json_schema_extra={"example": "GoTo Gojek Tokopedia Tbk"})

    # --- LEVEL 1: SUMMARY CARD ---
    verdict: VerdictLevel = Field(..., description="Status lampu lalu lintas")
    confidence_score: float = Field(..., ge=0.0, le=1.0, json_schema_extra={"example": 0.94})
    points: List[FactCheckPoint] = Field(..., min_length=1, max_length=3)
    cooling_off_prompt: str = Field(
        ..., json_schema_extra={"example": "Tarik napas 5 detik! Yakin membeli karena analisa atau takut tertinggal harga?"}
    )

    # --- LEVEL 2: EXPANDED DATA (Zero-Latency Tab) ---
    details: ExpandedDetails

    is_cached: bool = Field(False)


class HealthResponse(BaseModel):
    status: str = Field("healthy", json_schema_extra={"example": "healthy"})
    app_name: str = Field("Tilik AI Backend", json_schema_extra={"example": "Tilik AI Backend"})
    version: str = Field("2.0.0", json_schema_extra={"example": "2.0.0"})
    gemini_api: str = Field("connected", json_schema_extra={"example": "connected"})
    sectors_api: str = Field("connected", json_schema_extra={"example": "connected"})
    slang_rag_records: int = Field(0, json_schema_extra={"example": 52})
