"""Slang dictionary seed & validation script for Tilik AI."""

import csv
import logging
import sys
from pathlib import Path
from typing import Dict, List, Set

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_slang")

DATA_DIR = Path(__file__).resolve().parent
CSV_PATH = DATA_DIR / "slang_dictionary.csv"

REQUIRED_COLUMNS = [
    "slang_term",
    "formal_ticker",
    "category",
    "meaning",
    "sentiment_bias",
    "context_examples",
]

ALLOWED_CATEGORIES = {
    "TICKER_ALIAS",
    "ACTION",
    "BROKER",
    "MARKET_CONDITION",
    "HYPE_TRIGGER",
}

ALLOWED_SENTIMENTS = {
    "BULLISH",
    "BEARISH",
    "MANIPULATIVE",
    "NEUTRAL",
}


def validate_and_stats(file_path: Path = CSV_PATH) -> Dict[str, any]:
    """Validates the CSV dictionary format and returns summary statistics."""
    if not file_path.exists():
        raise FileNotFoundError(f"Slang CSV not found at: {file_path}")

    seen_terms: Set[str] = set()
    category_counts: Dict[str, int] = {cat: 0 for cat in ALLOWED_CATEGORIES}
    sentiment_counts: Dict[str, int] = {sent: 0 for sent in ALLOWED_SENTIMENTS}
    tickers: Set[str] = set()
    total_records = 0
    errors: List[str] = []

    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in (reader.fieldnames or [])]
        if missing_cols:
            raise ValueError(f"Missing required columns in CSV: {missing_cols}")

        for line_num, row in enumerate(reader, start=2):
            total_records += 1
            term = (row.get("slang_term") or "").strip().lower()
            ticker = (row.get("formal_ticker") or "").strip().upper()
            category = (row.get("category") or "").strip().upper()
            sentiment = (row.get("sentiment_bias") or "").strip().upper()
            meaning = (row.get("meaning") or "").strip()

            if not term:
                errors.append(f"Line {line_num}: Empty slang_term")
                continue

            if term in seen_terms:
                logger.warning(f"Line {line_num}: Duplicate slang_term '{term}' detected")
            seen_terms.add(term)

            if not meaning:
                errors.append(f"Line {line_num}: Empty meaning for term '{term}'")

            if category not in ALLOWED_CATEGORIES:
                errors.append(
                    f"Line {line_num}: Invalid category '{category}' for term '{term}'. Allowed: {ALLOWED_CATEGORIES}"
                )
            else:
                category_counts[category] += 1

            if sentiment not in ALLOWED_SENTIMENTS:
                errors.append(
                    f"Line {line_num}: Invalid sentiment '{sentiment}' for term '{term}'. Allowed: {ALLOWED_SENTIMENTS}"
                )
            else:
                sentiment_counts[sentiment] += 1

            if ticker:
                tickers.add(ticker)

    if errors:
        for err in errors:
            logger.error(err)
        raise ValueError(f"Found {len(errors)} validation error(s) in {file_path}")

    stats = {
        "total_records": total_records,
        "unique_terms": len(seen_terms),
        "unique_tickers": len(tickers),
        "categories": category_counts,
        "sentiments": sentiment_counts,
        "tickers": sorted(list(tickers)),
    }
    return stats


def main() -> None:
    logger.info(f"Validating slang dictionary at: {CSV_PATH}")
    try:
        stats = validate_and_stats(CSV_PATH)
        logger.info(f"Validation successful! Total records: {stats['total_records']}")
        logger.info(f"Unique tickers mapped: {stats['unique_tickers']} ({', '.join(stats['tickers'])})")
        logger.info(f"Category distribution: {stats['categories']}")
        logger.info(f"Sentiment distribution: {stats['sentiments']}")
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
