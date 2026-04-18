"""
Unit tests for the face service.
"""

import uuid
import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from app.services.face_service import (
    _encoding_to_pg,
    _pg_to_encoding,
    FaceData,
    MatchResult,
    find_or_create_face,
    match_face,
)


# ---------------------------------------------------------------------------
# Encoding conversion helpers
# ---------------------------------------------------------------------------

class TestEncodingConversion:
    """Tests for pgvector ↔ numpy conversion helpers."""

    def test_encoding_to_pg_format(self):
        """Encoded string should be a bracketed, comma-separated list."""
        enc = np.array([0.1, 0.2, 0.3])
        result = _encoding_to_pg(enc)
        assert result.startswith("[")
        assert result.endswith("]")
        assert "0.10000000" in result

    def test_roundtrip_conversion(self):
        """Converting to pg and back should preserve values."""
        original = np.random.rand(128).astype(np.float64)
        pg_str = _encoding_to_pg(original)
        restored = _pg_to_encoding(pg_str)
        np.testing.assert_array_almost_equal(original, restored, decimal=6)

    def test_encoding_dimensionality(self):
        """128-d vectors should produce 128 comma-separated values."""
        enc = np.zeros(128)
        pg_str = _encoding_to_pg(enc)
        values = pg_str.strip("[]").split(",")
        assert len(values) == 128


# ---------------------------------------------------------------------------
# find_or_create_face
# ---------------------------------------------------------------------------

class TestFindOrCreateFace:
    """Tests for the find_or_create_face database operation."""

    def test_returns_existing_face_when_match_found(self):
        """When DB returns a matching face, should return its grab_id."""
        existing_id = uuid.uuid4()
        encoding = np.random.rand(128)

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # Simulate a matching face found
        cursor.fetchone.return_value = (existing_id, 0.92)

        grab_id, is_new = find_or_create_face(encoding, conn)

        assert grab_id == existing_id
        assert is_new is False

    def test_creates_new_face_when_no_match(self):
        """When no match is found, should insert and return new grab_id."""
        new_id = uuid.uuid4()
        encoding = np.random.rand(128)

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # First call: no match; second call: return new id
        cursor.fetchone.side_effect = [None, (new_id,)]

        grab_id, is_new = find_or_create_face(encoding, conn)

        assert grab_id == new_id
        assert is_new is True


# ---------------------------------------------------------------------------
# match_face
# ---------------------------------------------------------------------------

class TestMatchFace:
    """Tests for the selfie-matching operation."""

    def test_returns_match_result_when_found(self):
        """Should return a MatchResult with correct fields."""
        expected_id = uuid.uuid4()
        encoding = np.random.rand(128)

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = (expected_id, 0.87)

        result = match_face(encoding, conn)

        assert result is not None
        assert result.grab_id == expected_id
        assert result.similarity == 0.87

    def test_returns_none_when_no_match(self):
        """Should return None when no face exceeds threshold."""
        encoding = np.random.rand(128)

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = None

        result = match_face(encoding, conn)

        assert result is None


# ---------------------------------------------------------------------------
# FaceData structure
# ---------------------------------------------------------------------------

class TestFaceData:
    """Tests for the FaceData dataclass."""

    def test_face_data_creation(self):
        """FaceData should store encoding and bbox."""
        enc = np.random.rand(128)
        bbox = (10, 200, 150, 50)
        face = FaceData(encoding=enc, bbox=bbox)

        assert face.encoding.shape == (128,)
        assert face.bbox == (10, 200, 150, 50)
