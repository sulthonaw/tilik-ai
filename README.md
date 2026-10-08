![Tilik AI Banner](banner.png)

# Tilik AI — Backend Service

## 1. Pengertian

**Tilik AI** adalah layanan backend pemeriksa fakta keuangan (*in-context financial fact-checker*) untuk memvalidasi narasi atau klaim saham di media sosial (seperti X, Threads, dan Telegram) secara langsung menggunakan data resmi pasar modal dari **Sectors API v2** dan **Google Gemini**.

### Cara Kerja Singkat
1. **Deteksi Entitas & Istilah Pasar:** Menganalisis teks klaim dan mencocokkan kode saham serta istilah gaul bursa menggunakan kamus data (*Slang RAG*).
2. **Validasi Data Resmi:** Mengambil data fundamental, valuasi relatif (*peers*), arus broker (*broker flow*), aliran dana asing (*foreign flow*), serta status suspensi/Papan Pemantauan Khusus (FCA) dari Sectors API v2.
3. **Hasil Verifikasi Berjenjang:**
   - **Level 1 (Ringkasan):** Label verifikasi (Sesuai Fakta, Waspada, atau Berisiko/Tidak Sesuai) disertai 1–3 poin fakta kunci dan catatan pertimbangan objektif.
   - **Level 2 (Data Lengkap):** Rincian angka fundamental dan transaksi dari BEI/Sectors API bagi pengguna yang membutuhkan data lebih mendalam.

> **Catatan Regulasi:** Tilik AI murni menyajikan informasi dan data fakta objektif. Sistem tidak memberikan rekomendasi investasi, sinyal beli/jual, target harga, maupun eksekusi transaksi otomatis (*Disclaimer On*).

---

## 2. Cara Install & Menjalankan (venv & Docker)

### A. Menjalankan via Virtual Environment (venv)

#### 1. Prasyarat
* Python 3.11 atau lebih baru
* Git

#### 2. Masuk ke Direktori Proyek
```bash
cd E:\tilik-ai
```

#### 3. Buat dan Aktifkan Virtual Environment
* **Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
* **Windows (Command Prompt):**
  ```cmd
  python -m venv venv
  .\venv\Scripts\activate.bat
  ```
* **Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

#### 4. Pasang Dependensi
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 5. Konfigurasi Environment Variables
Salin berkas `.env.example` ke `.env`:
```bash
cp .env.example .env
```
Lengkapi konfigurasi berikut:
* `GOOGLE_API_KEY`: Kunci API Google AI Studio (Gemini).
* `SECTORS_API_KEY`: Kunci API Sectors v2 (`https://sectors.app`).
* `JWT_SECRET_KEY`: Kunci rahasia untuk penandatanganan token sesi.

#### 6. Jalankan Server Aplikasi
```bash
python -m uvicorn app.main:app --reload --port 8000
```
Layanan akan berjalan di `http://localhost:8000`.  
Dokumentasi interaktif dapat diakses di:
* Swagger UI: `http://localhost:8000/docs`
* ReDoc: `http://localhost:8000/redoc`

#### 7. Menjalankan Pengujian (Opsional)
```bash
pytest
```

---

### B. Menjalankan via Docker & Docker Compose

#### 1. Prasyarat
* Docker Desktop / Docker Engine
* Docker Compose v2

#### 2. Konfigurasi Environment Variables
Pastikan berkas `.env` sudah dibuat dan disesuaikan:
```bash
cp .env.example .env
```

#### 3. Build & Jalankan Kontainer
```bash
docker compose up -d --build
```

#### 4. Cek Status Layanan (Health Check)
```bash
curl http://localhost:8000/api/v1/health
```

#### 5. Melihat Log Kontainer
```bash
docker compose logs -f app
```

#### 6. Menghentikan Layanan Kontainer
```bash
docker compose down
```
