"""FastAPI Application Factory for Tilik AI Backend."""

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Tilik AI — In-Context Financial Fact-Checker & Slang RAG Engine for IDX Stocks",
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
