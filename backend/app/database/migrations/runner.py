"""Startup schema migration runner.

Provides a lightweight, Alembic-free migration system for additive schema
changes.  Each migration is a numbered function that receives a SQLAlchemy
``Connection`` and executes raw DDL.  The runner tracks applied versions in
a ``_schema_migrations`` table and only runs new ones.

Design constraints:
  - Every migration MUST be idempotent (safe to re-run).
  - Migrations are additive-only — never drop columns, tables, or data.
  - All DDL uses raw SQL so there is zero ORM coupling.
  - The tracker table is bootstrapped before anything else with
    ``CREATE TABLE IF NOT EXISTS``.

Usage (called from lifespan.py at startup)::

    from app.database.migrations.runner import run_migrations
    run_migrations(engine)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, List

from sqlalchemy import Engine, text

from app.core.logging import get_logger


logger = get_logger("attendai.migrations")


# ---------------------------------------------------------------------------
# Migration registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Migration:
    """One numbered schema migration."""

    version: str           # e.g. "0001"
    description: str       # human-readable
    fn: Callable           # (connection) -> None


_MIGRATIONS: List[Migration] = []


def _register(version: str, description: str):
    """Decorator: register a migration function."""
    def decorator(fn: Callable):
        _MIGRATIONS.append(Migration(version=version, description=description, fn=fn))
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Tracker table bootstrap
# ---------------------------------------------------------------------------

_TRACKER_DDL = """\
CREATE TABLE IF NOT EXISTS _schema_migrations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    version    TEXT    NOT NULL UNIQUE,
    description TEXT   NOT NULL,
    applied_at TEXT    NOT NULL
)
"""


def _ensure_tracker(conn) -> None:
    """Create the tracker table if it doesn't exist."""
    conn.execute(text(_TRACKER_DDL))
    conn.commit()


def _applied_versions(conn) -> set[str]:
    """Return the set of already-applied migration versions."""
    rows = conn.execute(
        text("SELECT version FROM _schema_migrations ORDER BY version")
    ).fetchall()
    return {row[0] for row in rows}


def _record_migration(conn, migration: Migration) -> None:
    """Mark a migration as applied."""
    conn.execute(
        text(
            "INSERT INTO _schema_migrations (version, description, applied_at) "
            "VALUES (:version, :description, :applied_at)"
        ),
        {
            "version": migration.version,
            "description": migration.description,
            "applied_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_migrations(engine: Engine) -> int:
    """Execute all pending migrations in order.

    Returns the number of migrations applied (0 when fully up-to-date).
    """
    applied = 0
    with engine.connect() as conn:
        _ensure_tracker(conn)
        done = _applied_versions(conn)

        # Migrations must be sorted by version.
        for migration in sorted(_MIGRATIONS, key=lambda m: m.version):
            if migration.version in done:
                continue
            logger.info(
                "Applying migration %s: %s",
                migration.version,
                migration.description,
            )
            try:
                migration.fn(conn)
                _record_migration(conn, migration)
                applied += 1
                logger.info("Migration %s applied", migration.version)
            except Exception:
                logger.exception(
                    "Migration %s FAILED — aborting remaining migrations",
                    migration.version,
                )
                raise

    if applied:
        logger.info("Schema migrations complete: %d applied", applied)
    else:
        logger.info("Schema migrations: already up-to-date")
    return applied


# ---------------------------------------------------------------------------
# Helpers for migration authors
# ---------------------------------------------------------------------------

def _column_exists(conn, table: str, column: str) -> bool:
    """Check whether a column exists on a table (SQLite PRAGMA)."""
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(row[1] == column for row in rows)


def _table_exists(conn, table: str) -> bool:
    """Check whether a table exists (SQLite)."""
    row = conn.execute(
        text(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name=:name"
        ),
        {"name": table},
    ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Migrations — add new ones at the bottom, always incrementing the version.
# ---------------------------------------------------------------------------

@_register("0001", "Create academic_classes table")
def _m0001(conn) -> None:
    if _table_exists(conn, "academic_classes"):
        return
    conn.execute(text("""\
        CREATE TABLE academic_classes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            class_code    TEXT    NOT NULL UNIQUE,
            major         TEXT    NOT NULL,
            year          INTEGER NOT NULL,
            section       TEXT    NOT NULL,
            academic_year TEXT    NOT NULL,
            is_active     INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT    NOT NULL,
            UNIQUE (major, year, section, academic_year)
        )
    """))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_academic_classes_code "
        "ON academic_classes (class_code)"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_academic_classes_active "
        "ON academic_classes (is_active)"
    ))
    conn.commit()


@_register("0002", "Add class_id column to students")
def _m0002(conn) -> None:
    if _column_exists(conn, "students", "class_id"):
        return
    conn.execute(text(
        "ALTER TABLE students ADD COLUMN class_id INTEGER "
        "REFERENCES academic_classes(id)"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_students_class_id ON students (class_id)"
    ))
    conn.commit()


@_register("0003", "Create faculty_classes join table")
def _m0003(conn) -> None:
    if _table_exists(conn, "faculty_classes"):
        return
    conn.execute(text("""\
        CREATE TABLE faculty_classes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            class_id    INTEGER NOT NULL REFERENCES academic_classes(id) ON DELETE CASCADE,
            assigned_at TEXT    NOT NULL,
            UNIQUE (user_id, class_id)
        )
    """))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_faculty_classes_user "
        "ON faculty_classes (user_id)"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_faculty_classes_class "
        "ON faculty_classes (class_id)"
    ))
    conn.commit()


@_register("0004", "Create attendance_sessions table")
def _m0004(conn) -> None:
    if _table_exists(conn, "attendance_sessions"):
        return
    conn.execute(text("""\
        CREATE TABLE attendance_sessions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT    NOT NULL,
            class_id     INTEGER NOT NULL REFERENCES academic_classes(id),
            faculty_id   INTEGER NOT NULL REFERENCES users(id),
            started_at   TEXT    NOT NULL,
            ended_at     TEXT,
            status       TEXT    NOT NULL DEFAULT 'active'
        )
    """))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_attendance_sessions_class "
        "ON attendance_sessions (class_id)"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_attendance_sessions_faculty "
        "ON attendance_sessions (faculty_id)"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_attendance_sessions_status "
        "ON attendance_sessions (status)"
    ))
    conn.commit()


@_register("0005", "Add session_id column to attendance")
def _m0005(conn) -> None:
    if _column_exists(conn, "attendance", "session_id"):
        return
    conn.execute(text(
        "ALTER TABLE attendance ADD COLUMN session_id INTEGER "
        "REFERENCES attendance_sessions(id)"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_attendance_session_id "
        "ON attendance (session_id)"
    ))
    conn.commit()


@_register("0006", "Add must_change_password column to users")
def _m0006(conn) -> None:
    if _column_exists(conn, "users", "must_change_password"):
        return
    conn.execute(text(
        "ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0"
    ))
    conn.commit()


@_register("0007", "Add student lifecycle fields (status, graduated_at, last_class_id, lifecycle_batch_id)")
def _m0007(conn) -> None:
    if not _column_exists(conn, "students", "status"):
        conn.execute(text(
            "ALTER TABLE students ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'active'"
        ))
    if not _column_exists(conn, "students", "graduated_at"):
        conn.execute(text(
            "ALTER TABLE students ADD COLUMN graduated_at TIMESTAMP NULL"
        ))
    if not _column_exists(conn, "students", "last_class_id"):
        conn.execute(text(
            "ALTER TABLE students ADD COLUMN last_class_id INTEGER NULL "
            "REFERENCES academic_classes(id)"
        ))
    if not _column_exists(conn, "students", "lifecycle_batch_id"):
        conn.execute(text(
            "ALTER TABLE students ADD COLUMN lifecycle_batch_id VARCHAR(64) NULL"
        ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_students_status ON students (status)"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_students_last_class ON students (last_class_id)"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_students_lifecycle_batch ON students (lifecycle_batch_id)"
    ))
    conn.commit()
