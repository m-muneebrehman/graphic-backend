"""
Database connection pool and initialization utilities.

Uses psycopg2 with a SimpleConnectionPool for efficient connection reuse.
"""

import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from psycopg2 import pool, extras

from app.config import settings

# Register the UUID adapter so psycopg2 returns Python uuid objects
psycopg2.extras.register_uuid()

# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------

_pool: pool.SimpleConnectionPool | None = None


def _get_pool() -> pool.SimpleConnectionPool:
    """Lazy-initialise and return the connection pool."""
    global _pool
    if _pool is None or _pool.closed:
        _pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=settings.DATABASE_URL,
        )
    return _pool


@contextmanager
def get_db():
    """
    Context manager that yields a database connection from the pool.

    Usage::

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    p = _get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


# ---------------------------------------------------------------------------
# Schema migration
# ---------------------------------------------------------------------------

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def init_db() -> None:
    """
    Run all SQL migration files in order.

    Migration files are expected to be named ``NNN_description.sql`` and are
    executed in alphabetical order.  Each migration is idempotent (uses
    IF NOT EXISTS / ON CONFLICT where appropriate).
    """
    migration_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        print("[db] No migration files found.")
        return

    with get_db() as conn:
        with conn.cursor() as cur:
            for mf in migration_files:
                print(f"[db] Applying migration: {mf.name}")
                sql = mf.read_text(encoding="utf-8")
                cur.execute(sql)
    print("[db] All migrations applied successfully.")


def close_pool() -> None:
    """Close every connection in the pool."""
    global _pool
    if _pool and not _pool.closed:
        _pool.closeall()
        _pool = None
