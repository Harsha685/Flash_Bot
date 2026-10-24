"""SQLite persistence for pipeline runs."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from flashbot.workspace import get_workspace

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS flash_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    board_name TEXT NOT NULL,
    fqbn TEXT NOT NULL,
    port TEXT NOT NULL,
    sketch_path TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('success', 'failed')),
    error TEXT,
    source_hash TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

# Columns added after the original schema; applied to existing databases on open.
_MIGRATIONS = {
    "source_hash": "TEXT",
    "target_kind": "TEXT",
    "env": "TEXT",
    "stage": "TEXT",
    "test_status": "TEXT",
    "duration": "REAL",
}

_initialized: set[Path] = set()


def _db_path() -> Path:
    return get_workspace().db_path


def init_db(path: Optional[Path] = None) -> None:
    path = Path(path or _db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(_SCHEMA)
        existing = {row[1] for row in conn.execute("PRAGMA table_info(flash_logs)")}
        for column, sql_type in _MIGRATIONS.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE flash_logs ADD COLUMN {column} {sql_type}")
        conn.commit()
    finally:
        conn.close()
    _initialized.add(path)


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    path = _db_path()
    if path not in _initialized:
        init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_result(*, board_name: str, fqbn: str, port: str, sketch_path: str, status: str,
                error: Optional[str] = None, source_hash: Optional[str] = None,
                target_kind: str = "arduino", env: Optional[str] = None,
                stage: Optional[str] = None, test_status: Optional[str] = None,
                duration: Optional[float] = None) -> int:
    """
    Record one pipeline run. Pass source_hash only when the build succeeded:
    it is what lets the next run of the same sketch skip compilation.
    """
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO flash_logs
               (board_name, fqbn, port, sketch_path, status, error, source_hash,
                target_kind, env, stage, test_status, duration, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (board_name, fqbn, port, sketch_path, status, error, source_hash,
             target_kind, env, stage, test_status, duration,
             datetime.now().strftime(TIMESTAMP_FORMAT)),
        )
        return cur.lastrowid


def get_results(limit: Optional[int] = None, failed_only: bool = False,
                since: Optional[datetime] = None) -> list[sqlite3.Row]:
    query = "SELECT * FROM flash_logs WHERE 1=1"
    params: list = []
    if failed_only:
        query += " AND status = 'failed'"
    if since:
        query += " AND timestamp >= ?"
        params.append(since.strftime(TIMESTAMP_FORMAT))
    query += " ORDER BY id DESC"
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    with _connect() as conn:
        return conn.execute(query, params).fetchall()


def get_last_build_hash(fqbn: str, sketch_path: str) -> Optional[str]:
    """Source hash of the most recent successful build of this sketch for this FQBN."""
    with _connect() as conn:
        row = conn.execute(
            """SELECT source_hash FROM flash_logs
               WHERE fqbn = ? AND sketch_path = ? AND source_hash IS NOT NULL
               ORDER BY id DESC LIMIT 1""",
            (fqbn, sketch_path),
        ).fetchone()
    return row["source_hash"] if row else None


def get_stats() -> dict:
    with _connect() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS total,
                      COALESCE(SUM(status = 'success'), 0) AS success,
                      COALESCE(SUM(status = 'failed'), 0) AS failed
               FROM flash_logs"""
        ).fetchone()
    return dict(row)
