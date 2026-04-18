"""
POST /api/v1/ingest — Crawl storage and index all images.
"""

from fastapi import APIRouter, HTTPException, Query

from app.database import get_db
from app.models import IngestResponse
from app.services.ingestion_service import run_ingestion

router = APIRouter(prefix="/api/v1", tags=["Ingestion"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest images from storage",
    description=(
        "Crawl the configured storage directory (or an optional sub-path), "
        "detect faces in every image, assign unique `grab_id`s, and persist "
        "the image→face mappings."
    ),
)
def ingest_images(
    path: str | None = Query(
        None,
        description="Optional sub-path inside the storage directory to ingest.",
    ),
):
    """Trigger a full ingestion run."""
    try:
        with get_db() as conn:
            stats = run_ingestion(storage_path=path, conn=conn)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")

    return IngestResponse(
        images_processed=stats.images_processed,
        images_skipped=stats.images_skipped,
        faces_detected=stats.faces_detected,
        new_faces_created=stats.new_faces_created,
        errors=stats.errors,
    )
