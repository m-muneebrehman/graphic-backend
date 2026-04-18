"""
Face detection, encoding, and matching service.

Uses **InsightFace** (``buffalo_l`` model by default) to produce 512-dimensional
ArcFace embeddings and pgvector for cosine-similarity search.

Model notes
-----------
* Model pack   : configurable via ``settings.FACE_MODEL`` (default: ``buffalo_l``)
* Embedding dim: 512-d float32
* Bbox format  : [x1, y1, x2, y2]  (pixel coordinates, top-left → bottom-right)
* Similarity   : cosine similarity in pgvector (higher = more similar)
* Threshold    : ``settings.FACE_MATCH_TOLERANCE`` (default 0.45; consider 0.6–0.7
                 for production with ``buffalo_l``)
"""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from PIL import Image

from app.config import settings


# ---------------------------------------------------------------------------
# InsightFace model — loaded once and reused
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_model():
    """
    Lazy-load and cache the InsightFace FaceAnalysis model.

    The model is downloaded on first use (~300 MB for buffalo_l).
    ``ctx_id=-1`` forces CPU inference; change to 0 for GPU.
    """
    import insightface
    from insightface.app import FaceAnalysis

    fa = FaceAnalysis(
        name=settings.FACE_MODEL,
        providers=["CPUExecutionProvider"],
    )
    fa.prepare(ctx_id=-1, det_size=(640, 640))
    return fa


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FaceData:
    """One detected face in an image."""
    embedding: np.ndarray               # 512-d float32 (ArcFace)
    bbox: tuple[int, int, int, int]     # (x1, y1, x2, y2) — top-left → bottom-right


@dataclass
class MatchResult:
    """Result of comparing a face against the database."""
    grab_id: uuid.UUID
    similarity: float  # 0-1, higher = more similar


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def _pil_to_bgr(pil_image: Image.Image) -> np.ndarray:
    """Convert a PIL RGB image to a NumPy BGR array (InsightFace expects BGR)."""
    return np.array(pil_image.convert("RGB"))[:, :, ::-1]


def _run_detection(bgr_array: np.ndarray) -> list[FaceData]:
    """
    Run InsightFace detection + embedding on a BGR numpy array.

    Returns a list of :class:`FaceData`, one per detected face.
    """
    model = _get_model()
    faces = model.get(bgr_array)

    results: list[FaceData] = []
    for face in faces:
        if face.embedding is None:
            continue  # skip detections without an embedding

        x1, y1, x2, y2 = face.bbox.astype(int).tolist()
        results.append(
            FaceData(
                embedding=face.embedding.astype(np.float32),
                bbox=(x1, y1, x2, y2),
            )
        )
    return results


# ---------------------------------------------------------------------------
# Public detection API
# ---------------------------------------------------------------------------

def detect_faces(image_path: str) -> list[FaceData]:
    """
    Load an image from disk and return all detected faces with embeddings.

    Parameters
    ----------
    image_path : str
        Absolute or relative path to the image file.

    Returns
    -------
    list[FaceData]
        One entry per face found in the image.
    """
    pil_image = Image.open(image_path)
    bgr = _pil_to_bgr(pil_image)
    return _run_detection(bgr)


def detect_faces_from_bytes(image_bytes: bytes) -> list[FaceData]:
    """
    Same as :func:`detect_faces` but accepts raw bytes (e.g. from an upload).
    """
    pil_image = Image.open(io.BytesIO(image_bytes))
    bgr = _pil_to_bgr(pil_image)
    return _run_detection(bgr)


# ---------------------------------------------------------------------------
# Helpers — convert between numpy and pgvector literal
# ---------------------------------------------------------------------------

def _embedding_to_pg(embedding: np.ndarray) -> str:
    """Convert a 512-d numpy array to a pgvector literal string."""
    return "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"


def _pg_to_embedding(pg_str: str) -> np.ndarray:
    """Convert a pgvector literal string back to a numpy array."""
    clean = pg_str.strip("[]")
    return np.array([float(x) for x in clean.split(",")], dtype=np.float32)


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

def find_or_create_face(embedding: np.ndarray, conn) -> tuple[uuid.UUID, bool]:
    """
    Search for an existing face matching *embedding*.  If found, return its
    ``grab_id``; otherwise insert a new row and return the new id.

    Parameters
    ----------
    embedding : np.ndarray
        512-d ArcFace embedding.
    conn
        psycopg2 connection (caller manages the transaction).

    Returns
    -------
    (grab_id, is_new) : tuple[uuid.UUID, bool]
    """
    pg_vec = _embedding_to_pg(embedding)

    with conn.cursor() as cur:
        # Cosine similarity = 1 - cosine_distance
        cur.execute(
            """
            SELECT grab_id,
                   1 - (embedding <=> %s::vector) AS similarity
              FROM faces
             WHERE 1 - (embedding <=> %s::vector) > %s
             ORDER BY similarity DESC
             LIMIT 1
            """,
            (pg_vec, pg_vec, settings.FACE_MATCH_TOLERANCE),
        )
        row = cur.fetchone()

        if row is not None:
            return row[0], False  # existing face

        # No match — insert new face
        cur.execute(
            """
            INSERT INTO faces (embedding)
            VALUES (%s::vector)
            RETURNING grab_id
            """,
            (pg_vec,),
        )
        new_id = cur.fetchone()[0]
        return new_id, True


def match_face(embedding: np.ndarray, conn) -> MatchResult | None:
    """
    Find the closest matching face in the database.

    Returns ``None`` if no face exceeds the similarity threshold.
    """
    pg_vec = _embedding_to_pg(embedding)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT grab_id,
                   1 - (embedding <=> %s::vector) AS similarity
              FROM faces
             WHERE 1 - (embedding <=> %s::vector) > %s
             ORDER BY similarity DESC
             LIMIT 1
            """,
            (pg_vec, pg_vec, settings.FACE_MATCH_TOLERANCE),
        )
        row = cur.fetchone()

        if row is None:
            return None

        return MatchResult(grab_id=row[0], similarity=float(row[1]))
