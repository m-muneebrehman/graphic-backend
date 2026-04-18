"""
apply_migrations.py — Manually apply all pending schema changes to the live DB.

Run once:
    uv run python apply_migrations.py
"""
import psycopg2

DSN = "postgresql://postgres:Gmail.com123@db.xcbjvscvnilefhplbwxv.supabase.co:5432/postgres"

# Full target schema — idempotent
MIGRATIONS = [
    # ── 1. Enable vector extension
    ("enable_vector", "CREATE EXTENSION IF NOT EXISTS vector;"),

    # ── 2. Add missing columns to images (safe: only if they don't exist)
    ("images_file_name",  "ALTER TABLE images ADD COLUMN IF NOT EXISTS file_name TEXT NOT NULL DEFAULT '';"),
    ("images_file_size",  "ALTER TABLE images ADD COLUMN IF NOT EXISTS file_size INTEGER;"),
    ("images_width",      "ALTER TABLE images ADD COLUMN IF NOT EXISTS width INTEGER;"),
    ("images_height",     "ALTER TABLE images ADD COLUMN IF NOT EXISTS height INTEGER;"),
    # Fix ingested_at type to TIMESTAMPTZ if it's plain TIMESTAMP
    ("images_ingested_tz","ALTER TABLE images ALTER COLUMN ingested_at TYPE TIMESTAMPTZ USING ingested_at AT TIME ZONE 'UTC';"),
    # Add DEFAULT for ingested_at
    ("images_ingested_default", "ALTER TABLE images ALTER COLUMN ingested_at SET DEFAULT now();"),
    # Add UNIQUE on file_path
    ("images_file_path_unique", """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'images_file_path_key'
            ) THEN
                ALTER TABLE images ADD CONSTRAINT images_file_path_key UNIQUE (file_path);
            END IF;
        END $$;
    """),

    # ── 3. Fix faces.embedding dimension: check current, drop index, resize, recreate
    ("drop_embedding_index", "DROP INDEX IF EXISTS idx_faces_embedding;"),
    ("resize_embedding", """
        DO $$ BEGIN
            -- Only resize if current dimension is wrong (not 512)
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'faces'
                  AND column_name = 'embedding'
                  AND udt_name != 'vector'
            ) OR (
                -- check atttypmod for vector(N): atttypmod = N+1 for pgvector
                SELECT atttypmod FROM pg_attribute
                 WHERE attrelid = 'faces'::regclass
                   AND attname = 'embedding'
            ) != 513 THEN
                -- Clear incompatible old rows
                TRUNCATE faces CASCADE;
                ALTER TABLE faces ALTER COLUMN embedding TYPE vector(512);
            END IF;
        END $$;
    """),
    ("recreate_hnsw_index", """
        CREATE INDEX IF NOT EXISTS idx_faces_embedding
            ON faces USING hnsw (embedding vector_cosine_ops);
    """),

    # ── 4. Fix faces.created_at type
    ("faces_created_tz", "ALTER TABLE faces ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';"),
    ("faces_created_default", "ALTER TABLE faces ALTER COLUMN created_at SET DEFAULT now();"),

    # ── 5. Ensure image_faces has all expected columns
    ("imgfaces_confidence", "ALTER TABLE image_faces ADD COLUMN IF NOT EXISTS confidence FLOAT;"),
    ("imgfaces_bbox_x",     "ALTER TABLE image_faces ADD COLUMN IF NOT EXISTS bbox_x INTEGER;"),
    ("imgfaces_bbox_y",     "ALTER TABLE image_faces ADD COLUMN IF NOT EXISTS bbox_y INTEGER;"),
    ("imgfaces_bbox_w",     "ALTER TABLE image_faces ADD COLUMN IF NOT EXISTS bbox_w INTEGER;"),
    ("imgfaces_bbox_h",     "ALTER TABLE image_faces ADD COLUMN IF NOT EXISTS bbox_h INTEGER;"),
]

def main():
    print("Connecting to Supabase...")
    conn = psycopg2.connect(DSN)
    conn.autocommit = False

    for name, sql in MIGRATIONS:
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            print(f"  [OK]   {name}")
        except Exception as e:
            conn.rollback()
            print(f"  [SKIP] {name}: {e}")

    # Final state
    with conn.cursor() as cur:
        cur.execute("SELECT column_name, udt_name FROM information_schema.columns WHERE table_name='images' ORDER BY ordinal_position")
        print("\nimages columns:", [r[0] for r in cur.fetchall()])
        cur.execute("SELECT column_name, udt_name FROM information_schema.columns WHERE table_name='faces' ORDER BY ordinal_position")
        print("faces  columns:", [r[0] for r in cur.fetchall()])
        cur.execute("SELECT atttypmod FROM pg_attribute WHERE attrelid='faces'::regclass AND attname='embedding'")
        mod = cur.fetchone()[0]
        print(f"embedding dim  : {mod - 1} (should be 512)")

    conn.close()
    print("\nAll migrations applied.")

if __name__ == "__main__":
    main()
