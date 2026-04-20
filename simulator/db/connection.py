"""
Database connection management for AMS Simulator.

Provides SimDB, the central database interface with thread-local connections,
transaction support, and automatic schema initialization.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from simulator.db.schema import SCHEMA_VERSION, get_schema_sql


class SimDB:
    """Central database interface for AMS Simulator.

    Thread-safe SQLite database manager with automatic schema creation
    and migration support.

    Usage:
        db = SimDB('my_designs.db')
        db.initialize()
        with db.transaction() as conn:
            conn.execute("INSERT INTO technologies ...")
        db.close()
    """

    def __init__(self, db_path: str = "ams_simulator.db"):
        self.db_path = str(Path(db_path).resolve())
        self._local = threading.local()
        self._lock = threading.Lock()
        self._initialized = False

    def connect(self) -> sqlite3.Connection:
        """Get or create a thread-local database connection."""
        conn = getattr(self._local, "connection", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.connection = conn
        return conn

    def initialize(self):
        """Create all tables if they don't exist. Idempotent."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            conn = self.connect()
            conn.executescript(get_schema_sql())
            # Store schema version
            conn.execute(
                "INSERT OR REPLACE INTO _schema_meta (key, value) VALUES (?, ?)",
                ("schema_version", str(SCHEMA_VERSION)),
            )
            conn.commit()
            self._initialized = True

    def close(self):
        """Close the thread-local connection if open."""
        conn = getattr(self._local, "connection", None)
        if conn is not None:
            conn.close()
            self._local.connection = None

    @contextmanager
    def transaction(self):
        """Context manager for atomic transactions.

        Usage:
            with db.transaction() as conn:
                conn.execute("INSERT INTO ...")
                conn.execute("UPDATE ...")
            # Auto-commits on success, rolls back on exception
        """
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single SQL statement and return the cursor."""
        return self.connect().execute(sql, params)

    def executemany(self, sql: str, params_seq) -> sqlite3.Cursor:
        """Execute SQL with multiple parameter sets."""
        return self.connect().executemany(sql, params_seq)

    def commit(self):
        """Commit the current transaction."""
        self.connect().commit()

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute SQL and fetch one row."""
        return self.connect().execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute SQL and fetch all rows."""
        return self.connect().execute(sql, params).fetchall()

    @property
    def schema_version(self) -> int:
        """Return the current schema version stored in the database."""
        try:
            row = self.fetchone(
                "SELECT value FROM _schema_meta WHERE key='schema_version'"
            )
            return int(row["value"]) if row else 0
        except (sqlite3.OperationalError, TypeError):
            return 0
