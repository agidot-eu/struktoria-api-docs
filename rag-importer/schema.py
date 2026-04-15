"""
schema.py — SQLite schema definition and helper functions for Struktoria RAG importers.

The SQLite database acts as an intermediate format that maps directly
to the Struktoria RAG upload-nodes API:
  POST /v1/rag/api/sources/{id}/upload-nodes
  Body: { "nodes": [{ "relativePath", "content", "nodeType" }] }
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional


DDL = """
CREATE TABLE IF NOT EXISTS import_session (
    id          TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,   -- 'mssql' | 'git'
    source_name TEXT NOT NULL,   -- server/path (no passwords)
    created_at  TEXT NOT NULL    -- ISO8601 UTC
);

CREATE TABLE IF NOT EXISTS import_nodes (
    id            TEXT PRIMARY KEY,
    session_id    TEXT NOT NULL REFERENCES import_session(id),
    relative_path TEXT NOT NULL,  -- RAG hierarchy path, e.g. "MyDb/tables/dbo.Users"
    content       TEXT NOT NULL,  -- full text content
    node_type     TEXT NOT NULL DEFAULT 'document',  -- 'folder' | 'document'
    source_type   TEXT NOT NULL,  -- 'mssql' | 'git'
    source_path   TEXT,           -- original source location/identifier
    meta_json     TEXT,           -- JSON: {"type", "db", "server", "extension", ...}
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nodes_session ON import_nodes(session_id);
CREATE INDEX IF NOT EXISTS idx_nodes_path    ON import_nodes(relative_path);
"""


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class ImportDb:
    """
    Thin wrapper around sqlite3 for writing RAG import data.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> "ImportDb":
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(DDL)
        self._conn.commit()
        return self

    def __exit__(self, *_):
        if self._conn:
            self._conn.close()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("ImportDb not opened — use as context manager")
        return self._conn

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    def create_session(self, source_type: str, source_name: str) -> str:
        """Create a new import session and return its id."""
        sid = new_id()
        self.conn.execute(
            "INSERT INTO import_session (id, source_type, source_name, created_at) VALUES (?,?,?,?)",
            (sid, source_type, source_name, now_utc()),
        )
        self.conn.commit()
        return sid

    def get_sessions(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM import_session ORDER BY created_at DESC").fetchall()

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------

    def upsert_node(
        self,
        *,
        session_id: str,
        relative_path: str,
        content: str,
        node_type: str = "document",
        source_type: str,
        source_path: Optional[str] = None,
        meta_json: Optional[str] = None,
    ) -> str:
        """Insert or replace a node. Returns the node id."""
        nid = new_id()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO import_nodes
                (id, session_id, relative_path, content, node_type,
                 source_type, source_path, meta_json, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (nid, session_id, relative_path, content, node_type,
             source_type, source_path, meta_json, now_utc()),
        )
        return nid

    def flush(self):
        self.conn.commit()

    def count_nodes(self, session_id: Optional[str] = None) -> int:
        if session_id:
            row = self.conn.execute(
                "SELECT COUNT(*) FROM import_nodes WHERE session_id=?", (session_id,)
            ).fetchone()
        else:
            row = self.conn.execute("SELECT COUNT(*) FROM import_nodes").fetchone()
        return row[0]

    def iter_nodes(self, session_id: Optional[str] = None, batch_size: int = 100):
        """
        Yield batches of nodes as lists of sqlite3.Row.
        Used by upload.py to read nodes for API calls.
        """
        offset = 0
        where = "WHERE session_id=?" if session_id else ""
        params: tuple = (session_id,) if session_id else ()
        while True:
            rows = self.conn.execute(
                f"SELECT * FROM import_nodes {where} ORDER BY relative_path LIMIT ? OFFSET ?",
                params + (batch_size, offset),
            ).fetchall()
            if not rows:
                break
            yield rows
            offset += len(rows)
