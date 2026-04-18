-- ============================================================
-- Grabpic schema – v001
-- Requires: pgvector extension
-- ============================================================

-- 1. Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Unique faces discovered during ingestion
CREATE TABLE IF NOT EXISTS faces (
    grab_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    embedding   vector(128)  NOT NULL,
    created_at  TIMESTAMPTZ  DEFAULT now()
);

-- 3. Ingested images
CREATE TABLE IF NOT EXISTS images (
    image_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path   TEXT NOT NULL UNIQUE,
    file_name   TEXT NOT NULL,
    file_size   INTEGER,
    width       INTEGER,
    height      INTEGER,
    ingested_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Many-to-many join: image ↔ face
CREATE TABLE IF NOT EXISTS image_faces (
    id          SERIAL PRIMARY KEY,
    image_id    UUID NOT NULL REFERENCES images(image_id) ON DELETE CASCADE,
    grab_id     UUID NOT NULL REFERENCES faces(grab_id)   ON DELETE CASCADE,
    bbox_x      INTEGER,
    bbox_y      INTEGER,
    bbox_w      INTEGER,
    bbox_h      INTEGER,
    confidence  FLOAT,
    UNIQUE(image_id, grab_id)
);

-- 5. HNSW index for fast cosine-similarity search on face embeddings
CREATE INDEX IF NOT EXISTS idx_faces_embedding
    ON faces USING hnsw (embedding vector_cosine_ops);
