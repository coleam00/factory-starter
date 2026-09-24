"""SQLite access and schema migrations.

Migrations are NAMED and recorded by name, so the order features load in never
matters. To change the schema, register a new migration with a new name:

    db.migration("things_001_create", "CREATE TABLE things (...)")

Never edit a migration that has shipped. A database that already ran it would
silently disagree with the code; add a new one (e.g. "things_002_add_color").
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "app.sqlite"

MIGRATIONS: dict[str, str] = {
    "core_001_app_meta": "CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
}


def migration(name: str, sql: str) -> None:
    """Register a schema change. Names are unique; reusing one with different SQL is a bug."""
    existing = MIGRATIONS.get(name)
    if existing is not None and existing != sql:
        raise ValueError(f"migration {name!r} already registered with different SQL")
    MIGRATIONS[name] = sql


def database_path() -> Path:
    """APP_DATABASE wins (the runtime host sets it to a fresh file per run)."""
    return Path(os.environ.get("APP_DATABASE") or DEFAULT_PATH)


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or database_path()
    if str(target) != ":memory:":
        Path(target).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Apply every registered migration this database has not run. Returns the names applied."""
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)")
    done = {row[0] for row in conn.execute("SELECT name FROM schema_migrations")}
    applied = []
    for name, sql in MIGRATIONS.items():
        if name in done:
            continue
        with conn:
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migrations (name) VALUES (?)", (name,))
        applied.append(name)
    return applied
