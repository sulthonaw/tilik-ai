# Tilik AI 🚀

**Tilik AI** adalah platform backend berbasis AI Agent untuk analisis finansial, interaksi multimodal (voice/audio to text), dan intelijen pasar modal (IDX) yang ditenagai oleh Google Gemini, LangGraph, dan Sectors API.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11+ & FastAPI
- **AI Agent & Workflow**: LangGraph & LangChain
- **LLM & Audio**: Google Gemini (`gemini-2.0-flash` / Multimodal Audio)
- **Financial Data**: Sectors API (REST / MCP)
- **Database**: PostgreSQL 16
- **Testing & Quality**: Pytest, Ruff, Pre-commit
- **Container**: Docker & Docker Compose

---

## 🐳 Panduan Instalasi & Menjalankan dengan Docker

Ikuti langkah-langkah berikut untuk menginstal dan menjalankan Tilik AI versi development:

### 1. Prasyarat
Pastikan Anda telah menginstal perangkat lunak berikut pada sistem Anda:
- [Docker](https://www.docker.com/products/docker-desktop/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/) (v2.0+)
- [Git](https://git-scm.com/)

---

### 2. Clone Repository & Salin Konfigurasi Environment
Salin file `.env.example` menjadi `.env`:

```bash
# Windows (PowerShell / Command Prompt)
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Buka file `.env` dan lengkapi konfigurasi API Key:
```env
GEMINI_API_KEY=masukkan_api_key_gemini_anda
SECTORS_API_KEY=masukkan_api_key_sectors_anda
```

---

### 3. Build & Jalankan Container
Jalankan perintah berikut untuk mem-build image dan menyalakan container (FastAPI Dev Server & PostgreSQL):

```bash
docker compose up --build
```

Jika ingin menjalankan di latar belakang (*detached mode*):
```bash
docker compose up -d
```

---

### 4. Mengakses Aplikasi & Dokumentasi API

Setelah container berhasil berjalan, Anda dapat mengakses:

| Layanan | URL | Keterangan |
| :--- | :--- | :--- |
| **FastAPI Base API** | `http://localhost:8000` | Endpoint API |
| **Swagger UI Docs** | `http://localhost:8000/docs` | Dokumentasi interaktif OpenAPI |
| **ReDoc UI Docs** | `http://localhost:8000/redoc` | Dokumentasi alternatif |
| **PostgreSQL Database** | `localhost:5432` | Port database (User: `tilik_user`, DB: `tilik_db`) |

> 💡 **Fitur Hot-Reload**: Source code di-mount langsung ke dalam container dev (`Dockerfile.dev`), sehingga setiap perubahan kode akan otomatis me-reload server tanpa perlu rebuild container.

---

### 5. Perintah Docker yang Sering Digunakan

```bash
# Melihat log aplikasi secara realtime
docker compose logs -f app

# Menghentikan seluruh container
docker compose down

# Menghentikan container dan menghapus volume database
docker compose down -v

# Masuk ke terminal container aplikasi
docker compose exec app bash
```
