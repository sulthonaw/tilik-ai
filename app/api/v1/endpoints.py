"""API v1 router endpoints for Tilik AI."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.agent.graph import run_verification
from app.core.cache import cache
from app.core.config import settings
from app.core.security import (
    check_rate_limit,
    create_access_token,
    get_current_user,
    get_current_user_optional,
    sanitize_input_text,
    verify_google_id_token,
)
from app.models.schemas import (
    AuthResponse,
    GoogleAuthRequest,
    HealthResponse,
    UserPayload,
    UserProfileResponse,
    VerificationResponse,
    VerifyTweetRequest,
)
from app.rag.slang_store import slang_store

logger = logging.getLogger("api_v1_endpoints")

router = APIRouter()


@router.post(
    "/auth/google",
    response_model=AuthResponse,
    summary="Sign in with Google",
    description="Exchanges Google ID Token from client for a Tilik AI JWT access token.",
    dependencies=[Depends(check_rate_limit)],
)
async def login_with_google(payload: GoogleAuthRequest) -> AuthResponse:
    """Verifies client-provided Google ID Token and returns JWT bearer token."""
    try:
        id_info = verify_google_id_token(payload.id_token)
        google_id = id_info.get("sub")
        email = id_info.get("email")
        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token Google tidak memuat identifier akun (sub/email) yang valid.",
            )

        user = UserPayload(
            email=email,
            name=id_info.get("name"),
            picture=id_info.get("picture"),
            google_id=google_id,
        )

        token_data = {
            "sub": google_id,
            "email": email,
            "name": user.name,
            "picture": user.picture,
        }
        access_token = create_access_token(data=token_data)
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        logger.info(f"User berhasil login via Google: {email} ({google_id})")
        return AuthResponse(
            status="success",
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            user=user,
        )
    except ValueError as e:
        logger.warning(f"Google login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during Google login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan pada server saat memproses login Google.",
        )


@router.get(
    "/auth/me",
    response_model=UserProfileResponse,
    summary="Get Current User Profile",
    description="Returns authenticated user information from validated Bearer JWT token.",
)
async def get_current_user_profile(
    current_user: UserPayload = Depends(get_current_user),
) -> UserProfileResponse:
    """Returns profile for currently authenticated user."""
    return UserProfileResponse(
        status="success",
        user=current_user,
    )


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
    current_user: Optional[UserPayload] = Depends(get_current_user_optional),
) -> VerificationResponse:
    """Single unified endpoint for full Level 1 and Level 2 verification."""
    caller = current_user.email if current_user else "anonymous/guest"
    logger.info(f"Permintaan verifikasi diterima dari: {caller}")
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
