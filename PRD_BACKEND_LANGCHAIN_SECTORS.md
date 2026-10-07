# 📘 PRODUCT REQUIREMENTS DOCUMENT (PRD)
## Project Name: Tilik AI — Backend Service
### In-Context Financial Fact-Checker & Slang RAG Engine for IDX Stocks
*(FastAPI + LangGraph + Google Gemini + Sectors API v2 + Slang CSV RAG)*

> **Target Implementation Path:** `E:\tilik-ai`  
> **Document Status:** Approved & Revised (Ready for Development)  
> **Version:** 2.0.0  
> **Target Release:** Sectors Hackathon 2026 (Track: AI Agents & Assistants / Reason)  
> **Engine Stack:** Python 3.11+ | FastAPI | LangGraph 0.2+ | Google Gemini (`gemini-2.0-flash`) | ChromaDB / FAISS (Slang RAG) | Sectors API v2 | Pydantic v2  
> **Environment & Deployment:** Local Virtualenv (`venv`) & Docker (`Dockerfile` + `docker-compose.yml`)  

---

## 1. PENGERTIAN & OBJECTIVE PRODUK (TILIK AI)

### 1.1 Filosofi Nama "Tilik AI"
Kata **"Tilik"** berasal dari bahasa Jawa/Indonesia yang bermakna *melihat secara teliti, memeriksa kebenaran, menengok kondisi, atau menginspeksi fakta*. **Tilik AI** adalah perisai pertahanan (*investor defense shield*) yang menilik dan memeriksa keabsahan narasi cuitan saham di media sosial langsung di titik kejadian (*in-context*).

### 1.2 Masalah yang Diselesaikan
1. **Kesenjangan Literasi (17,78% vs 80,51%):** Investor pemula mudah terpedaya klaim *pom-pom* finfluencer di X (Twitter), Threads, dan Telegram.
2. **The 15-Second UX Friction:** Verifikasi manual ke aplikasi sekuritas (RTI/Stockbit) terlalu ribet dan memakan waktu, kalah cepat dengan desakan dopamin impulsif (*"HAKA sekarang sebelum ARA!"*).
3. **Bahasa Gaul & Eufemisme Bursa:** Finfluencer kerap menyamarkan kode saham dengan istilah gaul (*"si ijo"*, *"saham paman"*, *"diserok YP"*, *"barang salah harga"*).

### 1.3 Solusi Inti & Nilai Tambah
* **Arsitektur Satu Pintu (*Single Unified Endpoint*):** Frontend Android cukup menembak 1 endpoint (`POST /api/v1/verify`). Backend secara otomatis mendeteksi slang, mengklasifikasi klaim, memanggil Sectors API v2 secara paralel, dan mengembalikan respons bertingkat:
  * **Level 1 (Default Card):** Kartu lampu lalu lintas (🔴 Merah, 🟡 Kuning, 🟢 Hijau), 3 fakta kunci (maksimal 25 kata/poin), dan jeda refleksi 5 detik.
  * **Level 2 (Expanded Data - Zero Latency):** Data angka mendalam (komparasi valuasi peers, rincian Top 5 broker summary, dan kesehatan laba) yang sudah ter-bundle di dalam payload, sehingga saat pengguna mengetuk *"Lihat Data Lengkap"*, data terbuka instan tanpa loading ulang.
* **Slang RAG Engine:** Database kamus slang berbasis CSV (`data/slang_dictionary.csv`) yang diindeks ke dalam vector store lokal untuk mendeteksi istilah gaul, julukan emiten, dan frasa manipulasi bursa secara akurat melalui *semantic search*.

---

## 2. ARSITEKTUR SISTEM & ALUR DATA END-TO-END

```mermaid
flowchart TD
    Client["Frontend Android (ACTION_PROCESS_TEXT / Overlay)"]
    
    subgraph FastAPI_Layer ["FastAPI Gateway (E:\\tilik-ai)"]
        VerifyEndpoint["POST /api/v1/verify"]
        HealthEndpoint["GET /api/v1/health"]
        CacheLayer["Fast In-Memory / Redis Cache (SHA256 Text Hash)"]
    end

    subgraph Slang_RAG_Subsystem ["Slang RAG Subsystem"]
        CSVSource[("data/slang_dictionary.csv")]
        VectorStore[("ChromaDB / FAISS Vector Store")]
        SemanticRetriever["Semantic Slang Retriever (Top-K Slang Context)"]
        CSVSource -->|Ingest & Embed| VectorStore
        VectorStore --> SemanticRetriever
    end

    subgraph LangGraph_Core ["LangGraph Agentic State Machine"]
        StartNode((START))
        NERNode["1. NER & Slang Resolution (Gemini Flash + RAG Context)"]
        IntentNode["2. Intent & Claim Classifier (Valuation, Flow, Earnings, FCA)"]
        ConcurrentFetchNode["3. Concurrent Sectors Data Fetcher (httpx.AsyncClient)"]
        EvaluatorNode["4. Fact-Checking & Anomaly Evaluator"]
        SynthesizerNode["5. Structured Output Generator (Pydantic Schema)"]
        EndNode((END))
    end

    subgraph External_APIs ["External Services"]
        SectorsAPI["Sectors API v2 (https://api.sectors.app)"]
        GeminiAPI["Google Gemini 2.0 Flash"]
    end

    Client -->|Raw Tweet Text| VerifyEndpoint
    VerifyEndpoint --> CacheLayer
    CacheLayer -->|Cache Hit (Immediate Response)| Client
    CacheLayer -->|Cache Miss| StartNode
    
    StartNode --> NERNode
    SemanticRetriever -.->|Inject Slang Candidates| NERNode
    NERNode <-->|Resolve Ticker| GeminiAPI
    NERNode --> IntentNode
    IntentNode --> ConcurrentFetchNode
    
    ConcurrentFetchNode <-->|Async Parallel: /v2/company/report, /v2/financials/quarterly, /v2/broker-summary, /v2/foreign-flow, /v2/suspensions| SectorsAPI
    ConcurrentFetchNode --> EvaluatorNode
    EvaluatorNode <-->|Reasoning vs Claims| GeminiAPI
    EvaluatorNode --> SynthesizerNode
    SynthesizerNode --> EndNode
    
    EndNode -->|Store to Cache| CacheLayer
    EndNode -->|Level 1 Summary + Level 2 Expanded Data| Client
```

---

## 3. STRUKTUR DIREKTORI PROYEK (`E:\tilik-ai`)

Berikut adalah struktur direktori resmi yang akan diimplementasikan di `E:\tilik-ai`:

```text
E:\tilik-ai\
├── data/
│   ├── slang_dictionary.csv        # Database CSV kamus slang pasar modal Indonesia
│   └── seed_slang.py               # Skrip inisialisasi & validasi data CSV
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application factory, CORS & Lifespan
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic-settings (.env configuration)
│   │   ├── cache.py                # In-memory / Redis SHA256 caching layer
│   │   └── security.py             # Basic rate limiting & request validator
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py              # Pydantic v2 Request, Response, Level 1 & Level 2
│   │   └── state.py                # LangGraph AgentState TypedDict
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── slang_store.py          # Vector store manager (ChromaDB / FAISS)
│   │   └── retriever.py            # Hybrid semantic retrieval untuk slang bursa
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py                # Kompilasi LangGraph StateGraph
│   │   ├── nodes.py                # Implementasi logika setiap node workflow
│   │   └── prompts.py              # System prompts deterministik untuk Gemini
│   ├── services/
│   │   ├── __init__.py
│   │   └── sectors_client.py       # Asynchronous Sectors API v2 HTTP client (httpx)
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           └── endpoints.py        # Router: POST /api/v1/verify & GET /api/v1/health
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures & mock Sectors API data
│   ├── test_rag.py                 # Pengujian semantic search slang CSV
│   ├── test_agent.py               # Pengujian eksekusi LangGraph workflow
│   └── test_api.py                 # Pengujian integrasi endpoint FastAPI
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md                       # HANYA: 1. Pengertian, 2. Cara Install (venv & Docker)
```

---


---

## 4. INTEGRASI RESMI SECTORS API v2 & OPTIMASI KREDIT

Sistem Tilik AI terhubung langsung ke **Sectors Financial API v2** (OpenAPI Catalog 3.0.3) dengan spesifikasi teknis dan optimasi berikut:

### 4.1 Spesifikasi Konektivitas & Billing
* **Base URL:** `https://api.sectors.app`
* **Autentikasi:** Header `Authorization: <SECTORS_API_KEY>` (tanpa awalan `Bearer`).
* **Format Ticker:** 4 huruf kapital (misal: `BBCA`, `GOTO`, `ANTM`), case-insensitive.
* **Optimasi Kuota (Credit Optimization):**
  * Endpoint `/v2/company/report/{symbol}/` mengenakan **1 credit per section**.
  * Default behavior (tanpa parameter `sections`) mengambil 8 section (biaya 8 credits).
  * **Tilik AI mewajibkan parameter:** `?sections=overview,valuation,financials,peers` sehingga konsumsi dipangkas 50% menjadi hanya **4 credits**!
  * Endpoint lainnya (`/v2/financials/quarterly/`, `/v2/broker-summary/{symbol}/top/`, `/v2/foreign-flow/{symbol}/`, `/v2/suspensions/`) masing-masing hanya mengonsumsi **1 credit**.

### 4.2 Pemetaan Endpoint Riil vs Kebutuhan Tilik AI

| Kebutuhan Analisis Tilik AI | Endpoint Resmi Sectors API v2 | Query Parameter Wajib / Rekomendasi | Output Kunci yang Digunakan |
| :--- | :--- | :--- | :--- |
| **Profil, Valuasi & Peers** | `GET /v2/company/report/{symbol}/` | `sections=overview,valuation,financials,peers` | `pe_ratio`, `pb_ratio`, `peers` (median PE & PBV sektor) |
| **Kinerja Laba Riil** | `GET /v2/financials/quarterly/{symbol}/` | `n_quarters=4`, `approx=true` | `revenue`, `earnings`, `operating_cash_flow` |
| **Bandar & Akumulasi Broker** | `GET /v2/broker-summary/{symbol}/top/` | `n_brokers=10`, `start`, `end` | `top_buyers`, `top_sellers`, `net_idr`, `foreign_net_idr` |
| **Arus Dana Investor Asing** | `GET /v2/foreign-flow/{symbol}/` | `start`, `end` (maks 90 hari) | `data[].net_foreign_inflow`, `data[].foreign_share` |
| **Suspensi & Notasi Bursa** | `GET /v2/suspensions/` | `symbol={symbol}`, `limit=5` | `results[].reason`, `results[].suspension_date`, status FCA |
| **Transaksi Orang Dalam** | `GET /v2/filings/` | `symbol={symbol}`, `limit=5` | `results[].transaction_type`, `holder_name`, insider activity |

### 4.3 Implementasi Client Asinkron (`app/services/sectors_client.py`)
```python
import httpx
from typing import Dict, Any, List, Optional
from app.core.config import settings

class SectorsAPIClient:
    """Asynchronous Client untuk komunikasi dengan Sectors API v2."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.SECTORS_API_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.SECTORS_API_KEY
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }

    async def get_company_report(self, symbol: str, sections: str = "overview,valuation,financials,peers") -> Dict[str, Any]:
        """Mengambil laporan ringkas emiten dengan optimasi 4 credits."""
        url = f"{self.base_url}/v2/company/report/{symbol.upper()}/"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self.headers, params={"sections": sections})
            resp.raise_for_status()
            return resp.json()

    async def get_quarterly_financials(self, symbol: str, n_quarters: int = 4) -> List[Dict[str, Any]]:
        """Mengambil laporan keuangan kuartalan (biaya 1 credit)."""
        url = f"{self.base_url}/v2/financials/quarterly/{symbol.upper()}/"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self.headers, params={"n_quarters": n_quarters, "approx": "true"})
            resp.raise_for_status()
            return resp.json()

    async def get_top_brokers(self, symbol: str, n_brokers: int = 10, start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, Any]:
        """Mengambil ringkasan Top Buyers dan Top Sellers broker (biaya 1 credit)."""
        url = f"{self.base_url}/v2/broker-summary/{symbol.upper()}/top/"
        params: Dict[str, Any] = {"n_brokers": n_brokers}
        if start: params["start"] = start
        if end: params["end"] = end
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_foreign_flow(self, symbol: str, start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, Any]:
        """Mengambil arus dana investor asing harian (biaya 1 credit)."""
        url = f"{self.base_url}/v2/foreign-flow/{symbol.upper()}/"
        params = {}
        if start: params["start"] = start
        if end: params["end"] = end
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_suspensions(self, symbol: str) -> Dict[str, Any]:
        """Mengecek apakah saham sedang disuspensi / notasi khusus oleh BEI."""
        url = f"{self.base_url}/v2/suspensions/"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self.headers, params={"symbol": symbol.upper(), "limit": 5})
            resp.raise_for_status()
            return resp.json()

    async def get_filings(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """Mengambil keterbukaan informasi dan aksi insider trading emiten."""
        url = f"{self.base_url}/v2/filings/"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self.headers, params={"symbol": symbol.upper(), "limit": limit})
            resp.raise_for_status()
            return resp.json()
```

## 5. SUBSISTEM SLANG RAG (`data/slang_dictionary.csv`)

### 5.1 Spesifikasi Kolom Database CSV
Berkas `data/slang_dictionary.csv` memuat kamus istilah bursa dengan struktur skema berikut:

| Nama Kolom | Tipe Data | Deskripsi & Contoh |
| :--- | :--- | :--- |
| `slang_term` | String (Indexed) | Istilah gaul/julukan (misal: `si ijo`, `paman`, `haka`, `haki`, `serok`, `cuci piring`) |
| `formal_ticker` | String (Nullable) | Kode resmi BEI jika merupakan julukan emiten (misal: `GOTO`, `BREN`, `ANTM`), atau `NULL` |
| `category` | Enum String | `TICKER_ALIAS` \| `ACTION` \| `BROKER` \| `MARKET_CONDITION` \| `HYPE_TRIGGER` |
| `meaning` | String | Penjelasan arti istilah dalam bahasa Indonesia baku |
| `sentiment_bias` | Enum String | `BULLISH` \| `BEARISH` \| `MANIPULATIVE` \| `NEUTRAL` |
| `context_examples` | String | Contoh kalimat penggunaan di X/Threads/Telegram |

### 5.2 Contoh Sampel Data CSV
```csv
slang_term,formal_ticker,category,meaning,sentiment_bias,context_examples
si ijo,GOTO,TICKER_ALIAS,Julukan untuk saham GoTo Gojek Tokopedia Tbk karena identitas warna hijau,NEUTRAL,"Si ijo mulai diserok bandar YP di harga gocap"
paman,BREN,TICKER_ALIAS,Julukan untuk saham konglomerasi Barito milik Prajogo Pangestu,BULLISH,"Saham paman ditarik ke langit lagi hari ini"
om pp,BREN,TICKER_ALIAS,Julukan konglomerasi Prajogo Pangestu (BREN/PTRO/CUAN/BRPT),BULLISH,"Om PP masuk barang tebal siap-siap to the moon"
saham sejuta umat,ANTM,TICKER_ALIAS,Julukan saham favorit investor ritel saat demam nikel dan emas,NEUTRAL,"Saham sejuta umat lagi diguyur bandar asing"
haka,NULL,ACTION,Hajar Kanan - membeli langsung di kolom offer agar transaksi langsung match,BULLISH,"HAKA sekarang sebelum kehabisan barang di antrean"
haki,NULL,ACTION,Hajar Kiri - menjual langsung di kolom bid agar saham langsung laku,BEARISH,"Bandar mulai HAKI brutal di sesi dua"
serok,NULL,ACTION,Membeli saham saat harga anjlok tajam dengan asumsi di dasar,BULLISH,"Saatnya serok bawah mumpung ada diskon besar"
cuci piring,NULL,MARKET_CONDITION,Kondisi ritel membeli di harga pucuk dan menanggung rugi saat bandar keluar,BEARISH,"Jangan fomo nanti cuma kebagian cuci piring"
salah harga,NULL,HYPE_TRIGGER,Klaim tidak berdasar bahwa saham sangat murah dan wajib naik tinggi,MANIPULATIVE,"Ini saham beneran salah harga buruan masuk"
to the moon,NULL,HYPE_TRIGGER,Klaim manipulatif bahwa harga saham akan terbang tanpa batas,MANIPULATIVE,"Siap-siap to the moon jangan sampai ketinggalan kereta"
yp,NULL,BROKER,Kode broker Mirae Asset Sekuritas representasi mayoritas investor ritel,NEUTRAL,"YP borong banyak tapi asing malah jualan bersih"
```

### 5.3 Cara Kerja RAG untuk Slang
1. Saat teks masuk ke backend, modul `rag/retriever.py` melakukan pencarian kemiripan semantik (*semantic similarity*) terhadap teks cuitan ke dalam `slang_dictionary.csv`.
2. Kandidat slang yang terdeteksi (misal: *"si ijo"*, *"serok"*, *"salah harga"*) ditarik bersama artinya.
3. Rangkuman kamus ini disuntikkan ke dalam *system prompt* Gemini Flash sebagai *ground truth context*.
4. Gemini Flash mengidentifikasi kode saham resmi (`GOTO`) dan maksud klaim secara akurat dengan latensi **< 300 ms**.

---

## 6. SKEMA KONTRAK DATA PYDANTIC V2 (DUAL-LEVEL PAYLOAD)

Backend mengembalikan payload lengkap yang langsung memuat **Level 1 (Summary Card)** dan **Level 2 (Expanded Data)**:

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class VerdictLevel(str, Enum):
    HOAX_BAHAYA = "HOAX_BAHAYA"      # 🔴 HOAX / BAHAYA: Klaim bohong, pom-pom manipulatif, atau saham bertato suspensi
    WASPADA = "WASPADA"              # 🟡 WASPADA: Ada fakta tersembunyi/separuh benar, atau harga kemahalan/premium, jangan buru-buru
    SESUAI_FAKTA = "SESUAI_FAKTA"    # 🟢 SESUAI FAKTA: Informasi valid dan fundamental terbukti sehat

# LEVEL 1: Summary Facts (Maksimal 25 kata per poin)
class FactCheckPoint(BaseModel):
    title: str = Field(..., description="Parameter fakta, misal: 'Valuasi PER'")
    fact: str = Field(..., max_length=150, description="Uraian komparasi data, maks 25 kata")
    is_favorable: bool = Field(..., description="True jika mendukung fundamental sehat")

# LEVEL 2: Expanded Data (Untuk tombol 'Lihat Data Lengkap')
class ValuationPeerDetail(BaseModel):
    pe_ratio: Optional[float] = Field(None, description="Price to Earnings Ratio emiten")
    pbv_ratio: Optional[float] = Field(None, description="Price to Book Value Ratio emiten")
    industry_median_pe: Optional[float] = Field(None, description="Median PE industri sejenis")
    industry_median_pbv: Optional[float] = Field(None, description="Median PBV industri sejenis")
    valuation_status: str = Field(..., example="45% Lebih Mahal dari Sektor")

class BrokerDetail(BaseModel):
    broker_code: str = Field(..., example="YP")
    broker_type: str = Field(..., example="Ritel Domestik | Asing")
    net_value_idr: float = Field(..., description="Nilai transaksi bersih dalam Rupiah")
    action: str = Field(..., example="NET_BUY | NET_SELL")

class BrokerFlowDetail(BaseModel):
    foreign_net_idr: float = Field(..., description="Total akumulasi bersih asing hari ini")
    top_buyers: List[BrokerDetail] = Field(default_factory=list)
    top_sellers: List[BrokerDetail] = Field(default_factory=list)
    summary_verdict: str = Field(..., example="Asing net sell Rp 12M, pembeli didominasi ritel")

class FinancialHealthDetail(BaseModel):
    net_profit_growth_yoy: Optional[float] = Field(None, description="Pertumbuhan laba bersih YoY (%)")
    operating_cash_flow_idr: Optional[float] = Field(None, description="Arus kas operasional")
    is_fca: bool = Field(..., description="True jika masuk Papan Pemantauan Khusus")
    special_notations: List[str] = Field(default_factory=list, description="Daftar tato bursa, misal: ['X']")

class ExpandedDetails(BaseModel):
    valuation: ValuationPeerDetail
    broker_flow: BrokerFlowDetail
    financial_health: FinancialHealthDetail

# ENUM ROLE PENGGUNA
class UserRole(str, Enum):
    PEMULA = "PEMULA"    # Bahasa santai, analogi sederhana, cooling-off sebagai pesan statis protektif
    EXPERT = "EXPERT"    # Bahasa teknis padat, istilah industri, devil's advocate prompt

# REQUEST & RESPONSE UNIFIED
class VerifyTweetRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=1000, example="Si ijo mulai diserok bandar YP, valuasi salah harga to the moon!")
    source_platform: Optional[str] = Field("x", example="x | threads | telegram")
    user_role: UserRole = Field(UserRole.PEMULA, description="Mode tampilan dan bahasa. Ditetapkan dari pengaturan onboarding pengguna.")

class VerificationResponse(BaseModel):
    status: str = Field("success", example="success")
    ticker: Optional[str] = Field(None, example="GOTO")
    company_name: Optional[str] = Field(None, example="GoTo Gojek Tokopedia Tbk")
    user_role: UserRole = Field(..., description="Role yang digunakan saat request — di-echo kembali untuk kebutuhan UI rendering")
    
    # --- LEVEL 1: SUMMARY CARD ---
    verdict: VerdictLevel = Field(..., description="Status lampu lalu lintas")
    confidence_score: float = Field(..., ge=0.0, le=1.0, example=0.94)
    points: List[FactCheckPoint] = Field(..., min_length=1, max_length=3)
    cooling_off_prompt: str = Field(..., description="Pesan statis refleksi (Pemula) atau pertanyaan devil's advocate (Expert)")
    
    # --- LEVEL 2: EXPANDED DATA (Zero-Latency Tab) ---
    details: ExpandedDetails
    
    is_cached: bool = Field(False)
```

---


### 6.1 Arsitektur Level 2: Pure Deterministic Data (Tanpa AI)
> ⚠️ **PRINSIP DESAIN LEVEL 2 (LIHAT DETAIL DATA):**  
> Data di Level 2 **SAMA SEKALI TIDAK MENGGUNAKAN AI**. Level 2 menyajikan data keuangan mentah terstruktur yang dipass-through langsung dari Sectors API v2 ke antarmuka Android.  
> **Keunggulan:**  
> 1. **Nol Halusinasi:** 100% angka resmi bursa (PBV, PER, Broker net value, laba kuartalan).  
> 2. **Zero Latency:** Tampil seketika tanpa jeda pemrosesan LLM.  
> 3. **Hemat Biaya Token:** 0 token Gemini digunakan untuk merender data detail.

#### 4 Kotak Data Utama Level 2:
1. **Kotak Valuasi (Kewajaran Harga vs Sektor):**
   * PBV & PER Emiten vs Median Sektor (dihitung deterministik dari array `peers`).
   * Tabel komparasi 3 emiten sejenis (*peer comparison*).
2. **Kotak Arus Transaksi (Bandar & Asing):**
   * Total arus dana bersih asing hari ini (`foreign_net_idr`).
   * Top 3–5 broker pembeli (*buyers*) & penjual (*sellers*) beserta net value dan klasifikasi (Institusi vs Ritel).
3. **Kotak Kinerja Keuangan (Laba & Pendapatan Kuartalan):**
   * Laba bersih kuartal terakhir (`earnings`) dan pertumbuhan YoY.
   * Pendapatan kuartal terakhir (`revenue`) dan arus kas operasional (`operating_cash_flow`).
4. **Kotak Keamanan Bursa:**
   * Status suspensi resmi bursa (`results` dari `/v2/suspensions/`).
   * Papan pencatatan emiten (`listing_board` dari `/v2/company/report/`).

## 7. SPESIFIKASI ENDPOINT API (FASTAPI)

### 7.1 `POST /api/v1/verify`
* **Path:** `/api/v1/verify`
* **Method:** `POST`
* **Headers:** `Content-Type: application/json`
* **Request Payload:** `VerifyTweetRequest`
* **Response 200 OK (Contoh Mode PEMULA):**
```json
{
  "status": "success",
  "ticker": "BBCA",
  "company_name": "Bank Central Asia Tbk",
  "user_role": "PEMULA",
  "verdict": "WASPADA",
  "confidence_score": 0.92,
  "points": [
    {
      "title": "Kewajaran Harga Saham",
      "fact": "Harga Tergolong Premium: Saat ini dihargai 2,4x dari modal bersihnya, 45,5% lebih tinggi dari rata-rata bank lain (1,6x).",
      "is_favorable": false
    },
    {
      "title": "Arus Dana Asing",
      "fact": "Investor Asing Borong Besar: Ada dana asing masuk bersih Rp 429,7 Miliar hari ini melalui broker institusi besar.",
      "is_favorable": true
    },
    {
      "title": "Keamanan & Status Saham",
      "fact": "Sangat Aman: Berjalan normal, sehat secara operasional, dan bebas dari sanksi atau pantauan khusus bursa.",
      "is_favorable": true
    }
  ],
  "cooling_off_prompt": "Catatan Panduan: BBCA sangat solid dan didukung aliran dana institusi besar, namun valuasinya berada di batas atas industri. Mencicil bertahap (DCA) jauh lebih terukur dibanding pembelian agresif sekaligus.",
  "details": {
    "valuation": {
      "pe_ratio": 22.4,
      "pbv_ratio": 2.4,
      "industry_median_pe": 18.5,
      "industry_median_pbv": 1.65,
      "valuation_status": "Harga Premium (45.5% Lebih Tinggi dari Rata-Rata Industri)"
    },
    "broker_flow": {
      "foreign_net_idr": 429706960000.0,
      "top_buyers": [
        {"broker_code": "DX", "broker_type": "Institusi", "net_value_idr": 15200000000.0, "action": "NET_BUY"},
        {"broker_code": "YU", "broker_type": "Institusi", "net_value_idr": 15200000000.0, "action": "NET_BUY"}
      ],
      "top_sellers": [
        {"broker_code": "BK", "broker_type": "Asing / Institusi", "net_value_idr": 24100000000.0, "action": "NET_SELL"},
        {"broker_code": "AK", "broker_type": "Asing / Institusi", "net_value_idr": 24100000000.0, "action": "NET_SELL"}
      ],
      "summary_verdict": "Investor Asing borong bersih Rp 429,7 Miliar, didorong oleh akumulasi broker institusi besar"
    },
    "financial_health": {
      "net_profit_growth_yoy": 12.4,
      "operating_cash_flow_idr": -15658754000000.0,
      "is_fca": false,
      "special_notations": []
    }
  },
  "is_cached": false
}
```

* **Response 200 OK (Contoh Mode EXPERT - Level 1 Padat & Devil's Advocate):**
```json
{
  "status": "success",
  "ticker": "BBCA",
  "company_name": "Bank Central Asia Tbk",
  "user_role": "EXPERT",
  "verdict": "WASPADA",
  "confidence_score": 0.92,
  "points": [
    {
      "title": "Valuasi Relatif",
      "fact": "PBV 2.4x (premium 45.5% vs median sektor 1.65x); trailing PE 22.4x vs industri 18.5x.",
      "is_favorable": false
    },
    {
      "title": "Arus Transaksi Asing",
      "fact": "Net foreign inflow +Rp429.7B; konsentrasi top buyers institusional DX dan YU.",
      "is_favorable": true
    },
    {
      "title": "Listing & Kepatuhan",
      "fact": "Main Board IDX, non-FCA, nihil notasi khusus bursa.",
      "is_favorable": true
    }
  ],
  "cooling_off_prompt": "Devil's Advocate: OCF kuartalan tercatat -Rp15.6T meski laba bersih tumbuh +12.4% YoY. Apakah thesis Anda telah memisahkan ekspansi kredit wajar perbankan dari risiko kenaikan pencadangan NPL?",
  "details": {
    "valuation": {
      "pe_ratio": 22.4,
      "pbv_ratio": 2.4,
      "industry_median_pe": 18.5,
      "industry_median_pbv": 1.65,
      "valuation_status": "Premium 45.5% vs Median Industri"
    },
    "broker_flow": {
      "foreign_net_idr": 429706960000.0,
      "top_buyers": [
        {"broker_code": "DX", "broker_type": "Institusi", "net_value_idr": 15200000000.0, "action": "NET_BUY"},
        {"broker_code": "YU", "broker_type": "Institusi", "net_value_idr": 15200000000.0, "action": "NET_BUY"}
      ],
      "top_sellers": [
        {"broker_code": "BK", "broker_type": "Asing / Institusi", "net_value_idr": 24100000000.0, "action": "NET_SELL"},
        {"broker_code": "AK", "broker_type": "Asing / Institusi", "net_value_idr": 24100000000.0, "action": "NET_SELL"}
      ],
      "summary_verdict": "Net foreign inflow +Rp429.7B dominasi akumulasi institusi"
    },
    "financial_health": {
      "net_profit_growth_yoy": 12.4,
      "operating_cash_flow_idr": -15658754000000.0,
      "is_fca": false,
      "special_notations": []
    }
  },
  "is_cached": false
}
```

### 7.2 `GET /api/v1/health`
* **Path:** `/api/v1/health`
* **Response 200 OK:**
```json
{
  "status": "healthy",
  "app_name": "Tilik AI Backend",
  "version": "2.0.0",
  "gemini_api": "connected",
  "sectors_api": "connected",
  "slang_rag_records": 120
}
```

---


---

### 8. PANDUAN TONE OF VOICE & ARSITEKTUR MULTI-ROLE (HUMAN-CENTERED FINANCIAL LANGUAGE)

Tilik AI dirancang untuk memecahkan kesenjangan literasi keuangan Indonesia (hanya 17,78%). Bahasa luaran AI disesuaikan secara adaptif berdasarkan nilai `user_role` pada permintaan (`PEMULA` atau `EXPERT`). Modul `app/agent/prompts.py` mengelola blueprint prompt khusus untuk masing-masing profil pengguna:

### 8.1 Komparasi Karakteristik Antar Role

| Aspek | Mode PEMULA | Mode EXPERT |
| :--- | :--- | :--- |
| **Gaya Bahasa Fakta** | Analogi sederhana, naratif santai, bebas jargon mentah | Presisi tinggi, ringkas, istilah baku bursa (PE, PBV, OCF) |
| **Contoh Uraian Valuasi** | *"Harga 2,4x lipat dari modal bersihnya, 45% lebih mahal dibanding rata-rata bank lain"* | *"PBV 2.4x (premium 45% vs median sektor 1.65x); PE 22.4x vs median 18.5x"* |
| **Contoh Uraian Broker Flow** | *"Investor luar negeri sedang banyak masuk ratusan miliar hari ini"* | *"Net foreign inflow +Rp429.7B; didorong broker institusi DX & YU; YP net sell"* |
| **Sifat Cooling-Off / Alert** | **Pesan Statis Protektif** (selalu tampil mendidik, bukan countdown/timer) | **Devil's Advocate Prompt** (pertanyaan penantang tesis/anomali data) |
| **Contoh Cooling-Off / Alert** | *"Perusahaannya bagus, tetapi harganya sedang mahal. Beli bertahap lebih aman daripada terburu-buru."* | *"OCF negatif Rp15.6T meski laba naik 12% YoY. Ekspansi kredit normal atau ada penurunan kualitas aset?"* |
| **Peran Slang RAG** | Menerjemahkan bahasa gaul agar pemula paham konteks narasi | Ekstraksi ticker presisi dari kerumunan *social noise* & cashtags |

### 8.2 Pedoman Bahasa Manusiawi untuk Mode PEMULA
1. **Prinsip "Analogi Warung" (No Naked Jargon):**
   * Jelaskan arti dari angka, bukan sekadar menyebut nama rasio.
   * `PBV 2.4x` dijelaskan sebagai *"Dihargai 2,4x dari modal bersihnya"*.
2. **Kesesuaian Angka & Narasi Mutlak (Zero Hallucination):**
   * Teks di Level 1 wajib merefleksikan nilai riil di Level 2 (`foreign_net_idr` positif harus dinyatakan akumulasi dana asing, dilarang memakai template ritel YP).
3. **Pesan Refleksi Statis (Bukan Countdown Timer):**
   * Tidak memakai penghitung waktu buatan yang mengganggu alur. Menampilkan pesan statis yang relevan dengan tipe cuitan (pertanyaan entry vs klaim pom-pom).
4. **Konteks Khusus Saham Perbankan:**
   * Di sektor perbankan, OCF negatif pada fase ekspansi kredit adalah hal lumrah. Sistem dilarang menyimpulkan kinerja bank buruk selama laba bersih bertumbuh sehat.

### 8.3 Blueprint Generator Prompt (`app/agent/prompts.py`)
```python
SYNTHESIZER_SYSTEM_PROMPT_PEMULA = """
Anda adalah Tilik AI, asisten pelindung investor pemula dari FOMO dan manipulasi pasar modal Indonesia (IDX).
Tugas Anda adalah merangkum data bursa resmi dari Sectors API menjadi kartu verifikasi yang SANGAT MUDAH DIPAHAMI OLEH PEMULA.

PEDOMAN TONE OF VOICE (WAJIB DIPATUHI):
1. GUNAKAN BAHASA MANUSIAWI & ANALOGI SEDERHANA:
   - Jelaskan rasio keuangan dengan artinya, BUKAN rumusnya.
   - Daripada 'PBV 2.4x', gunakan 'Dihargai 2,4x dari modal bersihnya (tergolong premium/mahal dibanding rata-rata sektor)'.
   - Daripada 'Akumulasi Broker', gunakan 'Pergerakan Dana Asing & Bandar'.
   - Daripada 'Papan Pemantauan Khusus (FCA)', gunakan 'Status Keamanan & Bursa'.
2. SINKRONISASI DATA RIIL:
   - Jika foreign_net_idr POSITIF: nyatakan asing sedang memborong/akumulasi.
   - Jika foreign_net_idr NEGATIF: nyatakan asing sedang melakukan aksi jual bersih.
3. PESAN REFLEKSI STATIS KONTEKSTUAL:
   - Jika cuitan bernada ragu/bertanya entry: sarankan beli bertahap (DCA) atau tunggu momentum diskon.
   - Jika cuitan bernada pom-pom: ingatkan bahaya FOMO di harga pucuk.
   - Selalu tampilkan sebagai catatan panduan statis yang menenangkan.
4. MAKSIMAL 25 KATA PER POIN FAKTA: Padat, akurat, dan menenangkan psikologi pengguna.
"""

SYNTHESIZER_SYSTEM_PROMPT_EXPERT = """
Anda adalah Tilik AI dalam mode Expert — alat validasi data cepat untuk analis dan investor berpengalaman.
Tugas Anda adalah menyajikan data bursa resmi dari Sectors API secara PADAT, TEKNIS, dan EFISIEN.

PEDOMAN TONE OF VOICE (WAJIB DIPATUHI):
1. TERMINOLOGI INDUSTRI STANDAR:
   - Gunakan istilah baku: PBV, PE, net foreign inflow/outflow, OCF, YoY, broker flow.
   - Langsung sebutkan angka dan deviasi vs benchmark industri tanpa parafrase panjang.
2. SINKRONISASI DATA RIIL MUTLAK:
   - Sajikan pergerakan dana institusi dan net foreign flow sesuai kalkulasi nominal aktual.
3. DEVIL'S ADVOCATE PROMPT (PENANTANG TESIS):
   - Jangan berikan nasihat emosional/protektif pemula.
   - Ajukan satu pertanyaan kritis yang menyoroti kontradiksi atau anomali data keuangan.
   - Contoh: 'OCF negatif Rp15.6T meski laba naik 12% YoY. Ekspansi kredit normal atau penurunan kualitas aset?'
4. MAKSIMAL 20 KATA PER POIN FAKTA: Padat, berbasis metrik, bebas basa-basi.
"""

def get_synthesizer_prompt(user_role: str) -> str:
    """Mengembalikan system prompt yang sesuai dengan preferensi role pengguna."""
    if user_role == "EXPERT":
        return SYNTHESIZER_SYSTEM_PROMPT_EXPERT
    return SYNTHESIZER_SYSTEM_PROMPT_PEMULA
```

## 9. TEKNOLOGI & DEPENDENSI (`requirements.txt`)

```text
fastapi==0.115.0
uvicorn[standard]==0.31.0
pydantic==2.9.2
pydantic-settings==2.5.2
langgraph==0.2.28
langchain-core==0.3.0
langchain-google-genai==2.0.0
google-genai==0.1.1
chromadb==0.5.5
pandas==2.2.3
httpx==0.27.2
python-dotenv==1.0.1
cachetools==5.5.0
pytest==8.3.3
pytest-asyncio==0.24.0
```

---

## 10. LINGKUNGAN PENGEMBANGAN: DOCKER & VENV

### 10.1 Setup Virtual Environment Lokal (`venv`)
* **Di Windows (PowerShell):**
  ```powershell
  cd E:\tilik-ai
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  pip install --upgrade pip
  pip install -r requirements.txt
  ```
* **Di Linux / macOS:**
  ```bash
  cd E:\tilik-ai
  python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  ```

### 10.2 Konfigurasi `Dockerfile`
```dockerfile
FROM python:3.11-slim-bullseye

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends curl build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 10.3 Konfigurasi `docker-compose.yml`
```yaml
version: '3.8'

services:
  tilik-backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: tilik_ai_backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./app:/app/app
      - ./data:/app/data
    environment:
      - PORT=8000
      - HOST=0.0.0.0
```

---

## 11. ATURAN STANDAR `README.md` REPOSITORI (WAJIB DIIKUTI)

> ⚠️ **INSTRUKSI KHUSUS:**  
> Berkas `README.md` pada repositori proyek `E:\tilik-ai` HANYA BOLEH memuat 2 bab berikut tanpa konten tambahan:

```markdown
# 🔍 Tilik AI — Backend Service

## 1. Pengertian
Backend service berbasis **FastAPI**, **LangGraph**, dan **Google Gemini** yang bertugas menilik dan memvalidasi keabsahan cuitan saham di media sosial Indonesia (X, Threads, Telegram) secara real-time menggunakan data bursa resmi dari **Sectors API v2**. Sistem dilengkapi mesin **Slang RAG** berbasis database CSV untuk mengenali bahasa gaul bursa, membandingkan klaim terhadap data fundamental, valuasi relatif, dan broker flow, serta mengembalikan kartu verifikasi lampu lalu lintas (Merah, Kuning, Hijau) beserta data angka mendalam dalam waktu < 2 detik.

---

## 2. Cara Install & Menjalankan

### Opsi A: Menjalankan via Virtual Environment (venv)
1. **Clone Repositori & Masuk ke Folder:**
   ```bash
   cd E:\tilik-ai
   ```
2. **Buat & Aktifkan Virtual Environment:**
   * Windows (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   * Linux / macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Siapkan Environment Variables:**
   ```bash
   cp .env.example .env
   # Buka file .env dan isi GOOGLE_API_KEY serta SECTORS_API_KEY Anda
   ```
5. **Jalankan Server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Akses dokumentasi Swagger UI di: `http://localhost:8000/docs`

---

### Opsi B: Menjalankan via Docker
1. **Siapkan File `.env`:**
   ```bash
   cp .env.example .env
   # Lengkapi API Key di file .env
   ```
2. **Build & Jalankan Container:**
   ```bash
   docker compose up -d --build
   ```
3. **Cek Kesehatan Server:**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```
```

---

## 12. REKAYASA PENGUJIAN (`pytest`)
* `test_rag.py`: Menguji akurasi semantic retrieval kamus CSV slang terhadap 30 frasa cuitan acak.
* `test_agent.py`: Menguji eksekusi node LangGraph dan fallback saat upstream Sectors API timeout.
* `test_api.py`: Menguji payload response `POST /api/v1/verify` memastikan field `points` (Level 1) dan `details` (Level 2) terisi lengkap sesuai skema Pydantic v2.
