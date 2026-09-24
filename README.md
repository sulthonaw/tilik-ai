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
