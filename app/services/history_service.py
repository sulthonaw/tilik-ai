"""Verification history management service with persistence and caching."""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import threading
import time
from typing import Dict, List, Optional, Tuple
import uuid

from app.core.cache import cache
from app.core.config import ROOT_DIR, settings
from app.models.schemas import (
    HistoryDetailResponse,
    HistoryItemSummary,
    UserRole,
    VerdictLevel,
    VerificationResponse,
)

logger = logging.getLogger("history_service")

HISTORY_DIR = ROOT_DIR / "data" / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


class HistoryService:
    """Manages fact-check history records for both logged in users and guests."""

    def __init__(self):
        self._lock = threading.Lock()
        self._in_memory_records: Dict[str, Dict] = {}  # {history_id: dict_data}
        self._load_all_records()

    def _get_user_file(self, user_id: str) -> Path:
        # Sanitize user_id for filesystem
        safe_name = "".join(c for c in user_id if c.isalnum() or c in ("-", "_")) or "guest"
        return HISTORY_DIR / f"{safe_name}.json"

    def _load_all_records(self) -> None:
        """Loads all existing history files into memory cache on startup."""
        try:
            for file_path in HISTORY_DIR.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        items = json.load(f)
                        if isinstance(items, list):
                            for item in items:
                                if isinstance(item, dict) and "id" in item:
                                    self._in_memory_records[item["id"]] = item
                except Exception as e:
                    logger.warning(f"Failed to read history file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error accessing history directory: {e}")

    def add_history(
        self,
        user_id: str,
        tweet_text: str,
        source_platform: Optional[str],
        verification: VerificationResponse,
    ) -> str:
        """Stores a new verification entry and returns the generated history_id."""
        now_iso = datetime.now(timezone.utc).isoformat()
        ms_ts = int(time.time() * 1000)
        history_id = f"hist_{ms_ts}_{uuid.uuid4().hex[:6]}"

        preview = tweet_text[:100] + ("..." if len(tweet_text) > 100 else "")

        summary_dict = {
            "id": history_id,
            "created_at": now_iso,
            "ticker": verification.ticker,
            "company_name": verification.company_name,
            "user_role": verification.user_role.value,
            "verdict": verification.verdict.value,
            "confidence_score": verification.confidence_score,
            "tweet_preview": preview,
            "source_platform": source_platform or "x",
        }

        full_record = {
            "id": history_id,
            "user_id": user_id,
            "created_at": now_iso,
            "tweet_text": tweet_text,
            "source_platform": source_platform or "x",
            "summary": summary_dict,
            "verification": verification.model_dump(),
        }

        with self._lock:
            # 1. Update in-memory registry
            self._in_memory_records[history_id] = full_record

            # 2. Append/save to user file
            user_file = self._get_user_file(user_id)
            user_items = []
            if user_file.exists():
                try:
                    with open(user_file, "r", encoding="utf-8") as f:
                        user_items = json.load(f)
                except Exception:
                    user_items = []

            user_items.insert(0, full_record)
            # Limit history to 200 items per user
            user_items = user_items[:200]

            try:
                with open(user_file, "w", encoding="utf-8") as f:
                    json.dump(user_items, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Failed to persist history file {user_file}: {e}")

        logger.info(f"History recorded: id={history_id}, user={user_id}, ticker={verification.ticker}")
        return history_id

    def list_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[HistoryItemSummary], int]:
        """Lists summaries of verification history for given user_id."""
        with self._lock:
            user_file = self._get_user_file(user_id)
            user_items = []
            if user_file.exists():
                try:
                    with open(user_file, "r", encoding="utf-8") as f:
                        user_items = json.load(f)
                except Exception:
                    user_items = []

            # If user_items is empty in file, check memory
            if not user_items:
                user_items = [
                    rec for rec in self._in_memory_records.values()
                    if rec.get("user_id") == user_id
                ]
                user_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            total = len(user_items)
            paged = user_items[offset : offset + limit]

            summaries: List[HistoryItemSummary] = []
            for item in paged:
                s = item.get("summary") or item
                summaries.append(HistoryItemSummary(
                    id=s["id"],
                    created_at=s["created_at"],
                    ticker=s.get("ticker"),
                    company_name=s.get("company_name"),
                    user_role=UserRole(s.get("user_role", UserRole.PEMULA.value)),
                    verdict=VerdictLevel(s.get("verdict", VerdictLevel.WASPADA.value)),
                    confidence_score=float(s.get("confidence_score", 0.90)),
                    tweet_preview=s.get("tweet_preview", ""),
                    source_platform=s.get("source_platform", "x"),
                ))

            return summaries, total

    def get_history_detail(self, history_id: str) -> Optional[HistoryDetailResponse]:
        """Retrieves full Level 1 & Level 2 verification response by history_id."""
        with self._lock:
            record = self._in_memory_records.get(history_id)
            if not record:
                # Attempt to search files
                for file_path in HISTORY_DIR.glob("*.json"):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            items = json.load(f)
                            for item in items:
                                if item.get("id") == history_id:
                                    record = item
                                    self._in_memory_records[history_id] = record
                                    break
                    except Exception:
                        pass
                    if record:
                        break

            if not record:
                return None

            try:
                verification = VerificationResponse(**record["verification"])
                return HistoryDetailResponse(
                    status="success",
                    id=record["id"],
                    created_at=record["created_at"],
                    tweet_text=record.get("tweet_text", ""),
                    source_platform=record.get("source_platform", "x"),
                    verification=verification,
                )
            except Exception as e:
                logger.error(f"Failed to reconstruct VerificationResponse for {history_id}: {e}")
                return None

    def delete_history_item(self, history_id: str, user_id: str) -> bool:
        """Deletes a single history record."""
        with self._lock:
            found = False
            if history_id in self._in_memory_records:
                del self._in_memory_records[history_id]
                found = True

            user_file = self._get_user_file(user_id)
            if user_file.exists():
                try:
                    with open(user_file, "r", encoding="utf-8") as f:
                        items = json.load(f)
                    filtered = [it for it in items if it.get("id") != history_id]
                    if len(filtered) < len(items):
                        found = True
                        with open(user_file, "w", encoding="utf-8") as f:
                            json.dump(filtered, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.error(f"Failed to update file during history deletion: {e}")

            return found

    def clear_user_history(self, user_id: str) -> None:
        """Clears all history records for specified user."""
        with self._lock:
            to_del = [
                hid for hid, rec in self._in_memory_records.items()
                if rec.get("user_id") == user_id
            ]
            for hid in to_del:
                del self._in_memory_records[hid]

            user_file = self._get_user_file(user_id)
            if user_file.exists():
                try:
                    user_file.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete history file {user_file}: {e}")


history_service = HistoryService()
