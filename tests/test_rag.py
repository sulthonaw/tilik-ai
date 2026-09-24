"""Tests for the Slang RAG Subsystem (30 Indonesian social media test phrases)."""

import time
import pytest
from app.rag.retriever import SlangRetriever, slang_retriever
from app.rag.slang_store import slang_store

TEST_PHRASES_30 = [
    ("Si ijo mulai diserok bandar YP di harga gocap", "si ijo", "GOTO"),
    ("Saham paman ditarik ke langit lagi hari ini", "paman", "BREN"),
    ("Om PP masuk barang tebal siap-siap to the moon", "om pp", "BREN"),
    ("Saham sejuta umat lagi diguyur bandar asing", "saham sejuta umat", "ANTM"),
    ("Beceha dividen interim cair lagi mantap", "beceha", "BBCA"),
    ("Bank sultan tetap kokoh biar IHSG merah merona", "bank sultan", "BBCA"),
    ("Beberi asing net sell terus nih mending tunggu di bawah", "beberi", "BBRI"),
    ("Mandur all time high lagi dividen jumbo", "mandur", "BMRI"),
    ("Saham indomie defensif cocok buat tabungan masa depan", "saham indomie", "ICBP"),
    ("Saham odol longsor terus nyangkut bertahun-tahun", "saham odol", "UNVR"),
    ("Saham sabun labanya tergerus boikot ritel boncos", "saham sabun", "UNVR"),
    ("Saham dino tidur mulu kapan bangunnya", "saham dino", "TLKM"),
    ("Bumi mulai ada transaksi volume jumbo lagi", "bumi", "BUMI"),
    ("Saham om boy mau spin-off mineral bagi dividen gede", "saham om boy", "ADRO"),
    ("Geng barito kompak hijau hari ini IHSG ikut terkerek", "geng barito", "BRPT"),
    ("HAKA sekarang sebelum kehabisan barang di antrean offer", "haka", None),
    ("Bandar mulai HAKI brutal di sesi dua kabur semua", "haki", None),
    ("Saatnya serok bawah mumpung ada diskon besar di pasar", "serok", None),
    ("Awas diguyur bandar jangan pasang antrean tebal di bid", "guyur", None),
    ("Saham dibanting 5 fraksi ritel langsung panik cut loss", "banting", None),
    ("Bandar mulai kerek harga ke ARA jangan lewatkan", "kerek", None),
    ("Titip sandal dulu 1 lot kalau terbang biar ada barang", "titip sandal", None),
    ("Asing siap nampung di harga bawah antrean tebal", "tampung", None),
    ("Portofolio disilet habis-habisan udah gak kuat nahan rugi", "disilet", None),
    ("Jangan fomo nanti cuma kebagian cuci piring di pucuk", "cuci piring", None),
    ("Alhamdulillah cuan luber 20 persen hari ini dari swing", "cuan", None),
    ("Saham ini calon multi bagger simpan rapi di RDN", "bagger", None),
    ("Masuk neraka FCA harga langsung ambles tiap sesi lelang", "fca", None),
    ("Ini saham beneran salah harga buruan masuk sebelum rame", "salah harga", None),
    ("Hati-hati pom-pom influencer akun centang biru jangan kemakan", "pom-pom", None),
]


def setup_module():
    """Warm up retriever before benchmarking latency."""
    slang_store.initialize_store()
    slang_retriever.retrieve("warmup query", top_k=5)


def test_slang_store_initialization():
    """Verify that the slang store loads at least 50 records and initializes cleanly."""
    count = slang_store.count()
    assert count >= 50, f"Expected at least 50 slang records, got {count}"
    assert len(slang_store.records) == count


@pytest.mark.parametrize("query,expected_term,expected_ticker", TEST_PHRASES_30)
def test_semantic_retrieval_30_phrases(query: str, expected_term: str, expected_ticker: str):
    """Tests accuracy of slang retrieval on 30 diverse Indonesian stock market phrases."""
    start_time = time.perf_counter()
    results = slang_retriever.retrieve(query, top_k=8)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Latency requirement: sub-second on local CPU
    assert elapsed_ms < 600, f"Retrieval took {elapsed_ms:.2f}ms (> 600ms)"
    assert len(results) > 0, f"No slang candidates retrieved for query: {query}"

    retrieved_terms = [r["slang_term"] for r in results]
    assert expected_term in retrieved_terms, (
        f"Expected term '{expected_term}' not in retrieved terms {retrieved_terms} for query: '{query}'"
    )

    if expected_ticker:
        tickers = [r.get("formal_ticker") for r in results if r.get("formal_ticker")]
        assert expected_ticker in tickers, (
            f"Expected ticker '{expected_ticker}' not found in retrieved tickers {tickers} for query: '{query}'"
        )


def test_format_for_prompt():
    """Verify prompt formatting helper outputs proper context."""
    candidates = slang_retriever.retrieve("si ijo mulai diserok bandar YP")
    prompt_context = slang_retriever.format_for_prompt(candidates)
    assert "si ijo" in prompt_context
    assert "GOTO" in prompt_context
    assert "Kategori" in prompt_context or "TICKER_ALIAS" in prompt_context
