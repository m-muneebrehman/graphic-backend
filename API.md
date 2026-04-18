# Grabpic API — Full Reference Documentation

> **Base URL:** `http://localhost:8000` (development) · `https://your-domain.com` (production)  
> **API Version:** `v1`  
> **Content Format:** All responses are `application/json` unless noted otherwise.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication Model](#authentication-model)
3. [Common Data Types](#common-data-types)
4. [Error Handling](#error-handling)
5. [Endpoints](#endpoints)
   - [GET /health](#get-health)
   - [POST /api/v1/ingest](#post-apiv1ingest)
   - [POST /api/v1/auth/selfie](#post-apiv1authselfie)
   - [GET /api/v1/images/{grab_id}](#get-apiv1imagesgrab_id)
6. [End-to-End Usage Workflows](#end-to-end-usage-workflows)
7. [Client Examples](#client-examples)
8. [Rate Limits & Operational Notes](#rate-limits--operational-notes)

---

## Overview

Grabpic is an intelligent facial identity and image retrieval engine designed for large-scale event photography. It provides three core capabilities:

| Capability | Description |
|---|---|
| **Ingestion** | Crawl a storage directory, detect all faces, and index them into the database |
| **Authentication** | Identify a person by uploading a selfie — no usernames or passwords required |
| **Retrieval** | Fetch all event photos in which a given person appears, with face positions |

### How It Works

```
┌──────────────────────────────────────────────────────────────┐
│  STEP 1 — Ingest                                             │
│                                                              │
│  Upload photos to ./storage/                                 │
│  POST /api/v1/ingest                                         │
│    → InsightFace detects faces                               │
│    → 512-d ArcFace embeddings stored in pgvector DB          │
│    → Each unique person gets a UUID "grab_id"                │
│                                                              │
│  STEP 2 — Authenticate                                       │
│                                                              │
│  POST /api/v1/auth/selfie  (upload selfie.jpg)               │
│    → Face detected and embedded                              │
│    → Compared against all indexed faces via cosine search    │
│    → Returns grab_id + confidence score                      │
│                                                              │
│  STEP 3 — Retrieve                                           │
│                                                              │
│  GET /api/v1/images/{grab_id}                                │
│    → Returns paginated list of all photos featuring the user │
│    → Includes bounding box coordinates for each face         │
└──────────────────────────────────────────────────────────────┘
```

---

## Authentication Model

Grabpic uses a **stateless, selfie-based identity system**. There are no user accounts, passwords, or session tokens.

1. A person's face is indexed during the ingestion phase and assigned a permanent `grab_id` (UUID v4).
2. At retrieval time, the user uploads a selfie. The system matches their face against the database and returns the corresponding `grab_id`.
3. The `grab_id` is then used as a lookup key for the images endpoint.

> The system does **not** issue JWT tokens or OAuth credentials. For production deployments requiring access control, wrap the API behind an authentication gateway.

---

## Common Data Types

### `grab_id`
A UUID v4 string uniquely identifying one person across all indexed images.

```
"grab_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
```

### `BoundingBox`
Pixel coordinates of a detected face within an image.

| Field | Type | Description |
|---|---|---|
| `x` | `integer` | Left edge of bounding box (in pixels) |
| `y` | `integer` | Top edge of bounding box (in pixels) |
| `w` | `integer` | Width of bounding box (in pixels) |
| `h` | `integer` | Height of bounding box (in pixels) |

The region of interest can be cropped using: `image[y : y+h, x : x+w]`

### `FaceInImage`
A face instance within a specific image.

| Field | Type | Description |
|---|---|---|
| `grab_id` | `UUID` | Identity this face belongs to |
| `bbox` | `BoundingBox \| null` | Face bounding box (null if not stored) |
| `confidence` | `float \| null` | Cosine similarity score when this face was matched |

### `ImageOut`
Full metadata for one event photo.

| Field | Type | Description |
|---|---|---|
| `image_id` | `UUID` | Unique identifier for this image in the database |
| `file_path` | `string` | Absolute server-side filesystem path |
| `file_name` | `string` | Original filename |
| `file_size` | `integer \| null` | File size in bytes |
| `width` | `integer \| null` | Image width in pixels |
| `height` | `integer \| null` | Image height in pixels |
| `ingested_at` | `datetime \| null` | ISO 8601 UTC timestamp of when the image was indexed |
| `faces` | `FaceInImage[]` | All faces detected in this image (not just the queried one) |

---

## Error Handling

All errors follow a consistent JSON envelope:

```json
{
  "detail": "Human-readable error description"
}
```

### HTTP Status Codes

| Code | Meaning | When It Occurs |
|---|---|---|
| `200 OK` | Success | Request processed successfully |
| `400 Bad Request` | Client error | Empty file, no face detected in selfie |
| `404 Not Found` | Resource missing | `grab_id` does not exist; storage path not found |
| `422 Unprocessable Entity` | Validation error | Malformed query params, invalid UUID format, missing required fields |
| `500 Internal Server Error` | Server error | Unexpected ingestion failure, DB connection failure |

### Example Error Responses

**400 — No face in selfie:**
```json
{
  "detail": "No face detected in the uploaded image. Please upload a clear selfie."
}
```

**404 — Unknown grab_id:**
```json
{
  "detail": "No identity found with grab_id: 3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

**404 — Storage path missing:**
```json
{
  "detail": "Storage directory does not exist: /app/storage/event-2026"
}
```

**422 — Invalid UUID in path:**
```json
{
  "detail": [
    {
      "loc": ["path", "grab_id"],
      "msg": "value is not a valid uuid",
      "type": "type_error.uuid"
    }
  ]
}
```

---

## Endpoints

---

### GET /health

Check whether the service is running and responsive.

**Use case:** Load balancer health probes, uptime monitoring, deployment readiness checks.

#### Request

```http
GET /health HTTP/1.1
Host: localhost:8000
```

No parameters required.

#### Response `200 OK`

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | `string` | Always `"ok"` if the server is running |
| `version` | `string` | Current API version |

#### Examples

```bash
# cURL
curl http://localhost:8000/health

# Expected output
{"status":"ok","version":"0.1.0"}
```

```python
# Python (requests)
import requests

resp = requests.get("http://localhost:8000/health")
print(resp.json())  # {'status': 'ok', 'version': '0.1.0'}
```

---

### POST /api/v1/ingest

Crawl the configured storage directory (or a sub-path), detect all faces in every image using InsightFace, assign unique `grab_id`s, and persist the image-to-face mappings.

> **When to call this:** Run once after placing event photos in the `./storage/` directory. Re-run incrementally — already-indexed images are automatically skipped (deduplication by file path).

#### Request

```http
POST /api/v1/ingest HTTP/1.1
Host: localhost:8000
Content-Type: application/json
```

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `path` | `string` | No | `IMAGE_STORAGE_PATH` from `.env` | Optional sub-path inside the storage directory. Useful when ingesting a specific event subfolder. |

**Examples:**
```
POST /api/v1/ingest                          # Ingest everything in ./storage/
POST /api/v1/ingest?path=./storage/marathon  # Ingest only the marathon subfolder
```

#### Response `200 OK`

```json
{
  "images_processed": 342,
  "images_skipped": 12,
  "faces_detected": 1087,
  "new_faces_created": 215,
  "errors": [
    "corrupted_photo.jpg: cannot identify image file"
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `images_processed` | `integer` | Number of images successfully scanned and indexed this run |
| `images_skipped` | `integer` | Images already in the DB (skipped as duplicates) |
| `faces_detected` | `integer` | Total face detections across all processed images |
| `new_faces_created` | `integer` | New unique identities (`grab_id`s) inserted into `faces` table |
| `errors` | `string[]` | Per-image error messages (empty array if no errors) |

#### Response `404 Not Found`

Returned when the specified `path` does not exist on the filesystem.

```json
{
  "detail": "Storage directory does not exist: /app/storage/event-2026"
}
```

#### Response `500 Internal Server Error`

Unexpected failure during ingestion (e.g. DB connection dropped mid-run).

```json
{
  "detail": "Ingestion failed: connection to server lost"
}
```

#### Examples

```bash
# cURL — ingest everything
curl -X POST http://localhost:8000/api/v1/ingest

# cURL — ingest a specific subfolder
curl -X POST "http://localhost:8000/api/v1/ingest?path=./storage/marathon-2026"
```

```python
# Python — ingest with status reporting
import requests

resp = requests.post(
    "http://localhost:8000/api/v1/ingest",
    params={"path": "./storage/marathon-2026"},  # optional
)
resp.raise_for_status()
stats = resp.json()

print(f"Processed : {stats['images_processed']} images")
print(f"Skipped   : {stats['images_skipped']} (already indexed)")
print(f"Faces     : {stats['faces_detected']} detected")
print(f"New IDs   : {stats['new_faces_created']} unique people found")

if stats["errors"]:
    print(f"Errors ({len(stats['errors'])}):")
    for err in stats["errors"]:
        print(f"  - {err}")
```

```javascript
// JavaScript (fetch)
const resp = await fetch("http://localhost:8000/api/v1/ingest", {
  method: "POST",
});
const stats = await resp.json();
console.log(`Indexed ${stats.images_processed} images, found ${stats.new_faces_created} new identities`);
```

#### Behaviour Notes

- **Deduplication:** Images are de-duplicated by absolute `file_path`. Re-running ingest on the same directory is safe — already-indexed images produce a `skipped` count increment, not duplicates.
- **Partial failures:** Each image is processed in its own atomic DB transaction. If one image fails, it is recorded in `errors` and ingestion continues with the next image. The run always completes.
- **Face matching threshold:** Faces are matched against the database using cosine similarity. The threshold is controlled by `FACE_MATCH_TOLERANCE` in `.env` (default `0.45`). Two faces with similarity above this threshold are considered the same person.
- **Supported formats:** `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`

---

### POST /api/v1/auth/selfie

Identify a person by uploading a photo of their face. The system extracts a 512-d ArcFace embedding, searches the database using cosine similarity, and returns the matching `grab_id` if found.

> **This is the "Selfie-as-a-Key" endpoint.** The returned `grab_id` is used as the identity token for image retrieval.

#### Request

```http
POST /api/v1/auth/selfie HTTP/1.1
Host: localhost:8000
Content-Type: multipart/form-data; boundary=----FormBoundary
```

#### Form Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | `binary` (image) | **Yes** | Selfie image. Must contain exactly one clearly visible face. Accepted formats: JPEG, PNG, WEBP, BMP. |

#### Response `200 OK` — Match Found

```json
{
  "matched": true,
  "grab_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "confidence": 0.8734,
  "message": "Identity verified successfully."
}
```

#### Response `200 OK` — No Match

Returned when the face is detected successfully but does not match any identity in the database. This is **not** an error — it means the person was not present in any ingested photos.

```json
{
  "matched": false,
  "grab_id": null,
  "confidence": null,
  "message": "No matching identity found. You may not be in the system yet."
}
```

| Field | Type | Description |
|---|---|---|
| `matched` | `boolean` | `true` if a matching identity was found |
| `grab_id` | `UUID \| null` | The person's unique identity UUID. `null` if no match |
| `confidence` | `float \| null` | Cosine similarity score between uploaded face and matched identity (0.0–1.0, higher = more similar). `null` if no match |
| `message` | `string` | Human-readable result message |

#### Response `400 Bad Request`

```json
{
  "detail": "No face detected in the uploaded image. Please upload a clear selfie."
}
```

Returned when:
- No face is detected in the uploaded image
- The uploaded file is empty (zero bytes)

#### Examples

```bash
# cURL
curl -X POST http://localhost:8000/api/v1/auth/selfie \
  -F "file=@/path/to/my-selfie.jpg"
```

```python
# Python — full selfie auth flow
import requests

with open("my_selfie.jpg", "rb") as f:
    resp = requests.post(
        "http://localhost:8000/api/v1/auth/selfie",
        files={"file": ("selfie.jpg", f, "image/jpeg")},
    )

resp.raise_for_status()
result = resp.json()

if result["matched"]:
    grab_id = result["grab_id"]
    confidence = result["confidence"]
    print(f"✅ Identity matched! grab_id={grab_id}, confidence={confidence:.2%}")
else:
    print("❌ No match found — you may not be in the system yet.")
```

```javascript
// JavaScript — browser FileInput → selfie auth
async function authenticateWithSelfie(fileInputElement) {
  const formData = new FormData();
  formData.append("file", fileInputElement.files[0]);

  const resp = await fetch("http://localhost:8000/api/v1/auth/selfie", {
    method: "POST",
    body: formData,
  });

  const result = await resp.json();

  if (result.matched) {
    console.log("Matched! grab_id:", result.grab_id);
    console.log("Confidence:", (result.confidence * 100).toFixed(1) + "%");
    return result.grab_id;
  } else {
    console.log("No match found:", result.message);
    return null;
  }
}
```

#### Behaviour Notes

- **Multi-face uploads:** If multiple faces are detected, the system uses the **first detected face** (typically the most prominent or largest). For best accuracy, upload a clear, single-face selfie shot from the shoulders up.
- **Confidence score:** A score of `1.0` means the faces are mathematically identical vectors. In practice, scores above `0.70` indicate high confidence for the `buffalo_l` model. Scores between the threshold and `0.70` are valid matches but indicate lower certainty.
- **Privacy:** The uploaded image is processed entirely in memory — it is **never written to disk or stored** in the database.

---

### GET /api/v1/images/{grab_id}

Retrieve all event images in which the specified person appears. Results are paginated and include full image metadata plus face bounding boxes for every detected face in each image.

#### Request

```http
GET /api/v1/images/3fa85f64-5717-4562-b3fc-2c963f66afa6?page=1&per_page=20 HTTP/1.1
Host: localhost:8000
```

#### Path Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `grab_id` | `UUID` | **Yes** | The person's unique identity UUID (obtained from the selfie auth endpoint) |

#### Query Parameters

| Parameter | Type | Required | Default | Constraints | Description |
|---|---|---|---|---|---|
| `page` | `integer` | No | `1` | ≥ 1 | Page number (1-indexed) |
| `per_page` | `integer` | No | `20` | 1 – 100 | Number of images to return per page |

#### Response `200 OK`

```json
{
  "grab_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "page": 1,
  "per_page": 20,
  "total": 47,
  "images": [
    {
      "image_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "file_path": "/app/storage/marathon-2026/finish_line_0042.jpg",
      "file_name": "finish_line_0042.jpg",
      "file_size": 3145728,
      "width": 4032,
      "height": 3024,
      "ingested_at": "2026-04-18T06:30:00.000Z",
      "faces": [
        {
          "grab_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
          "bbox": {
            "x": 1240,
            "y": 380,
            "w": 210,
            "h": 280
          },
          "confidence": null
        },
        {
          "grab_id": "9b8a7c6d-5e4f-3210-fedc-ba0987654321",
          "bbox": {
            "x": 780,
            "y": 400,
            "w": 195,
            "h": 260
          },
          "confidence": null
        }
      ]
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `grab_id` | `UUID` | The identity that was queried |
| `page` | `integer` | Current page number |
| `per_page` | `integer` | Items per page (as requested) |
| `total` | `integer` | **Total number of images** containing this person (across all pages) |
| `images` | `ImageOut[]` | Array of image records for this page |
| `images[].faces` | `FaceInImage[]` | **All** faces in the image (not just the queried person) — useful for rendering all bounding boxes |

#### Response `404 Not Found`

```json
{
  "detail": "No identity found with grab_id: 3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

Returned when the given `grab_id` does not exist in the `faces` table.

#### Response `422 Unprocessable Entity`

```json
{
  "detail": [
    {
      "loc": ["path", "grab_id"],
      "msg": "value is not a valid uuid",
      "type": "type_error.uuid"
    }
  ]
}
```

#### Examples

```bash
# cURL — first page (default 20 per page)
curl "http://localhost:8000/api/v1/images/3fa85f64-5717-4562-b3fc-2c963f66afa6"

# cURL — page 2, 10 items per page
curl "http://localhost:8000/api/v1/images/3fa85f64-5717-4562-b3fc-2c963f66afa6?page=2&per_page=10"
```

```python
# Python — fetch all pages and collect every matching image
import requests

BASE_URL = "http://localhost:8000"

def get_all_images(grab_id: str) -> list[dict]:
    """Fetch every image for a given grab_id across all pages."""
    all_images = []
    page = 1
    per_page = 50  # max 100

    while True:
        resp = requests.get(
            f"{BASE_URL}/api/v1/images/{grab_id}",
            params={"page": page, "per_page": per_page},
        )
        resp.raise_for_status()
        data = resp.json()

        all_images.extend(data["images"])

        # Stop when we've collected all images
        if len(all_images) >= data["total"]:
            break
        page += 1

    return all_images

# Usage
grab_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
images = get_all_images(grab_id)
print(f"Found {len(images)} photos")

for img in images:
    # Find the bounding box for our specific person
    my_faces = [f for f in img["faces"] if f["grab_id"] == grab_id]
    if my_faces and my_faces[0]["bbox"]:
        bbox = my_faces[0]["bbox"]
        print(f"{img['file_name']}: face at x={bbox['x']}, y={bbox['y']}, "
              f"w={bbox['w']}, h={bbox['h']}")
```

```python
# Python — crop and save the person's face from each image using Pillow
from PIL import Image
import requests

def crop_face_from_image(file_path: str, bbox: dict) -> Image.Image:
    """Crop a face region from an image using a bounding box dict."""
    img = Image.open(file_path)
    x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
    return img.crop((x, y, x + w, y + h))
```

```javascript
// JavaScript — display images in a gallery with face highlight overlay
async function loadGallery(grabId) {
  let page = 1;
  const allImages = [];

  while (true) {
    const resp = await fetch(
      `http://localhost:8000/api/v1/images/${grabId}?page=${page}&per_page=50`
    );
    const data = await resp.json();
    allImages.push(...data.images);
    if (allImages.length >= data.total) break;
    page++;
  }

  return allImages;
}

function drawFaceBox(canvas, img, faces, targetGrabId) {
  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, 0, 0);

  for (const face of faces) {
    if (!face.bbox) continue;
    const { x, y, w, h } = face.bbox;
    ctx.strokeStyle = face.grab_id === targetGrabId ? "#00ff88" : "#ff4444";
    ctx.lineWidth = 3;
    ctx.strokeRect(x, y, w, h);
  }
}
```

#### Behaviour Notes

- **Pagination is 1-indexed.** Page `1` is the first page — there is no page `0`.
- **`total` is across all pages.** Use `total` and `per_page` to compute the number of pages: `Math.ceil(total / per_page)`.
- **All faces per image are returned.** Each `ImageOut.faces` array includes every detected face in the photo — not just your queried identity. This allows you to render bounding boxes for all people in the frame simultaneously.
- **Ordering:** Images are returned ordered by `ingested_at DESC` then `image_id` for stable, deterministic pagination.

---

## End-to-End Usage Workflows

### Workflow 1: Event Setup → Person Retrieves Their Photos

```
1. Organiser places all event photos in ./storage/marathon-2026/

2. Organiser calls:
   POST /api/v1/ingest?path=./storage/marathon-2026
   → 2,400 images processed, 850 unique people indexed

3. Runner opens the mobile app and takes a selfie
   POST /api/v1/auth/selfie  (file=selfie.jpg)
   → { matched: true, grab_id: "abc-123-...", confidence: 0.8921 }

4. App fetches runner's photos
   GET /api/v1/images/abc-123-...?page=1&per_page=20
   → 34 total images returned across 2 pages

5. App renders gallery with bounding boxes highlighting the runner's face
```

### Workflow 2: Incremental Ingestion

```
Day 1:
  POST /api/v1/ingest?path=./storage/day1/
  → 1,000 images processed, 0 skipped

Day 2 (new photos added):
  POST /api/v1/ingest?path=./storage/day2/
  → 800 images processed, 0 skipped (day1 images are untouched)

Re-running day1 (safe):
  POST /api/v1/ingest?path=./storage/day1/
  → 0 images processed, 1000 skipped (all already indexed)
```

### Workflow 3: Checking If a Person Is in the System

```
POST /api/v1/auth/selfie  (file=my_face.jpg)

Case A — In the system:
  → { matched: true, grab_id: "...", confidence: 0.87 }
  → Proceed to GET /api/v1/images/{grab_id}

Case B — Not in the system:
  → { matched: false, grab_id: null, confidence: null }
  → Inform the user they don't appear in any photos yet
```

---

## Client Examples

### Complete Python Client

```python
"""
grabpic_client.py — A minimal Python client for the Grabpic API.
"""

import requests
from pathlib import Path


class GrabpicClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def health(self) -> dict:
        """Check service health."""
        return self.session.get(f"{self.base_url}/health").json()

    def ingest(self, path: str | None = None) -> dict:
        """Trigger ingestion. Optionally specify a sub-path."""
        params = {"path": path} if path else {}
        resp = self.session.post(f"{self.base_url}/api/v1/ingest", params=params)
        resp.raise_for_status()
        return resp.json()

    def authenticate(self, image_path: str) -> dict:
        """
        Authenticate by selfie. Returns the full auth response dict.
        Raises requests.HTTPError on non-2xx (except 400).
        """
        with open(image_path, "rb") as f:
            resp = self.session.post(
                f"{self.base_url}/api/v1/auth/selfie",
                files={"file": (Path(image_path).name, f, "image/jpeg")},
            )
        resp.raise_for_status()
        return resp.json()

    def get_images(self, grab_id: str, page: int = 1, per_page: int = 20) -> dict:
        """Fetch one page of images for a given grab_id."""
        resp = self.session.get(
            f"{self.base_url}/api/v1/images/{grab_id}",
            params={"page": page, "per_page": per_page},
        )
        resp.raise_for_status()
        return resp.json()

    def get_all_images(self, grab_id: str, per_page: int = 50) -> list[dict]:
        """Fetch every image across all pages."""
        page, all_images = 1, []
        while True:
            data = self.get_images(grab_id, page=page, per_page=per_page)
            all_images.extend(data["images"])
            if len(all_images) >= data["total"]:
                break
            page += 1
        return all_images


# --- Usage ---
if __name__ == "__main__":
    client = GrabpicClient("http://localhost:8000")

    # 1. Ingest
    stats = client.ingest()
    print(f"Ingested {stats['images_processed']} images, {stats['new_faces_created']} new people")

    # 2. Authenticate
    auth = client.authenticate("my_selfie.jpg")
    if not auth["matched"]:
        print("Not found in the system.")
    else:
        grab_id = auth["grab_id"]
        print(f"Matched! grab_id={grab_id}, confidence={auth['confidence']:.2%}")

        # 3. Retrieve photos
        images = client.get_all_images(grab_id)
        print(f"You appear in {len(images)} photos")
```

---

## Rate Limits & Operational Notes

### Performance Characteristics

| Endpoint | Typical Latency | Notes |
|---|---|---|
| `GET /health` | < 5 ms | No DB or model call |
| `POST /api/v1/ingest` | 0.5–3 s per image | Dominated by InsightFace inference time |
| `POST /api/v1/auth/selfie` | 200–600 ms | Single model call + HNSW vector search |
| `GET /api/v1/images/{grab_id}` | 10–50 ms | Pure SQL with HNSW pre-filtered index |

### Scaling Considerations

- **CPU inference (default):** InsightFace runs on CPU via ONNX Runtime. A single-core CPU can process ~1–3 images/second. For large events (>10,000 photos), run ingestion overnight or use a multi-core server.
- **GPU acceleration:** Change `ctx_id=-1` to `ctx_id=0` in `face_service.py` and install `onnxruntime-gpu`. This accelerates ingestion to ~30–100 images/second on a modern GPU.
- **Connection pool:** The default pool size is 10 connections (`maxconn=10` in `database.py`). Increase for high-concurrency deployments.
- **Vector search:** pgvector's HNSW index ensures sub-millisecond similarity searches even with millions of face vectors.

### File Upload Limits

The default FastAPI/Uvicorn configuration handles files up to several hundred MB. For production deployments behind nginx or a reverse proxy, ensure the `client_max_body_size` is set appropriately (e.g., `20m` for standard event photos).

### Interactive API Explorer

When running locally, the full interactive Swagger UI is available at:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Both explorers allow you to test every endpoint directly from the browser, including file uploads for the selfie endpoint.
