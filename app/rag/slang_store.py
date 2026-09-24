"""Vector store manager and dictionary indexer for slang terms."""

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger("slang_store")


class SlangStore:
    """Manages slang dictionary loading, indexing, and ChromaDB vector store."""

    def __init__(self, csv_path: Optional[str] = None, persist_dir: Optional[str] = None):
        self.csv_path = Path(csv_path or settings.SLANG_CSV_PATH)
        self.persist_dir = Path(persist_dir or settings.CHROMA_PERSIST_DIR)
        self.records: List[Dict[str, Any]] = []
        self.chroma_client = None
        self.collection = None
        self._is_initialized = False

    def load_data(self) -> List[Dict[str, Any]]:
        """Loads records from CSV file."""
        if not self.csv_path.exists():
            # Fallback check in current working directory
            alt_path = Path("data/slang_dictionary.csv")
            if alt_path.exists():
                self.csv_path = alt_path
            else:
                alt_path2 = Path("slang_dictionary.csv")
                if alt_path2.exists():
                    self.csv_path = alt_path2

        if not self.csv_path.exists():
            logger.warning(f"Slang CSV not found at {self.csv_path}")
            return []

        loaded: List[Dict[str, Any]] = []
        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                slang_term = (row.get("slang_term") or "").strip()
                if not slang_term:
                    continue
                record = {
                    "slang_term": slang_term.lower(),
                    "formal_ticker": (row.get("formal_ticker") or "").strip().upper() or None,
                    "category": (row.get("category") or "").strip().upper(),
                    "meaning": (row.get("meaning") or "").strip(),
                    "sentiment_bias": (row.get("sentiment_bias") or "").strip().upper(),
                    "context_examples": (row.get("context_examples") or "").strip(),
                }
                loaded.append(record)

        self.records = loaded
        logger.info(f"Loaded {len(self.records)} slang records from {self.csv_path}")
        return self.records

    def initialize_store(self) -> None:
        """Initializes ChromaDB vector store and populates it with slang entries."""
        if self._is_initialized and self.collection is not None:
            return

        if not self.records:
            self.load_data()

        if not self.records:
            logger.warning("No records to index into vector store.")
            return

        try:
            import chromadb
            # In-memory ephemeral client is fast and avoids filesystem lock issues in tests
            self.chroma_client = chromadb.Client()
            collection_name = "idx_slang_collection"

            # Reset collection if exists
            try:
                self.chroma_client.delete_collection(name=collection_name)
            except Exception:
                pass

            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )

            ids: List[str] = []
            documents: List[str] = []
            metadatas: List[Dict[str, Any]] = []

            for idx, r in enumerate(self.records):
                doc = (
                    f"Istilah: {r['slang_term']}. Kategori: {r['category']}. "
                    f"Arti: {r['meaning']}. Sentimen: {r['sentiment_bias']}. "
                    f"Contoh: {r['context_examples']}. Ticker: {r['formal_ticker'] or '-'}"
                )
                ids.append(f"slang_{idx}")
                documents.append(doc)
                metadatas.append({
                    "slang_term": r["slang_term"],
                    "formal_ticker": r["formal_ticker"] or "",
                    "category": r["category"],
                    "sentiment_bias": r["sentiment_bias"],
                    "meaning": r["meaning"][:300],
                })

            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            # Warm up vector store model to avoid first-query latency penalty
            try:
                self.collection.query(query_texts=["warmup test"], n_results=1)
            except Exception:
                pass

            self._is_initialized = True
            logger.info(f"Successfully indexed and warmed up {len(ids)} slang items into ChromaDB")

        except Exception as e:
            logger.warning(f"Could not initialize ChromaDB vector store: {e}. Falling back to internal dictionary.")
            self._is_initialized = True

    def count(self) -> int:
        """Returns total slang dictionary records."""
        if not self.records:
            self.load_data()
        return len(self.records)


# Global singleton instance
slang_store = SlangStore()
