"""
Pydantic models for API request / response validation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

class IngestResponse(BaseModel):
    """Returned after a storage crawl + indexing run."""
    images_processed: int = Field(..., description="Total images scanned")
    images_skipped: int = Field(..., description="Images already indexed (duplicates)")
    faces_detected: int = Field(..., description="Total face detections across all images")
    new_faces_created: int = Field(..., description="Newly created unique grab_ids")
    errors: list[str] = Field(default_factory=list, description="Any per-image errors")


# ---------------------------------------------------------------------------
# Selfie Authentication
# ---------------------------------------------------------------------------

class AuthResponse(BaseModel):
    """Returned when a selfie is matched against the face database."""
    matched: bool
    grab_id: uuid.UUID | None = None
    confidence: float | None = Field(
        None, ge=0.0, le=1.0,
        description="Cosine similarity score (1.0 = identical)",
    )
    message: str = ""


# ---------------------------------------------------------------------------
# Image retrieval
# ---------------------------------------------------------------------------

class BoundingBox(BaseModel):
    x: int
    y: int
    w: int
    h: int


class FaceInImage(BaseModel):
    grab_id: uuid.UUID
    bbox: BoundingBox | None = None
    confidence: float | None = None


class ImageOut(BaseModel):
    image_id: uuid.UUID
    file_path: str
    file_name: str
    file_size: int | None = None
    width: int | None = None
    height: int | None = None
    ingested_at: datetime | None = None
    faces: list[FaceInImage] = Field(default_factory=list)


class PaginatedImages(BaseModel):
    grab_id: uuid.UUID
    page: int
    per_page: int
    total: int
    images: list[ImageOut]
