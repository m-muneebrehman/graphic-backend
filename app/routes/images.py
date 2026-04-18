"""
GET /api/v1/images/{grab_id} — Retrieve images for a specific person.
"""

import uuid

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.database import get_db
from app.models import (
    BoundingBox,
    FaceInImage,
    ImageOut,
    PaginatedImages,
)

router = APIRouter(prefix="/api/v1", tags=["Images"])


@router.get(
    "/images/{grab_id}",
    response_model=PaginatedImages,
    summary="Get images for a person",
    description=(
        "Return all images in which the given `grab_id` appears. "
        "Results are paginated."
    ),
)
def get_images_by_grab_id(
    grab_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(
        settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description="Items per page",
    ),
):
    """Fetch paginated images for a specific grab_id."""
    offset = (page - 1) * per_page

    with get_db() as conn:
        with conn.cursor() as cur:
            # Verify the grab_id exists
            cur.execute("SELECT 1 FROM faces WHERE grab_id = %s", (grab_id,))
            if cur.fetchone() is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"No identity found with grab_id: {grab_id}",
                )

            # Count total matching images
            cur.execute(
                """
                SELECT COUNT(DISTINCT i.image_id)
                  FROM images i
                  JOIN image_faces if2 ON i.image_id = if2.image_id
                 WHERE if2.grab_id = %s
                """,
                (grab_id,),
            )
            total = cur.fetchone()[0]

            # Fetch paginated images with face data
            cur.execute(
                """
                SELECT i.image_id, i.file_path, i.file_name,
                       i.file_size, i.width, i.height, i.ingested_at,
                       if2.grab_id  AS face_grab_id,
                       if2.bbox_x, if2.bbox_y, if2.bbox_w, if2.bbox_h,
                       if2.confidence
                  FROM images i
                  JOIN image_faces if2 ON i.image_id = if2.image_id
                 WHERE i.image_id IN (
                       SELECT DISTINCT i2.image_id
                         FROM images i2
                         JOIN image_faces if3 ON i2.image_id = if3.image_id
                        WHERE if3.grab_id = %s
                        ORDER BY i2.image_id
                       OFFSET %s LIMIT %s
                       )
                 ORDER BY i.ingested_at DESC, i.image_id
                """,
                (grab_id, offset, per_page),
            )
            rows = cur.fetchall()

    # Group rows by image
    images_map: dict[uuid.UUID, ImageOut] = {}
    for row in rows:
        img_id = row[0]
        if img_id not in images_map:
            images_map[img_id] = ImageOut(
                image_id=img_id,
                file_path=row[1],
                file_name=row[2],
                file_size=row[3],
                width=row[4],
                height=row[5],
                ingested_at=row[6],
                faces=[],
            )

        bbox = None
        if row[8] is not None:
            bbox = BoundingBox(x=row[8], y=row[9], w=row[10], h=row[11])

        images_map[img_id].faces.append(
            FaceInImage(
                grab_id=row[7],
                bbox=bbox,
                confidence=row[12],
            )
        )

    return PaginatedImages(
        grab_id=grab_id,
        page=page,
        per_page=per_page,
        total=total,
        images=list(images_map.values()),
    )
