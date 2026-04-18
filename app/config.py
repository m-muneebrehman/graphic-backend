"""
Application configuration loaded from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class Settings:
    """Central configuration for the Grabpic application."""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/postgres",
    )

    # Storage
    IMAGE_STORAGE_PATH: str = os.getenv("IMAGE_STORAGE_PATH", "./storage")

    # Server
    PORT: int = int(os.getenv("PORT", "8000"))

    # Face recognition
    FACE_MODEL: str = os.getenv("FACE_MODEL", "buffalo_l")
    """
    InsightFace model pack name.  ``buffalo_l`` (default) is the highest-accuracy
    pack; ``buffalo_s`` is faster and lighter.  The model is downloaded on first
    use to ``~/.insightface/models/<name>/``.
    """

    FACE_MATCH_TOLERANCE: float = float(os.getenv("FACE_MATCH_TOLERANCE", "0.45"))
    """
    Cosine-similarity threshold (0–1).  A *higher* value means the faces must
    be more similar to be considered a match.

    Recommended values for InsightFace ``buffalo_l`` (512-d ArcFace embeddings):
    - 0.45  — permissive / good for demos (current default)
    - 0.60  — balanced for events with moderate crowd size
    - 0.70  — strict / recommended for high-security scenarios
    """

    # Supported image extensions
    SUPPORTED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


settings = Settings()
