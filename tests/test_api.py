"""
Integration tests for the Grabpic API endpoints.
"""

import uuid
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


# ---------------------------------------------------------------------------
# Ingest endpoint
# ---------------------------------------------------------------------------

class TestIngestEndpoint:
    """Tests for POST /api/v1/ingest."""

    @patch("app.routes.ingest.get_db")
    @patch("app.routes.ingest.run_ingestion")
    def test_ingest_success(self, mock_run, mock_db, client):
        """Successful ingestion should return stats."""
        from app.services.ingestion_service import IngestStats

        mock_conn = MagicMock()
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_run.return_value = IngestStats(
            images_processed=10,
            images_skipped=2,
            faces_detected=25,
            new_faces_created=8,
        )

        resp = client.post("/api/v1/ingest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["images_processed"] == 10
        assert data["faces_detected"] == 25
        assert data["new_faces_created"] == 8

    @patch("app.routes.ingest.get_db")
    @patch("app.routes.ingest.run_ingestion")
    def test_ingest_not_found(self, mock_run, mock_db, client):
        """Should return 404 when storage path doesn't exist."""
        mock_conn = MagicMock()
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_run.side_effect = FileNotFoundError("Storage not found")

        resp = client.post("/api/v1/ingest")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth endpoint
# ---------------------------------------------------------------------------

class TestAuthEndpoint:
    """Tests for POST /api/v1/auth/selfie."""

    @patch("app.routes.auth.get_db")
    @patch("app.routes.auth.match_face")
    @patch("app.routes.auth.detect_faces_from_bytes")
    def test_selfie_auth_match(self, mock_detect, mock_match, mock_db, client):
        """Should return grab_id when face matches."""
        from app.services.face_service import FaceData, MatchResult

        test_id = uuid.uuid4()
        mock_detect.return_value = [
            FaceData(encoding=np.random.rand(128), bbox=(10, 100, 100, 10))
        ]
        mock_conn = MagicMock()
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_match.return_value = MatchResult(grab_id=test_id, similarity=0.92)

        # Upload a minimal JPEG-like file
        resp = client.post(
            "/api/v1/auth/selfie",
            files={"file": ("selfie.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["matched"] is True
        assert data["grab_id"] == str(test_id)
        assert data["confidence"] == 0.92

    @patch("app.routes.auth.detect_faces_from_bytes")
    def test_selfie_no_face_detected(self, mock_detect, client):
        """Should return 400 when no face is found in the upload."""
        mock_detect.return_value = []

        resp = client.post(
            "/api/v1/auth/selfie",
            files={"file": ("selfie.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
        )

        assert resp.status_code == 400
        assert "No face detected" in resp.json()["detail"]

    @patch("app.routes.auth.get_db")
    @patch("app.routes.auth.match_face")
    @patch("app.routes.auth.detect_faces_from_bytes")
    def test_selfie_no_match(self, mock_detect, mock_match, mock_db, client):
        """Should return matched=false when face doesn't match any grab_id."""
        from app.services.face_service import FaceData

        mock_detect.return_value = [
            FaceData(encoding=np.random.rand(128), bbox=(10, 100, 100, 10))
        ]
        mock_conn = MagicMock()
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_match.return_value = None

        resp = client.post(
            "/api/v1/auth/selfie",
            files={"file": ("selfie.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["matched"] is False
        assert data["grab_id"] is None


# ---------------------------------------------------------------------------
# Images endpoint
# ---------------------------------------------------------------------------

class TestImagesEndpoint:
    """Tests for GET /api/v1/images/{grab_id}."""

    @patch("app.routes.images.get_db")
    def test_images_not_found(self, mock_db, client):
        """Should return 404 for unknown grab_id."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_cursor.fetchone.return_value = None  # grab_id not found

        fake_id = uuid.uuid4()
        resp = client.get(f"/api/v1/images/{fake_id}")
        assert resp.status_code == 404

    @patch("app.routes.images.get_db")
    def test_images_returns_paginated(self, mock_db, client):
        """Should return paginated image list for a valid grab_id."""
        test_grab_id = uuid.uuid4()
        test_image_id = uuid.uuid4()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        # First call: grab_id exists; second call: count; third call: rows
        mock_cursor.fetchone.side_effect = [
            (1,),   # grab_id exists
            (1,),   # total count
        ]
        mock_cursor.fetchall.return_value = [
            (
                test_image_id, "/storage/img1.jpg", "img1.jpg",
                50000, 1920, 1080, "2026-01-01T00:00:00+00:00",
                test_grab_id, 10, 20, 100, 120, 0.95,
            ),
        ]

        resp = client.get(f"/api/v1/images/{test_grab_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["grab_id"] == str(test_grab_id)
        assert data["total"] == 1
        assert len(data["images"]) == 1
        assert data["images"][0]["file_name"] == "img1.jpg"
