"""FastAPI Application Factory for Tilik AI Backend."""

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.endpoints import get_health, router as api_v1_router
from app.core.config import settings
from app.models.schemas import HealthResponse
from app.rag.slang_store import slang_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tilik-ai")

# Suppress internal Google SDK function calling advisory logs
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google_genai.models").setLevel(logging.ERROR)


OPENAPI_TAGS = [
    {
        "name": "Verification",
        "description": "Endpoint utama verifikasi fakta cuitan saham menggunakan data resmi Sectors API v2 dan RAG Slang bursa.",
    },
    {
        "name": "History",
        "description": "Pengelolaan dan inspeksi mendalam (click-to-detail) riwayat verifikasi Level 1 dan Level 2.",
    },
    {
        "name": "Authentication",
        "description": "Autentikasi Google Sign-In dan penerbitan token JWT Bearer.",
    },
    {
        "name": "User Settings",
        "description": "Pengaturan preferensi profil pengguna (mode PEMULA atau EXPERT).",
    },
    {
        "name": "Health",
        "description": "Pemeriksaan kesehatan sistem, konektivitas Sectors API, Gemini LLM, RAG store, dan Cache.",
    },
    {
        "name": "Root",
        "description": "Informasi dasar service gateway dan shortcut endpoint.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for startup and shutdown actions."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION} [{settings.APP_ENV}]")

    # Ingest slang dictionary and warm up RAG vector store
    try:
        slang_store.initialize_store()
        logger.info(f"Slang RAG initialized with {slang_store.count()} records")
    except Exception as e:
        logger.error(f"Failed to initialize slang RAG store: {e}")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}")


API_DESCRIPTION = """
### 🔍 Tilik AI — In-Context Financial Fact-Checker & Slang RAG Engine for IDX Stocks

Tilik AI adalah layanan backend cerdas yang memvalidasi narasi dan klaim saham di media sosial (X, Threads, Telegram)
secara instan (< 1,5 detik) menggunakan data bursa resmi dari **Sectors API v2** dan basis pengetahuan **Slang RAG**.

#### 🛡️ Prinsip Regulasi & Invarian Sistem:
- **Kepatuhan OJK (POJK No. 6/2026 & UU P2SK):** Murni berposisi sebagai *Factual Information Provider* dengan menyandingkan *Klaim Medsos vs Data Resmi IDX* serta klausul *Disclaimer On*. Dilarang memberikan rekomendasi personal, sinyal transaksi (beli/jual), atau target price.
- **Tanpa Eksekusi Perdagangan Otomatis:** Sistem bersifat analitis, edukatif, dan fact-checking (*no automated trade execution*).
- **Dual-Level Output Payload:**
  - **Level 1 (Summary Card):** Status lampu lalu lintas (🔴 HOAX / BAHAYA, 🟡 WASPADA, 🟢 SESUAI FAKTA), 1–3 poin fakta kunci (maks 25 kata/poin), dan catatan refleksi kontekstual (*cooling-off prompt* untuk pemula atau *Devil's Advocate* untuk expert).
  - **Level 2 (Expanded Data - Zero Latency):** Rincian angka fundamental mendalam (valuasi vs median sektor, broker flow institusi vs ritel, pertumbuhan laba & OCF, status suspensi/FCA) langsung ter-bundle tanpa pemanggilan AI tambahan.
"""

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description=API_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# STANDARDIZED EXCEPTION HANDLERS
# ==========================================
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Menyeragamkan respons HTTPException menjadi format JSON terstruktur yang konsisten."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Menangani error validasi skema input (422) dengan pesan ringkas ramah pengguna."""
    errors = exc.errors()
    err_descriptions = []
    for err in errors:
        loc = ".".join(str(item) for item in err.get("loc", []) if item != "body")
        msg = err.get("msg", "Nilai tidak valid")
        err_descriptions.append(f"{loc}: {msg}" if loc else msg)

    friendly_msg = "; ".join(err_descriptions) if err_descriptions else "Format data permintaan tidak valid."
    return JSONResponse(
        status_code=422,
        content={
            "detail": errors,
            "message": f"Validasi input gagal: {friendly_msg}",
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Menangani exception yang tidak tertangkap agar tidak menyebabkan server crash atau return HTML mentah."""
    logger.error(
        f"[Unhandled Exception] {request.method} {request.url.path} - {type(exc).__name__}: {str(exc)}"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Terjadi kesalahan internal pada server. Silakan coba beberapa saat lagi.",
            "error_type": type(exc).__name__,
        },
    )



@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """Mencatat log setiap request GET/POST yang masuk, durasi, status hasil, dan error secara rapi."""
    start_time = time.perf_counter()
    method = request.method
    path = request.url.path
    client_ip = request.client.host if request.client else "unknown"

    logger.info(f"==> [HTTP] {method} {path} diterima dari {client_ip}")

    try:
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"<== [HTTP] {method} {path} selesai | Status: {response.status_code} ({duration_ms:.1f}ms)"
        )
        return response
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            f"[X] [HTTP] {method} {path} gagal ({duration_ms:.1f}ms) | Error: {type(exc).__name__}: {str(exc)}"
        )
        raise


# Mount API v1 endpoints
app.include_router(api_v1_router, prefix="/api/v1")


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Root Health Check",
    description="Convenience shortcut to the system health check.",
)
async def root_health() -> HealthResponse:
    """Convenience alias for /api/v1/health."""
    return await get_health()


@app.get(
    "/",
    tags=["Root"],
    summary="Root Info",
    description="Returns basic application info.",
)
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
        "verify_endpoint": "/api/v1/verify",
    }
