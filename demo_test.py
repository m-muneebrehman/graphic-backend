# -*- coding: utf-8 -*-
"""
demo_test.py — End-to-end showcase of the Grabpic API.

Usage:
    uv run python demo_test.py

Workflow:
    1. Health check
    2. Ingest the marathon-demo sample images
    3. Selfie authentication (uses the event images directly as selfies)
    4. Image retrieval for matched identities
    5. Print a full summary report
"""

import sys
import time
import json
from pathlib import Path

import io
import sys

# Force UTF-8 output on Windows so the script never hits cp1252 limits
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import requests

BASE_URL = "http://localhost:8000"

# For the selfie test we use the same event images that were ingested
# (same image → identical embedding → guaranteed 1.0 cosine similarity match)
SELFIE_ALICE = Path("storage/marathon-demo/alice_finish_line.png")
SELFIE_BOB   = Path("storage/marathon-demo/bob_finish_line.png")


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def header(text: str):
    bar = "=" * 60
    print(f"\n{bar}")
    print(f"  {text}")
    print(bar)


def ok(label: str, value):
    print(f"  [OK]   {label:<30} {value}")


def warn(label: str, value):
    print(f"  [WARN] {label:<30} {value}")


def fail(label: str, value):
    print(f"  [FAIL] {label:<30} {value}")
    sys.exit(1)


def pretty(data: dict) -> str:
    return json.dumps(data, indent=4, default=str)


# ─────────────────────────────────────────────────────────────
# Steps
# ─────────────────────────────────────────────────────────────

def step_health():
    header("STEP 1 — Health Check")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        ok("Status", data["status"])
        ok("Version", data["version"])
    except requests.ConnectionError:
        fail("Server unreachable", f"Is the server running at {BASE_URL}?")


def step_ingest() -> dict:
    header("STEP 2 — Ingest marathon-demo Images")
    print("  Ingesting: ./storage/marathon-demo/ ...")
    t0 = time.time()
    resp = requests.post(
        f"{BASE_URL}/api/v1/ingest",
        params={"path": "./storage/marathon-demo"},
        timeout=300,
    )
    elapsed = time.time() - t0

    if resp.status_code == 404:
        fail("Storage path not found", resp.json()["detail"])

    resp.raise_for_status()
    stats = resp.json()

    ok("Images processed", stats["images_processed"])
    ok("Images skipped (duplicates)", stats["images_skipped"])
    ok("Faces detected", stats["faces_detected"])
    ok("New unique identities", stats["new_faces_created"])
    ok("Ingestion time", f"{elapsed:.1f}s")

    if stats["errors"]:
        for err in stats["errors"]:
            warn("Error", err)
    else:
        ok("Errors", "None")

    return stats


def step_auth(name: str, selfie_path: Path) -> str | None:
    header(f"STEP 3 — Selfie Authentication ({name})")

    if not selfie_path.exists():
        warn("Selfie file not found", str(selfie_path))
        return None

    print(f"  Uploading selfie: {selfie_path.name}")
    with open(selfie_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/api/v1/auth/selfie",
            files={"file": (selfie_path.name, f, "image/png")},
            timeout=60,
        )

    if resp.status_code == 400:
        warn("Auth result", resp.json()["detail"])
        return None

    resp.raise_for_status()
    result = resp.json()

    if result["matched"]:
        ok("Matched", "YES")
        ok("grab_id", result["grab_id"])
        ok("Confidence", f"{result['confidence']:.4f}  ({result['confidence']*100:.1f}%)")
        ok("Message", result["message"])
        return result["grab_id"]
    else:
        warn("Matched", "NO — not found in the system")
        warn("Message", result["message"])
        return None


def step_retrieve(name: str, grab_id: str):
    header(f"STEP 4 — Retrieve Images for {name}")
    print(f"  Querying grab_id: {grab_id}")
    resp = requests.get(
        f"{BASE_URL}/api/v1/images/{grab_id}",
        params={"page": 1, "per_page": 20},
        timeout=30,
    )

    if resp.status_code == 404:
        warn("Retrieve result", "grab_id not found in DB")
        return

    resp.raise_for_status()
    data = resp.json()

    ok("Total images found", data["total"])
    ok("Page", f"{data['page']} of {-(-data['total'] // data['per_page'])}")  # ceiling div

    for i, img in enumerate(data["images"], 1):
        print(f"  [IMG {i}]  {img['file_name']}")
        print(f"       Size : {img['file_size'] // 1024 if img['file_size'] else '?'} KB")
        print(f"       Dims : {img['width']}×{img['height']} px" if img["width"] else "       Dims : unknown")
        print(f"       Date : {img['ingested_at']}")
        print(f"       Faces in frame: {len(img['faces'])}")

        # Show bounding box for our specific person
        my_faces = [f for f in img["faces"] if f["grab_id"] == grab_id]
        if my_faces and my_faces[0]["bbox"]:
            b = my_faces[0]["bbox"]
            print(f"       Your bbox : x={b['x']}, y={b['y']}, w={b['w']}, h={b['h']}")


def step_ingest_again():
    """Run ingest a second time to verify deduplication works."""
    header("STEP 5 — Re-Ingest (Deduplication Check)")
    print("  Running ingest a second time on the same directory ...")
    resp = requests.post(
        f"{BASE_URL}/api/v1/ingest",
        params={"path": "./storage/marathon-demo"},
        timeout=300,
    )
    resp.raise_for_status()
    stats = resp.json()

    ok("Images processed (should be 0)", stats["images_processed"])
    ok("Images skipped (should = total)", stats["images_skipped"])

    if stats["images_processed"] == 0 and stats["images_skipped"] > 0:
        ok("Deduplication", "WORKING [OK]")
    else:
        warn("Deduplication", "unexpected result")


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    print("\nGrabpic -- End-to-End Demo Test")
    print("=" * 60)
    print(f"  Base URL : {BASE_URL}")
    print(f"  Storage  : ./storage/marathon-demo/")

    step_health()
    ingest_stats = step_ingest()

    grab_id_alice = step_auth("Alice", SELFIE_ALICE)
    grab_id_bob   = step_auth("Bob",   SELFIE_BOB)

    if grab_id_alice:
        step_retrieve("Alice", grab_id_alice)

    if grab_id_bob:
        step_retrieve("Bob", grab_id_bob)

    step_ingest_again()

    header("DEMO COMPLETE")
    print("  All steps executed successfully.")
    print(f"  Interactive docs: {BASE_URL}/docs")
    print()


if __name__ == "__main__":
    main()
