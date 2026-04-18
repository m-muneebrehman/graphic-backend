"""
Face detection, encoding, and matching service.

Uses the ``face_recognition`` library (dlib) to produce 128-dimensional
embeddings and pgvector for cosine-similarity search.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import face_recognition
import numpy as np

from app.config import settings


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FaceData:
    """One detected face in an image."""
    encoding: np.ndarray          # 128-d float64
    bbox: tuple[int, int, int, int]  # (top, right, bottom, left) — dlib format


@dataclass
class MatchResult:
    """Result of comparing a face against the database."""
    grab_id: uuid.UUID
    similarity: float  # 0-1, higher = more similar


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def detect_faces(image_path: str) -> list[FaceData]:
    """
    Load an image and return all detected faces with their 128-d encodings.

    Parameters
    ----------
    image_path : str
        Absolute or relative path to the image file.

    Returns
    -------
    list[FaceData]
        One entry per face found in the image.
    """
    image = face_recognition.load_image_file(image_path)
    locations = face_recognition.face_locations(image, model="hog")

    if not locations:
        return []

    encodings = face_recognition.face_encodings(
        image,
        known_face_locations=locations,
        num_jitters=1,
    )

    return [
        FaceData(encoding=enc, bbox=loc)
        for enc, loc in zip(encodings, locations)
    ]


def detect_faces_from_bytes(image_bytes: bytes) -> list[FaceData]:
    """
    Same as ``detect_faces`` but accepts raw bytes (e.g. from an upload).
    """
    import io
    from PIL import Image

    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_array = np.array(pil_image)

    locations = face_recognition.face_locations(image_array, model="hog")
    if not locations:
        return []

    encodings = face_recognition.face_encodings(
        image_array,
        known_face_locations=locations,
        num_jitters=1,
    )

    return [
        FaceData(encoding=enc, bbox=loc)
        for enc, loc in zip(encodings, locations)
    ]


# ---------------------------------------------------------------------------
# Helpers — convert between numpy and pgvector literal
# ---------------------------------------------------------------------------

def _encoding_to_pg(encoding: np.ndarray) -> str:
    """Convert a 128-d numpy array to a pgvector literal string."""
    return "[" + ",".join(f"{v:.8f}" for v in encoding) + "]"


def _pg_to_encoding(pg_str: str) -> np.ndarray:
    """Convert a pgvector literal string back to a numpy array."""
    clean = pg_str.strip("[]")
    return np.array([float(x) for x in clean.split(",")], dtype=np.float64)


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

def find_or_create_face(encoding: np.ndarray, conn) -> tuple[uuid.UUID, bool]:
    """
    Search for an existing face matching *encoding*.  If found, return its
    ``grab_id``; otherwise insert a new row and return the new id.

    Parameters
    ----------
    encoding : np.ndarray
        128-d face embedding.
    conn
        psycopg2 connection (caller manages the transaction).

    Returns
    -------
    (grab_id, is_new) : tuple[uuid.UUID, bool]
    """
    pg_vec = _encoding_to_pg(encoding)

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


def match_face(encoding: np.ndarray, conn) -> MatchResult | None:
    """
    Find the closest matching face in the database.

    Returns ``None`` if no face exceeds the similarity threshold.
    """
    pg_vec = _encoding_to_pg(encoding)

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
