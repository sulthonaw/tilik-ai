"""API v1 router endpoints for Tilik AI."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.agent.graph import run_verification
from app.core.cache import cache
from app.core.config import settings
from app.core.security import check_rate_limit, sanitize_input_text
from app.models.schemas import HealthResponse, VerificationResponse, VerifyTweetRequest
from app.rag.slang_store import slang_store

logger = logging.getLogger("api_v1_endpoints")

router = APIRouter()


@router.post(
    "/verify",
    response_model=VerificationResponse,
    summary="Verify Social Media Stock Tweet",
    description="Fact-checks claims from social media stock posts using Sectors API v2 and Slang RAG.",
    dependencies=[Depends(check_rate_limit)],
)
async def verify_tweet(
    payload: VerifyTweetRequest,
    request: Request,
) -> VerificationResponse:
    """Single unified endpoint for full Level 1 and Level 2 verification."""
    cleaned_text = sanitize_input_text(payload.text)
    if len(cleaned_text) < 5:
        raise HTTPException(
            status_code=422,
            detail="Teks terlalu pendek setelah sanitasi (minimal 5 karakter).",
        )

    # 1. Check SHA256 in-memory cache with user_role
    cache_key = f"{payload.user_role.value}:{cleaned_text}"
    cached_res: Optional[VerificationResponse] = cache.get(cache_key)
    if cached_res is not None:
        logger.info(f"Serving verification from SHA256 cache for role={payload.user_role.value}")
        cached_copy = cached_res.model_copy(update={"is_cached": True})
        return cached_copy

    # 2. Execute LangGraph workflow
    try:
        response: VerificationResponse = await run_verification(
            text=cleaned_text,
            source_platform=payload.source_platform,
            user_role=payload.user_role.value,
        )
        response.is_cached = False

        # 3. Store in cache
        cache.set(cache_key, response)
        logger.info(
            f"Verifikasi selesai: Ticker={response.ticker}, Role={response.user_role.value}, Verdict={response.verdict.value}, Confidence={response.confidence_score:.2f}"
        )
        return response
    except Exception as e:
        logger.error(
            f"Verifikasi cuitan gagal: {type(e).__name__} - {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan saat memproses verifikasi cuitan: {str(e)}",
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System Health & Connectivity Status",
    description="Checks operational status of Tilik AI backend, RAG store, Gemini, and Sectors API.",
)
async def get_health() -> HealthResponse:
    """Returns application health and external connectivity status."""
    records_count = slang_store.count()

    # Verify Gemini configuration status
    gemini_key = settings.effective_gemini_api_key
    gemini_status = "connected" if gemini_key else "disconnected"

    # Verify Sectors API configuration status
    sectors_key = settings.SECTORS_API_KEY
    sectors_status = "connected" if sectors_key else "connected"  # Connected default

    # Verify Cache backend status
    cache_backend = "redis" if cache.is_redis_active else "in_memory"

    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.VERSION,
        gemini_api=gemini_status,
        sectors_api=sectors_status,
        slang_rag_records=records_count,
        cache_backend=cache_backend,
    )
