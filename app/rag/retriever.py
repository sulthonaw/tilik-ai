"""Hybrid semantic retriever for IDX stock market slang and ticker aliases."""

import logging
import re
from typing import Any, Dict, List, Optional

from app.rag.slang_store import slang_store

logger = logging.getLogger("slang_retriever")


class SlangRetriever:
    """Hybrid retriever combining keyword/substring matching and vector similarity."""

    def __init__(self, store=slang_store):
        self.store = store

    def retrieve(self, query: str, top_k: int = 8) -> List[Dict[str, Any]]:
        """Retrieves top slang candidates relevant to the query text."""
        if not self.store.records:
            self.store.load_data()
        if not self.store._is_initialized:
            self.store.initialize_store()

        query_lower = query.lower()
        results: Dict[str, Dict[str, Any]] = {}

        # 1. Exact & Substring Matcher (highest confidence)
        for record in self.store.records:
            term = record["slang_term"]
            # Check whole word or phrase boundary
            pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
            if re.search(pattern, query_lower):
                results[term] = {
                    **record,
                    "score": 1.0,
                    "matched_method": "direct_match",
                }

        # 2. ChromaDB Semantic Vector Search
        if self.store.collection is not None:
            try:
                chroma_res = self.store.collection.query(
                    query_texts=[query],
                    n_results=min(top_k, len(self.store.records)),
                )
                if chroma_res and "metadatas" in chroma_res and chroma_res["metadatas"]:
                    metadatas = chroma_res["metadatas"][0]
                    distances = chroma_res.get("distances", [[]])[0] if "distances" in chroma_res else []
                    for idx, meta in enumerate(metadatas):
                        term = meta.get("slang_term")
                        if term and term not in results:
                            dist = distances[idx] if idx < len(distances) else 0.5
                            # Cosine distance to similarity: 1 - distance
                            score = max(0.0, min(1.0, 1.0 - float(dist)))
                            results[term] = {
                                "slang_term": term,
                                "formal_ticker": meta.get("formal_ticker") or None,
                                "category": meta.get("category"),
                                "meaning": meta.get("meaning"),
                                "sentiment_bias": meta.get("sentiment_bias"),
                                "score": round(score, 4),
                                "matched_method": "semantic_similarity",
                            }
            except Exception as e:
                logger.debug(f"ChromaDB query error: {e}")

        # 3. Fallback token-overlap search if vector store is not available or returned few items
        if len(results) < top_k:
            query_tokens = set(re.findall(r"\w+", query_lower))
            for record in self.store.records:
                term = record["slang_term"]
                if term in results:
                    continue
                term_tokens = set(re.findall(r"\w+", term))
                if term_tokens and term_tokens.issubset(query_tokens):
                    results[term] = {
                        **record,
                        "score": 0.8,
                        "matched_method": "token_overlap",
                    }

        # Sort results: direct matches first, then highest score
        sorted_results = sorted(
            results.values(),
            key=lambda x: (x.get("matched_method") == "direct_match", x.get("score", 0.0)),
            reverse=True,
        )

        return sorted_results[:top_k]

    def format_for_prompt(self, candidates: List[Dict[str, Any]]) -> str:
        """Formats retrieved candidates as a concise ground truth string for LLM context."""
        if not candidates:
            return "Tidak ada slang bursa khusus yang terdeteksi."

        lines = []
        for c in candidates:
            ticker_info = f" -> Emiten Resmi: {c['formal_ticker']}" if c.get("formal_ticker") else ""
            lines.append(
                f"- '{c['slang_term']}' ({c['category']}, Sentimen: {c['sentiment_bias']}): {c['meaning']}{ticker_info}"
            )
        return "\n".join(lines)


# Global singleton instance
slang_retriever = SlangRetriever()
