# Grabpic — Intelligent Identity & Retrieval Engine

> High-performance image processing backend with facial recognition for automatic photo grouping and selfie-based retrieval.

Imagine a marathon with 500 runners and photographers taking 50,000 photos. Instead of manual tagging, **Grabpic** uses facial recognition to automatically group images by person and provides a secure **"Selfie-as-a-Key"** retrieval system.

📄 **See [SDD.md](./SDD.md) for architecture, data models, and request flows.**  
📡 **See [API.md](./API.md) for the full endpoint reference with request/response examples.**

---

## ⚡ Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | FastAPI + Uvicorn |
| Face Recognition | InsightFace `buffalo_l` (512-d ArcFace embeddings) |
| Image Processing | OpenCV, Pillow |
| Database | PostgreSQL + `pgvector` (Supabase recommended) |
| Testing | pytest |
| Docs | Swagger UI (auto at `/docs`) |

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL with `pgvector` extension (Supabase has this enabled by default)

> **Note:** InsightFace uses ONNX Runtime for CPU inference — no CMake, no dlib compilation required. The model weights (~300 MB for `buffalo_l`) are downloaded automatically on first run to `~/.insightface/models/`.

### Setup

```bash
# 1. Clone and install dependencies
uv sync

# 2. Configure environment
cp .env .env.local   # or edit .env directly with your credentials

# 3. Place images in the storage directory
cp your-event-photos/* ./storage/

# 4. Start the server (runs migrations automatically)
uv run uvicorn main:app --reload --port 8000
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `IMAGE_STORAGE_PATH` | `./storage` | Directory containing event images |
| `PORT` | `8000` | Server port |
| `FACE_MODEL` | `buffalo_l` | InsightFace model pack (`buffalo_l` = high accuracy, `buffalo_s` = faster) |
| `FACE_MATCH_TOLERANCE` | `0.45` | Cosine similarity threshold (0–1). See table below. |

#### Threshold Guide for InsightFace `buffalo_l`

| `FACE_MATCH_TOLERANCE` | Use Case |
|---|---|
| `0.45` | Permissive — demos, small events (default) |
| `0.60` | Balanced — medium-sized events |
| `0.70` | Strict — high-security or large crowds |

## 📡 API Reference

### Health Check
```bash
GET /health
# → {"status": "ok", "version": "0.1.0"}
```

### Ingest Images
```bash
POST /api/v1/ingest
```
Crawls the configured `IMAGE_STORAGE_PATH` directory, detects faces using InsightFace, indexes 512-d ArcFace embeddings, and creates unique `grab_id` mappings.
- **Returns:** JSON object summarizing processed files, duplicates skipped, and errors.

### Selfie Authentication
```bash
POST /api/v1/auth/selfie
Content-Type: multipart/form-data
```
Upload a selfie image containing a single face to be cross-matched against the database.
- **Returns:** A JSON object containing the matched `grab_id` and confidence score.

### Retrieve Images
```bash
GET /api/v1/images/{grab_id}?page=1&per_page=20
```
Fetch paginated event images known to contain the requested user.
- **Returns:** JSON with image list and bounding boxes indicating where the user appears.

### Interactive Docs

Visit **http://localhost:8000/docs** or **http://localhost:8000/redoc** while running locally for the full interactive Swagger UI.

## 🗃️ Database Migrations

Migrations run **automatically on startup**. SQL files in `migrations/` are applied in order:

| File | Description |
|---|---|
| `001_init.sql` | Creates tables, enables pgvector, adds HNSW index |
| `002_resize_embedding.sql` | Resizes embedding column `vector(128)` → `vector(512)` for InsightFace |

> **⚠️ Upgrading from dlib/face_recognition?** Run `002_resize_embedding.sql` against your database and re-ingest all images — old 128-d embeddings are incompatible with InsightFace 512-d embeddings.

## 🧪 Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=app -v
```

## 📂 Project Structure

```
graphic-backend/
├── app/
│   ├── config.py              # Settings loaded from .env (FACE_MODEL, tolerances, etc.)
│   ├── database.py            # Connection pool + auto-migration runner
│   ├── models.py              # Pydantic schemas for API request/response
│   ├── services/
│   │   ├── face_service.py    # InsightFace detection, 512-d ArcFace encoding, vector matching
│   │   └── ingestion_service.py # Storage crawler + relational indexing
│   └── routes/
│       ├── ingest.py          # POST /api/v1/ingest
│       ├── auth.py            # POST /api/v1/auth/selfie
│       └── images.py          # GET /api/v1/images/{grab_id}
├── migrations/
│   ├── 001_init.sql           # Schema, pgvector, HNSW index
│   └── 002_resize_embedding.sql  # 128-d → 512-d embedding resize
├── tests/
├── storage/                   # Default image mount point
├── SDD.md                     # Software Design Document
├── main.py                    # FastAPI app entrypoint
└── .env                       # Local environment secrets
```

## License

MIT
