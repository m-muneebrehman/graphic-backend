-- ============================================================
-- Grabpic schema – v002
-- Resize face embedding column: 128-d (dlib) → 512-d (InsightFace ArcFace)
-- ============================================================

-- Drop the old HNSW index (cannot be altered in-place)
DROP INDEX IF EXISTS idx_faces_embedding;

-- Alter the column type — existing rows must be deleted or re-ingested
-- because old 128-d vectors are incompatible with the new dimension.
-- In production, truncate the faces and image_faces tables before applying.
ALTER TABLE faces
    ALTER COLUMN embedding TYPE vector(512);

-- Recreate the HNSW index for the new dimension
CREATE INDEX IF NOT EXISTS idx_faces_embedding
    ON faces USING hnsw (embedding vector_cosine_ops);
