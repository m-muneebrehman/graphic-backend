"""
Unit tests for the ingestion service.
"""

import os
from pathlib import Path

import pytest
from PIL import Image

from app.services.ingestion_service import crawl_storage, IngestStats
from app.config import settings


# ---------------------------------------------------------------------------
# crawl_storage
# ---------------------------------------------------------------------------

class TestCrawlStorage:
    """Tests for the storage crawler."""

    def test_finds_supported_images(self, tmp_path):
        """Should find jpg, png, webp files."""
        (tmp_path / "photo1.jpg").write_bytes(b"\xff\xd8\xff")
        (tmp_path / "photo2.png").write_bytes(b"\x89PNG")
        (tmp_path / "photo3.webp").write_bytes(b"RIFF")
        (tmp_path / "document.pdf").write_bytes(b"%PDF")
        (tmp_path / "notes.txt").write_text("hello")

        results = crawl_storage(str(tmp_path))
        names = {p.name for p in results}

        assert "photo1.jpg" in names
        assert "photo2.png" in names
        assert "photo3.webp" in names
        assert "document.pdf" not in names
        assert "notes.txt" not in names

    def test_recursive_crawl(self, tmp_path):
        """Should find images in subdirectories."""
        sub = tmp_path / "event1" / "batch2"
        sub.mkdir(parents=True)
        (sub / "deep_photo.jpg").write_bytes(b"\xff\xd8\xff")

        results = crawl_storage(str(tmp_path))
        names = {p.name for p in results}

        assert "deep_photo.jpg" in names

    def test_empty_directory(self, tmp_path):
        """Should return empty list for a directory with no images."""
        results = crawl_storage(str(tmp_path))
        assert results == []

    def test_nonexistent_directory_raises(self):
        """Should raise FileNotFoundError for missing directory."""
        with pytest.raises(FileNotFoundError):
            crawl_storage("/nonexistent/path/that/does/not/exist")

    def test_returns_sorted_paths(self, tmp_path):
        """Results should be sorted alphabetically."""
        (tmp_path / "c.jpg").write_bytes(b"\xff\xd8\xff")
        (tmp_path / "a.jpg").write_bytes(b"\xff\xd8\xff")
        (tmp_path / "b.jpg").write_bytes(b"\xff\xd8\xff")

        results = crawl_storage(str(tmp_path))
        names = [p.name for p in results]

        assert names == ["a.jpg", "b.jpg", "c.jpg"]


# ---------------------------------------------------------------------------
# IngestStats
# ---------------------------------------------------------------------------

class TestIngestStats:
    """Tests for the IngestStats data structure."""

    def test_default_values(self):
        """All counters should default to zero."""
        stats = IngestStats()
        assert stats.images_processed == 0
        assert stats.images_skipped == 0
        assert stats.faces_detected == 0
        assert stats.new_faces_created == 0
        assert stats.errors == []

    def test_accumulation(self):
        """Stats should be mutable for accumulation."""
        stats = IngestStats()
        stats.images_processed += 5
        stats.faces_detected += 12
        stats.new_faces_created += 3
        stats.errors.append("bad_image.jpg: corrupt")

        assert stats.images_processed == 5
        assert stats.faces_detected == 12
        assert stats.new_faces_created == 3
        assert len(stats.errors) == 1
