# 🤖 AGENT RULES & CONTEXT MEMORY
## Proyek: Tilik AI — In-Context Financial Fact-Checker (Sectors Hackathon 2026)

> **Untuk Setiap AI Agent / Coding Assistant:**  
> Dokumen ini adalah **Ground Truth & Rules** utama proyek. Baca dokumen ini sebelum mengambil tindakan, menulis kode, atau memodifikasi arsitektur sistem di target repositori `E:\tilik-ai`. Dokumen ini merangkum seluruh riset masalah, validasi data, dan keputusan desain yang telah disepakati.

---

## 1. MISI & IDENTITAS PROYEK
* **Nama Proyek:** Tilik AI (Berasal dari kata "Tilik": memeriksa, meninjau, menginspeksi fakta).
* **Target Direktori Implementasi:** `E:\tilik-ai`
* **Target Kompetisi:** Sectors App Hackathon 2026 (Track: AI Agents & Assistants / Reason)
* **Penyelenggara:** Sectors & Supertype
* **Misi Utama:** Memotong transmisi FOMO (*Fear of Missing Out*) dan manipulasi *pom-pom* finfluencer langsung di tempat kejadian (media sosial smartphone: X/Threads/Telegram) menggunakan antarmuka melayang (*floating bottom sheet*) Android yang memvalidasi klaim ke **Sectors API v2** dalam waktu **< 1,5 detik**.

---

## 2. KEBUTUHAN PENGGUNA: 4 PERTANYAAN KRITIS & PEMETAAN RESMI SECTORS API v2
Investor pemula memiliki literasi pasar modal rendah (17,78%) dan rentan panik. Mereka **TIDAK BUTUH** tabel laporan keuangan 20 halaman. Setiap fitur sistem HARUS menjawab 4 pertanyaan ini menggunakan endpoint resmi Sectors API v2:

1. **Identitas & Keamanan:** *"Ini saham apa dan apakah bermasalah/masuk Papan FCA?"*  
   $
ightarrow$ Dicek via: `GET /v2/suspensions/?symbol={symbol}` (Notasi & Suspensi Resmi BEI) dan `GET /v2/company/report/{symbol}/?sections=overview` (Status Listing Board).
2. **Uji Klaim Valuasi ('Murah / Salah Harga'):** *"Beneran murah dibanding kompetitor sejenis?"*  
   $
ightarrow$ Dicek via: `GET /v2/company/report/{symbol}/?sections=valuation,peers` (Bandingkan PER/PBV terhadap median sektor dan peers emiten).
3. **Uji Klaim Bandar ('Bandar Borong / Asing Serok'):** *"Siapa yang beneran beli?"*  
   $
ightarrow$ Dicek via: `GET /v2/broker-summary/{symbol}/top/?n_brokers=10` dan `GET /v2/foreign-flow/{symbol}/` (Validasi akumulasi top 5 broker: institusi/asing vs ritel panik seperti YP/PD).
4. **Uji Klaim Kinerja Laba ('Laba Melesat 500%'):** *"Labanya untung jualan beneran atau sulap akuntansi?"*  
   $
ightarrow$ Dicek via: `GET /v2/financials/quarterly/{symbol}/?n_quarters=4` dan `GET /v2/company/report/{symbol}/?sections=financials` (Bedah laba operasional inti vs arus kas operasional / *operating cash flow*).

---

## 3. ATURAN MUTLAK SISTEM (SYSTEM INVARIANTS)
Setiap agent yang menulis kode atau dokumentasi WAJIB mematuhi 6 aturan berikut tanpa pengecualian:

* 🚫 **INVARIANT 1 (Regulasi OJK - POJK No. 6/2026 & UU P2SK):**  
  Sistem **DILARANG KERAS** memberikan rekomendasi investasi personal, sinyal transaksi (seperti *"Wajib beli!"* atau *"Segera cut loss!"*), atau menentukan target price. Sistem MURNI berposisi sebagai **Penyedia Informasi Fakta Objektif (*Factual Information Provider*)** dengan menyandingkan *Klaim Medsos vs Laporan Resmi IDX*, serta menyertakan klausul *Disclaimer On*.
* 🚫 **INVARIANT 2 (Aturan Mutlak Sectors Hackathon):**  
  Sistem **DILARANG KERAS** membuat fitur *automated trade execution* (order beli/jual otomatis di akun nyata atau sekuritas). Sistem hanya boleh bersifat analitis, fact-checking, scoring, dan alert.
* 🚦 **INVARIANT 3 (Format Output Dual-Level Payload & Arsitektur Multi-Role):**  
  Frontend cukup menembak **1 endpoint tunggal**: `POST /api/v1/verify` dengan menyertakan parameter `user_role` (`PEMULA` atau `EXPERT`).  
  Output payload langsung memuat 2 tingkatan data:
  - **Level 1 (Default Card):** Status lampu lalu lintas (🔴 HOAX / BAHAYA, 🟡 WASPADA, 🟢 SESUAI FAKTA), **tepat 1–3 poin fakta** dengan panjang **maksimal 20-25 kata per poin**, dan panduan kontekstual (`cooling_off_prompt`):
    * **Mode PEMULA:** Menampilkan narasi bahasa manusiawi bebas jargon mentah (contoh: *"Harga 2,4x dari modal bersihnya"*) dan **catatan panduan statis** (bukan timer countdown gimmick).
    * **Mode EXPERT:** Menampilkan metrik presisi industri (PBV, PE, net foreign flow) dan **Devil's Advocate prompt** yang menantang tesis atau menyorot anomali data (misal: OCF negatif vs kenaikan laba).
  - **Level 2 (Zero Latency & Zero AI):** Field `details` yang memuat angka mendalam (valuasi vs peers, broker flow, kesehatan laba) untuk ditampilkan seketika saat pengguna mengetuk *"Lihat Data Lengkap"*. Dilarang menggunakan LLM untuk Level 2 (100% data murni Sectors API).
* 📊 **INVARIANT 4 (Slang RAG Subsystem):**  
  Pencocokan bahasa gaul bursa wajib memanfaatkan database CSV `data/slang_dictionary.csv` (memuat julukan emiten, aksi transaksi, dan kode broker) yang diindeks ke dalam vector store (ChromaDB/FAISS) untuk menyuplai *ground truth context* ke Gemini Flash.
* ⚡ **INVARIANT 5 (Optimasi Kuota & Multi-Tier Caching Sectors API v2):**  
  1. **Section Optimization:** Endpoint `/v2/company/report/{symbol}/` memotong kuota 1 kredit per section. Selalu sertakan query param `?sections=overview,valuation,financials,peers` (menghabiskan 4 kredit, menghemat 4 kredit dibandingkan default 8 kredit).
  2. **Granular Symbol-Level Caching (Credit Saver Core):** Setiap panggilan data bursa tanpa cache memotong hingga 12 kredit. Karena cuitan berbeda kerap membicarakan emiten yang sama, sistem WAJIB meng-cache data Sectors API per symbol & endpoint:
     * `company_report:{symbol}`: TTL 24 jam (hemat 4 credits)
     * `quarterly_financials:{symbol}`: TTL 24 jam (hemat 4 credits)
     * `broker_summary:{symbol}`: TTL 30 menit (hemat 2 credits)
     * `foreign_flow:{symbol}`: TTL 30 menit (hemat 1 credit)
     * `suspensions:{symbol}`: TTL 2 jam (hemat 1 credit)
     * `tweet_verification:{role}:{hash}`: TTL 1 jam
  3. **Hybrid Engine Architecture:** Menggunakan Redis (`REDIS_URL`) untuk lingkungan container/production dan otomatis fallback tanpa error ke In-Memory `TTLCache` pada pengembangan lokal.
* 📱 **INVARIANT 6 (Arsitektur Android Tanpa Izin Bahaya):**  
  Hindari penggunaan `AccessibilityService` yang dilarang Google Play. Gunakan **Android `ACTION_PROCESS_TEXT` + Translucent BottomSheet Activity** (Nol izin berbahaya / *zero dangerous permission*).

---

## 4. PEMETAAN DATA & DIREKTORI (KNOWLEDGE MAP)

| Nama Berkas | Kategori | Fungsi & Kapan Agent Harus Membacanya |
| :--- | :--- | :--- |
| **[AGENTS.md](file:///E:/brainstorming/sector_hackathon/AGENTS.md)** | **Agent Rulebook** | Aturan mutlak sistem, invarian OJK, dan panduan target implementasi. |
| **[DOKUMENTASI_RESMI_SECTORS_API.md](file:///E:/brainstorming/sector_hackathon/DOKUMENTASI_RESMI_SECTORS_API.md)** | **Official API Spec** | **Spesifikasi resmi Sectors API v2:** Base URL, Auth header, endpoint paths, skema JSON, credit billing, & httpx client. |
| **[KONSEP_MASALAH_KEBUTUHAN_DAN_SOLUSI.md](file:///E:/brainstorming/sector_hackathon/KONSEP_MASALAH_KEBUTUHAN_DAN_SOLUSI.md)** | **Core Compass** | **Wajib Dibaca Pertama.** Penjelasan logika bisnis, psikologi FOMO, dan 4 pertanyaan kritis pengguna. |
| **[EXECUTIVE_SUMMARY_SCQA.md](file:///E:/brainstorming/sector_hackathon/EXECUTIVE_SUMMARY_SCQA.md)** | **Executive Pitch** | Rangkuman eksekutif framework SCQA, data statistik resmi (KSEI, OJK, BPS), dan analisis pasar. |
| **[PRD_BACKEND_LANGCHAIN_SECTORS.md](file:///E:/brainstorming/sector_hackathon/PRD_BACKEND_LANGCHAIN_SECTORS.md)** | **Backend PRD** | Spesifikasi lengkap Tilik AI Backend (v2.0.0): FastAPI, LangGraph, Slang RAG, Dual-Level Payload, Docker & venv. |
| **[PRD_FRONTEND_ANDROID_TILIK_AI.md](file:///E:/brainstorming/sector_hackathon/PRD_FRONTEND_ANDROID_TILIK_AI.md)** | **Frontend PRD** | Spesifikasi lengkap Klien Android: Material 3 ModalBottomSheet, ACTION_PROCESS_TEXT, Level 1 & Level 2 UI Components. |
| **[slang_dictionary.csv](file:///E:/brainstorming/sector_hackathon/slang_dictionary.csv)** | **RAG Database** | Database 52 baris kamus slang pasar modal IDX siap di-ingest ke vector store ChromaDB/FAISS. |
| **[DATASET_SLANG_SAHAM_INDONESIA.md](file:///E:/brainstorming/sector_hackathon/DATASET_SLANG_SAHAM_INDONESIA.md)** | **NLP Lexicon** | Kamus slang bursa: julukan emiten ("si ijo" -> GOTO), kode broker (YP/PD vs AK/BK), dan frasa pom-pom. |
| **[preview_floating_card.html](file:///E:/brainstorming/sector_hackathon/preview_floating_card.html)** | **UI Simulator** | Mockup interaktif antarmuka kartu melayang Android (bisa dibuka langsung di browser). |
| **[analisis/](file:///E:/brainstorming/sector_hackathon/analisis/)** | **Research Vault** | Berisi dokumen riset mendalam: validasi akar masalah 5-Whys, benchmarking kompetitor global/lokal, dan evaluasi OS Android. |
| **[referensi/](file:///E:/brainstorming/sector_hackathon/referensi/)** | **Academic Vault** | Berisi 3 jurnal ilmiah terakreditasi mengenai dampak FOMO dan finfluencer pada investor ritel. |

---

## 5. INSTRUKSI TEKNIS IMPLEMENTASI REPOSITORI `E:\tilik-ai`
Saat mengimplementasikan kode di `E:\tilik-ai`:
1. Salin `slang_dictionary.csv` ke dalam `E:\tilik-ai\data\slang_dictionary.csv`.
2. Gunakan `gemini-3.1-flash-lite` dengan smart fallback cascade ke `gemini-3.1-flash-lite-preview` / `gemini-2.5-flash`.
3. Terapkan multi-tier caching (Redis + In-Memory TTLCache) pada level respons verifikasi cuitan dan level fundamental emiten Sectors API guna memangkas konsumsi kredit bursa hingga 95%.
4. Pastikan berkas `README.md` pada repositori kode backend **HANYA** memuat bab:
   - **1. Pengertian**
   - **2. Cara Install & Menjalankan (venv & Docker)**
