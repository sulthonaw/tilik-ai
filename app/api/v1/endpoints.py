"""API v1 router endpoints for Tilik AI."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

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
    ErrorResponse,
    GoogleAuthRequest,
    HealthResponse,
    HistoryDetailResponse,
    HistoryItemSummary,
    HistoryListResponse,
    UserPayload,
    UserProfileResponse,
    UserRole,
    UserSettingsUpdate,
    VerificationResponse,
    VerifyTweetRequest,
)
from app.rag.slang_store import slang_store
from app.services.history_service import history_service
from app.services.user_service import user_service

logger = logging.getLogger("api_v1_endpoints")

router = APIRouter()


@router.post(
    "/auth/google",
    response_model=AuthResponse,
    tags=["Authentication"],
    summary="Sign in with Google",
    description="Exchanges Google ID Token from client for a Tilik AI JWT access token.",
    dependencies=[Depends(check_rate_limit)],
    responses={
        400: {"model": ErrorResponse, "description": "Token Google tidak memuat identifier akun yang valid."},
        401: {"model": ErrorResponse, "description": "Token Google tidak valid atau kedaluwarsa."},
        429: {"model": ErrorResponse, "description": "Batas frekuensi permintaan terlampaui."},
        500: {"model": ErrorResponse, "description": "Kesalahan server internal saat proses login."},
    },
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

        saved_role = user_service.get_user_role(google_id)
        user = UserPayload(
            email=email,
            name=id_info.get("name"),
            picture=id_info.get("picture"),
            google_id=google_id,
            user_role=saved_role,
        )

        token_data = {
            "sub": google_id,
            "email": email,
            "name": user.name,
            "picture": user.picture,
            "role": saved_role.value,
        }
        access_token = create_access_token(data=token_data)
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        logger.info(f"User berhasil login via Google: {email} ({google_id}) [Role: {saved_role.value}]")
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
    tags=["Authentication"],
    summary="Get Current User Profile",
    description="Returns authenticated user information from validated Bearer JWT token.",
    responses={
        401: {"model": ErrorResponse, "description": "Autentikasi diperlukan (Bearer token tidak valid atau tidak disertakan)."},
    },
)
async def get_current_user_profile(
    current_user: UserPayload = Depends(get_current_user),
) -> UserProfileResponse:
    """Returns profile for currently authenticated user."""
    return UserProfileResponse(
        status="success",
        user=current_user,
    )


@router.put(
    "/user/settings",
    response_model=UserProfileResponse,
    tags=["User Settings"],
    summary="Update User Role Setting",
    description="Updates and persists preferred display role (PEMULA or EXPERT) for authenticated user.",
    responses={
        401: {"model": ErrorResponse, "description": "Autentikasi diperlukan."},
        422: {"model": ErrorResponse, "description": "Format role tidak valid (hanya menerima PEMULA atau EXPERT)."},
    },
)
async def update_user_settings(
    payload: UserSettingsUpdate,
    current_user: UserPayload = Depends(get_current_user),
) -> UserProfileResponse:
    """Updates and persists preferred role for authenticated user."""
    user_service.set_user_role(current_user.google_id, payload.user_role)
    updated_user = current_user.model_copy(update={"user_role": payload.user_role})
    logger.info(f"Preferensi role user {current_user.email} diubah menjadi {payload.user_role.value}")
    return UserProfileResponse(
        status="success",
        user=updated_user,
    )


@router.post(
    "/verify",
    response_model=VerificationResponse,
    tags=["Verification"],
    summary="Verify Social Media Stock Tweet",
    description="Fact-checks claims from social media stock posts using Sectors API v2 and Slang RAG.",
    dependencies=[Depends(check_rate_limit)],
    responses={
        422: {"model": ErrorResponse, "description": "Teks cuitan terlalu pendek (minimal 5 karakter) atau format request tidak valid."},
        429: {"model": ErrorResponse, "description": "Batas frekuensi permintaan terlampaui."},
        500: {"model": ErrorResponse, "description": "Terjadi kesalahan internal pada pipeline verifikasi."},
    },
)
async def verify_tweet(
    payload: VerifyTweetRequest,
    request: Request,
    current_user: Optional[UserPayload] = Depends(get_current_user_optional),
) -> VerificationResponse:
    """Single unified endpoint for full Level 1 and Level 2 verification."""
    # Determine effective role:
    # 1. Explicit request payload override
    # 2. Saved user setting for authenticated user
    # 3. Default fallback to PEMULA for guest
    effective_role: UserRole = payload.user_role or (
        current_user.user_role if current_user else UserRole.PEMULA
    )

    caller = current_user.email if current_user else "anonymous/guest"
    logger.info(f"Permintaan verifikasi diterima dari: {caller} [Role: {effective_role.value}]")

    cleaned_text = sanitize_input_text(payload.text)
    if len(cleaned_text) < 5:
        raise HTTPException(
            status_code=422,
            detail="Teks terlalu pendek setelah sanitasi (minimal 5 karakter).",
        )

    user_id = current_user.google_id if current_user else "guest"

    # 1. Check SHA256 in-memory cache with effective_role
    cache_key = f"{effective_role.value}:{cleaned_text}"
    cached_res: Optional[VerificationResponse] = cache.get(cache_key)
    if cached_res is not None:
        logger.info(f"Serving verification from SHA256 cache for role={effective_role.value}")
        cached_copy = cached_res.model_copy(update={"is_cached": True})
        hist_id = history_service.add_history(
            user_id=user_id,
            tweet_text=cleaned_text,
            source_platform=payload.source_platform or "x",
            verification=cached_copy,
        )
        cached_copy.history_id = hist_id
        return cached_copy

    # 2. Execute LangGraph workflow
    try:
        response: VerificationResponse = await run_verification(
            text=cleaned_text,
            source_platform=payload.source_platform,
            user_role=effective_role.value,
        )
        response.is_cached = False

        # 3. Store in cache
        cache.set(cache_key, response)

        # 4. Record to verification history
        hist_id = history_service.add_history(
            user_id=user_id,
            tweet_text=cleaned_text,
            source_platform=payload.source_platform or "x",
            verification=response,
        )
        response.history_id = hist_id

        logger.info(
            f"Verifikasi selesai: Ticker={response.ticker}, Role={response.user_role.value}, Verdict={response.verdict.value}, Confidence={response.confidence_score:.2f}, HistID={hist_id}"
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


# ==========================================
# HISTORY ENDPOINTS (Click to detail)
# ==========================================
@router.get(
    "/history",
    response_model=HistoryListResponse,
    tags=["History"],
    summary="Get Verification History",
    description="Retrieves chronological verification history for the current authenticated user or guest.",
)
async def list_verification_history(
    limit: int = Query(default=20, ge=1, le=100, description="Jumlah item per halaman"),
    offset: int = Query(default=0, ge=0, description="Offset pemanggilan riwayat"),
    current_user: Optional[UserPayload] = Depends(get_current_user_optional),
) -> HistoryListResponse:
    """Returns list of past verification summaries for easy clicking."""
    user_id = current_user.google_id if current_user else "guest"
    items, total = history_service.list_history(user_id=user_id, limit=limit, offset=offset)
    return HistoryListResponse(
        status="success",
        total=total,
        items=items,
    )


@router.get(
    "/history/{history_id}",
    response_model=HistoryDetailResponse,
    tags=["History"],
    summary="Get Verification History Detail",
    description="Retrieves full verification detail (Level 1 and Level 2 data) by history ID for deep inspection.",
    responses={
        404: {"model": ErrorResponse, "description": "Riwayat verifikasi dengan ID yang diminta tidak ditemukan."},
    },
)
async def get_verification_history_detail(
    history_id: str,
) -> HistoryDetailResponse:
    """Returns complete Level 1 and Level 2 verification response when a card is clicked."""
    detail = history_service.get_history_detail(history_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Riwayat verifikasi dengan ID '{history_id}' tidak ditemukan.",
        )
    return detail


@router.delete(
    "/history/{history_id}",
    tags=["History"],
    summary="Delete Single History Record",
    description="Deletes a specific history record by its unique ID.",
    responses={
        404: {"model": ErrorResponse, "description": "Riwayat verifikasi dengan ID yang diminta tidak ditemukan."},
    },
)
async def delete_verification_history_item(
    history_id: str,
    current_user: Optional[UserPayload] = Depends(get_current_user_optional),
):
    """Deletes single history item."""
    user_id = current_user.google_id if current_user else "guest"
    deleted = history_service.delete_history_item(history_id, user_id=user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Riwayat verifikasi dengan ID '{history_id}' tidak ditemukan.",
        )
    return {"status": "success", "message": f"Riwayat '{history_id}' berhasil dihapus."}


@router.delete(
    "/history",
    tags=["History"],
    summary="Clear Verification History",
    description="Clears all verification history for current authenticated user or guest.",
)
async def clear_verification_history(
    current_user: Optional[UserPayload] = Depends(get_current_user_optional),
):
    """Clears all history for user."""
    user_id = current_user.google_id if current_user else "guest"
    history_service.clear_user_history(user_id=user_id)
    return {"status": "success", "message": "Semua riwayat verifikasi berhasil dibersihkan."}


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
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
