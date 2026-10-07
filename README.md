# 🔍 Tilik AI — Backend Service

## 1. Pengertian

**Tilik AI** (berasal dari kata bahasa Jawa/Indonesia *"Tilik"*: melihat secara teliti, memeriksa kebenaran, menengok kondisi, atau menginspeksi fakta) adalah layanan backend cerdas (*in-context financial fact-checker*) berbasis **FastAPI**, **LangGraph**, **Google Gemini**, dan **Sectors API v2** yang bertugas menilik dan memvalidasi keabsahan cuitan serta narasi saham di media sosial Indonesia (X/Twitter, Threads, Telegram) secara real-time.

### Latar Belakang & Masalah
Investor ritel pemula di Indonesia menghadapi kesenjangan literasi pasar modal yang sangat curam (hanya 17,78% menurut survei OJK). Hambatan ini diperparah oleh:
1. **Manipulasi Pom-Pom & Desakan FOMO:** Finfluencer kerap melontarkan klaim spekulatif (*"barang salah harga"*, *"haka sekarang to the moon"*, *"diserok bandar YP"*) yang memicu aksi beli impulsif tanpa analisis dasar.
2. **Friksi Verifikasi Manual (15-Second Friction):** Mengakses laporan keuangan berkala ke RTI atau aplikasi sekuritas memerlukan banyak klik dan memakan waktu, sehingga investor ritel kalah cepat oleh dorongan dopamin sesaat.
3. **Bahasa Gaul & Eufemisme Bursa IDX:** Narasi pom-pom sengaja menyamarkan kode saham menggunakan istilah gaul (*"si ijo"*, *"saham paman"*, *"diserok asing"*), sehingga sulit dideteksi oleh mesin pencari standar.

### Solusi & Nilai Tambah Sistem
Tilik AI memotong transmisi disinformasi langsung di tempat kejadian pada perangkat pengguna dengan arsitektur **Single Unified Endpoint** (`POST /api/v1/verify`):
* **Dual-Level Output Payload:**
  * **Level 1 (Default Summary Card):** Mengembalikan status lampu lalu lintas (🔴 **HOAX / BAHAYA**, 🟡 **WASPADA**, 🟢 **SESUAI FAKTA**), tepat **1–3 poin fakta kunci** (maksimal 20–25 kata per poin), serta pesan panduan kontekstual (*cooling-off prompt* berupa catatan statis ramah pemula atau *Devil's Advocate prompt* penantang tesis untuk investor berpengalaman).
  * **Level 2 (Expanded Data — Zero Latency & Zero AI):** Rincian angka fundamental mendalam (valuasi PER/PBV vs median peers sektor, broker flow Top 5 institusi vs ritel, pertumbuhan laba bersih YoY, arus kas operasional/OCF, serta status suspensi/Papan FCA resmi BEI) yang langsung ter-bundle dalam field `details` sehingga pengguna dapat membuka data seketika tanpa loading tambahan.
* **Mesin Slang RAG Subsystem:** Mengindeks basis data kamus slang bursa (`data/slang_dictionary.csv`) ke dalam vector store lokal untuk mendeteksi entitas emiten, julukan gaul, dan frasa manipulasi bursa IDX secara semantik.
* **Multi-Tier Credit Optimization Cache:** Menerapkan caching berbasis SHA256 cuitan dan TTL granular per endpoint emiten Sectors API (Redis dengan automatic fallback ke In-Memory TTLCache) yang memangkas konsumsi kredit API bursa hingga 95%.
* **Kepatuhan Regulasi Mutlak (POJK No. 6/2026 & UU P2SK):** Sistem berposisi murni sebagai **Penyedia Informasi Fakta Objektif (*Factual Information Provider*)** dengan menyandingkan *Klaim Medsos vs Laporan Resmi IDX* serta klausul *Disclaimer On*. Sistem **DILARANG KERAS** memberikan rekomendasi investasi personal, sinyal transaksi beli/jual, menentukan target price, maupun mengeksekusi order perdagangan otomatis (*automated trade execution*).

---

## 2. Cara Install & Menjalankan (venv & Docker)

### Opsi A: Menjalankan via Virtual Environment (venv)

#### 1. Prasyarat Sistem
* Python 3.11 atau lebih baru
* Git & PowerShell / Bash

#### 2. Masuk ke Direktori Proyek
```bash
cd E:\tilik-ai
```

#### 3. Buat & Aktifkan Virtual Environment
* **Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
* **Windows (Command Prompt / CMD):**
  ```cmd
  python -m venv venv
  .\venv\Scripts\activate.bat
  ```
* **Linux / macOS / Git Bash:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

#### 4. Instalasi Dependensi
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 5. Siapkan Environment Variables
Salin berkas konfigurasi sampel dan sesuaikan kredensial API:
```bash
cp .env.example .env
```
Buka berkas `.env` dan lengkapi konfigurasi berikut:
* `GOOGLE_API_KEY`: Kunci API Google AI Studio / Gemini.
* `SECTORS_API_KEY`: Kunci API resmi Sectors v2 (`https://sectors.app`).
* `JWT_SECRET_KEY`: Kunci rahasia untuk penandatanganan token JWT sesi login.

#### 6. Jalankan Server Pengembangan (Uvicorn)
```bash
python -m uvicorn app.main:app --reload --port 8000
```
Server aktif di: `http://localhost:8000`  
Dokumentasi interaktif OpenAPI:
* **Swagger UI:** `http://localhost:8000/docs`
* **ReDoc:** `http://localhost:8000/redoc`

#### 7. Menjalankan Automated Test Suite
Pastikan seluruh 52 skenario pengujian unit dan integrasi lulus:
```bash
pytest
```

---

### Opsi B: Menjalankan via Docker & Docker Compose

#### 1. Prasyarat Sistem
* Docker Desktop atau Docker Engine
* Docker Compose v2

#### 2. Konfigurasi Environment Variables
Salin dan lengkapi berkas `.env`:
```bash
cp .env.example .env
```
Pastikan `GOOGLE_API_KEY` dan `SECTORS_API_KEY` telah terisi di dalam berkas `.env`.

#### 3. Build & Jalankan Kontainer di Latar Belakang
```bash
docker compose up -d --build
```
Perintah ini akan menyalakan kontainer service `app` (FastAPI) dan Redis cache secara otomatis.

#### 4. Verifikasi Kesehatan Layanan (Health Check)
Pastikan status service dan konektivitas upstream bernilai sehat:
```bash
curl http://localhost:8000/api/v1/health
```
Contoh respons JSON:
```json
{
  "status": "healthy",
  "app_name": "Tilik AI Backend",
  "version": "2.0.0",
  "gemini_api": "connected",
  "sectors_api": "connected",
  "slang_rag_records": 52,
  "cache_backend": "redis"
}
```

#### 5. Memantau Log Kontainer
```bash
docker compose logs -f app
```

#### 6. Menghentikan Layanan Kontainer
```bash
docker compose down
```
