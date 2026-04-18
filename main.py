"""
Grabpic — Intelligent Identity & Retrieval Engine

High-performance image processing backend with facial recognition
for automatic photo grouping and selfie-based retrieval.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import close_pool, init_db
from app.models import HealthResponse
from app.routes import auth, images, ingest


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run DB migrations on startup; close pool on shutdown."""
    print("[grabpic] Initialising database …")
    init_db()
    print("[grabpic] Ready.")
    yield
    print("[grabpic] Shutting down …")
    close_pool()


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Grabpic API",
    description=(
        "Intelligent Identity & Retrieval Engine. "
        "Uses facial recognition to group event photos and provides "
        "a **Selfie-as-a-Key** retrieval system."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(ingest.router)
app.include_router(auth.router)
app.include_router(images.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check",
)
def health():
    """Return service health status."""
    return HealthResponse()
