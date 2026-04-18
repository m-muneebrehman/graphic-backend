# Grabpic — Intelligent Identity & Retrieval Engine

> High-performance image processing backend with facial recognition for automatic photo grouping and selfie-based retrieval.

Imagine a marathon with 500 runners and photographers taking 50,000 photos. Instead of manual tagging, **Grabpic** uses facial recognition to automatically group images by person and provides a secure **"Selfie-as-a-Key"** retrieval system.

---

## Architecture

```
┌────────────┐     ┌───────────────┐     ┌─────────────────────┐
│  ./storage │────▶│  Ingestion    │────▶│  PostgreSQL + pgvec │
│  (images)  │     │  Pipeline     │     │                     │
└────────────┘     │  • crawl      │     │  faces (128-d vec)  │
                   │  • detect     │     │  images             │
                   │  • encode     │     │  image_faces (M:N)  │
                   └───────────────┘     └──────────┬──────────┘
                                                    │
                   ┌───────────────┐                │
                   │  Selfie Auth  │◀───────────────┘
                   │  POST /selfie │     cosine similarity
                   │  → grab_id    │     search via HNSW
                   └───────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | FastAPI + Uvicorn |
| Face Recognition | `face_recognition` (dlib, 128-d embeddings) |
| Image Processing | OpenCV, Pillow |
| Database | PostgreSQL + `pgvector` (Supabase) |
| Testing | pytest |
| Docs | Swagger UI (auto at `/docs`) |

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL with `pgvector` extension (Supabase recommended)
- CMake + dlib build dependencies (for `face-recognition`)

### Setup

```bash
# 1. Clone and install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env with your database URL

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
| `FACE_MATCH_TOLERANCE` | `0.45` | Cosine similarity threshold (0-1) |

## API Reference

### Health Check
```bash
GET /health
# → {"status": "ok", "version": "0.1.0"}
```

### Ingest Images
```bash
POST /api/v1/ingest
# Crawl storage directory, detect faces, create grab_ids

curl -X POST http://localhost:8000/api/v1/ingest

# Response:
# {
#   "images_processed": 150,
#   "images_skipped": 0,
#   "faces_detected": 420,
#   "new_faces_created": 85,
#   "errors": []
# }
```

### Selfie Authentication
```bash
POST /api/v1/auth/selfie
Content-Type: multipart/form-data

curl -X POST -F "file=@my-selfie.jpg" http://localhost:8000/api/v1/auth/selfie

# Response:
# {
#   "matched": true,
#   "grab_id": "a1b2c3d4-...",
#   "confidence": 0.9234,
#   "message": "Identity verified successfully."
# }
```

### Retrieve Images
```bash
GET /api/v1/images/{grab_id}?page=1&per_page=20

curl http://localhost:8000/api/v1/images/a1b2c3d4-...

# Response:
# {
#   "grab_id": "a1b2c3d4-...",
#   "page": 1,
#   "per_page": 20,
#   "total": 12,
#   "images": [...]
# }
```

### Interactive Docs

Visit **http://localhost:8000/docs** for the full Swagger UI.

## Database Schema

```
faces (grab_id UUID PK, embedding vector(128), created_at)
  │
  ├──< image_faces (image_id FK, grab_id FK, bbox, confidence)
  │
images (image_id UUID PK, file_path, file_name, metadata, ingested_at)
```

- **faces**: One row per unique person discovered
- **images**: One row per ingested image file
- **image_faces**: Many-to-many junction (one image → many faces)

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_face_service.py -v

# Run with coverage
uv run pytest tests/ --cov=app -v
```

## Project Structure

```
graphic-backend/
├── app/
│   ├── config.py              # Settings from .env
│   ├── database.py            # Connection pool & migrations
│   ├── models.py              # Pydantic schemas
│   ├── services/
│   │   ├── face_service.py    # Detection, encoding, matching
│   │   └── ingestion_service.py  # Storage crawler + indexer
│   └── routes/
│       ├── ingest.py          # POST /api/v1/ingest
│       ├── auth.py            # POST /api/v1/auth/selfie
│       └── images.py          # GET /api/v1/images/{grab_id}
├── migrations/
│   └── 001_init.sql           # Schema DDL
├── tests/
│   ├── test_face_service.py
│   ├── test_ingest.py
│   └── test_api.py
├── storage/                   # Event images
├── main.py                    # App entrypoint
└── .env
```

## License

MIT
