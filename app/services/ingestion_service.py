"""
Storage crawler and image ingestion pipeline.

Walks the configured storage directory, detects faces in every image
using InsightFace, and persists the image→face mappings to the database.

Bounding-box convention (InsightFace)
-------------------------------------
``FaceData.bbox`` is ``(x1, y1, x2, y2)`` — top-left → bottom-right in
pixel coordinates.  Stored in the DB as
``(bbox_x=x1, bbox_y=y1, bbox_w=x2-x1, bbox_h=y2-y1)``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from app.config import settings
from app.services.face_service import FaceData, detect_faces, find_or_create_face


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class IngestStats:
    images_processed: int = 0
    images_skipped: int = 0
    faces_detected: int = 0
    new_faces_created: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Crawl
# ---------------------------------------------------------------------------

def crawl_storage(storage_path: str | None = None) -> list[Path]:
    """
    Recursively find all supported image files under *storage_path*.

    Returns a sorted list of ``Path`` objects.
    """
    root = Path(storage_path or settings.IMAGE_STORAGE_PATH).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Storage directory does not exist: {root}")

    images: list[Path] = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext in settings.SUPPORTED_EXTENSIONS:
                images.append(Path(dirpath) / fname)

    images.sort()
    return images


# ---------------------------------------------------------------------------
# Single-image ingestion
# ---------------------------------------------------------------------------

def _image_metadata(path: Path) -> dict:
    """Extract basic metadata from an image file."""
    stat = path.stat()
    try:
        with Image.open(path) as img:
            width, height = img.size
    except Exception:
        width, height = None, None

    return {
        "file_path": str(path),
        "file_name": path.name,
        "file_size": stat.st_size,
        "width": width,
        "height": height,
    }


def ingest_image(image_path: Path, conn) -> tuple[bool, int, int]:
    """
    Process a single image:

    1. Skip if already indexed.
    2. Insert image record.
    3. Detect faces and create/match ``grab_id`` entries.
    4. Insert ``image_faces`` rows.

    Returns
    -------
    (was_processed, faces_detected, new_faces) : tuple[bool, int, int]
        ``was_processed`` is False when the image was already in the DB.
    """
    meta = _image_metadata(image_path)

    with conn.cursor() as cur:
        # Check duplicate
        cur.execute(
            "SELECT image_id FROM images WHERE file_path = %s",
            (meta["file_path"],),
        )
        if cur.fetchone() is not None:
            return False, 0, 0  # already indexed

        # Insert image
        cur.execute(
            """
            INSERT INTO images (file_path, file_name, file_size, width, height)
            VALUES (%(file_path)s, %(file_name)s, %(file_size)s, %(width)s, %(height)s)
            RETURNING image_id
            """,
            meta,
        )
        image_id = cur.fetchone()[0]

    # Detect faces (outside cursor context to avoid long-held locks)
    faces = detect_faces(str(image_path))
    faces_detected = len(faces)
    new_faces = 0

    with conn.cursor() as cur:
        for face_data in faces:
            grab_id, is_new = find_or_create_face(face_data.embedding, conn)
            if is_new:
                new_faces += 1

            # InsightFace bbox is (x1, y1, x2, y2) — top-left → bottom-right
            x1, y1, x2, y2 = face_data.bbox
            cur.execute(
                """
                INSERT INTO image_faces (image_id, grab_id, bbox_x, bbox_y, bbox_w, bbox_h)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (image_id, grab_id) DO NOTHING
                """,
                (image_id, grab_id, x1, y1, x2 - x1, y2 - y1),
            )

    return True, faces_detected, new_faces


# ---------------------------------------------------------------------------
# Full ingestion run
# ---------------------------------------------------------------------------

def run_ingestion(storage_path: str | None = None, conn=None) -> IngestStats:
    """
    Crawl *storage_path* and ingest every image found.

    If *conn* is ``None``, a connection is obtained from the pool.
    """
    from app.database import get_db

    stats = IngestStats()
    image_files = crawl_storage(storage_path)

    def _process(db_conn):
        nonlocal stats
        for img_path in image_files:
            try:
                processed, n_faces, n_new = ingest_image(img_path, db_conn)
                if processed:
                    stats.images_processed += 1
                    stats.faces_detected += n_faces
                    stats.new_faces_created += n_new
                else:
                    stats.images_skipped += 1
                db_conn.commit()
            except Exception as exc:
                db_conn.rollback()
                stats.errors.append(f"{img_path.name}: {exc}")

    if conn is not None:
        _process(conn)
    else:
        with get_db() as db_conn:
            _process(db_conn)

    return stats
