"""
POST /api/v1/auth/selfie — Selfie-as-a-Key authentication.

Upload a selfie image to identify yourself and receive your `grab_id`.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.database import get_db
from app.models import AuthResponse
from app.services.face_service import detect_faces_from_bytes, match_face

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/selfie",
    response_model=AuthResponse,
    summary="Authenticate via selfie",
    description=(
        "Upload a photo of your face. The system extracts a facial encoding "
        "and searches the database for a matching `grab_id`. If found, "
        "the response includes the `grab_id` and a confidence score."
    ),
    responses={
        200: {"description": "Face matched or no match found"},
        400: {"description": "No face detected in the uploaded image"},
        422: {"description": "Invalid file upload"},
    },
)
async def selfie_auth(
    file: UploadFile = File(..., description="Selfie image (JPEG/PNG)"),
):
    """Authenticate a user by matching their selfie against known faces."""

    # Read the uploaded file
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    # Detect faces in the selfie
    faces = detect_faces_from_bytes(contents)
    if not faces:
        raise HTTPException(
            status_code=400,
            detail="No face detected in the uploaded image. Please upload a clear selfie.",
        )

    # Use the first (largest / most prominent) face
    encoding = faces[0].embedding

    # Search the database
    with get_db() as conn:
        result = match_face(encoding, conn)

    if result is None:
        return AuthResponse(
            matched=False,
            message="No matching identity found. You may not be in the system yet.",
        )

    return AuthResponse(
        matched=True,
        grab_id=result.grab_id,
        confidence=round(result.similarity, 4),
        message="Identity verified successfully.",
    )
