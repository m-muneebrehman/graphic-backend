"""
Shared pytest fixtures for Grabpic tests.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """
    Create a FastAPI TestClient with the DB init mocked out
    so tests don't require a real database connection.
    """
    with patch("app.database.init_db"):
        from main import app
        with TestClient(app) as c:
            yield c


# ---------------------------------------------------------------------------
# Mock database connection
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_conn():
    """Return a mock psycopg2 connection with a mock cursor."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn


@pytest.fixture()
def mock_cursor(mock_conn):
    """Convenience: return the cursor from mock_conn."""
    return mock_conn.cursor.return_value.__enter__.return_value


# ---------------------------------------------------------------------------
# Temporary storage directory with sample images
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_storage(tmp_path):
    """
    Create a temporary storage directory with a simple test image.
    Returns the path to the directory.
    """
    from PIL import Image

    # Create a simple 100x100 red image
    img = Image.new("RGB", (100, 100), color="red")
    img_path = tmp_path / "test_image.jpg"
    img.save(str(img_path))

    return tmp_path
