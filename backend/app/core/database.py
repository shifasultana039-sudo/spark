"""
ReliefChain AI - Unified Database Session & Connection Manager.
Supports both PostgreSQL (production/cloud) and SQLite (local zero-dependency development).
Implements strict connection leak prevention, transaction safety, and clean FastAPI dependency injection.
"""

import os
import re
import sqlite3
from typing import Generator, Any, Optional, Dict, List, Union
from contextlib import contextmanager

from .config import (
    get_database_url,
    get_database_engine,
    DATABASE_PATH,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB
)

# Optional psycopg driver import
try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False


def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> Dict[str, Any]:
    """Transforms SQLite row tuples into key-value dictionaries."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def adapt_sql(sql: str, target_engine: str) -> str:
    """
    Adapts SQL parameter placeholders between database engines while preserving string literals:
    - If target is 'postgresql': converts '?' to '%s'.
    - If target is 'sqlite': converts '%s' to '?'.
    """
    if target_engine == "postgresql":
        parts = re.split(r"('(?:''|[^'])*')", sql)
        for i in range(0, len(parts), 2):
            parts[i] = parts[i].replace("?", "%s")
        return "".join(parts)
    elif target_engine == "sqlite":
        parts = re.split(r"('(?:''|[^'])*')", sql)
        for i in range(0, len(parts), 2):
            parts[i] = parts[i].replace("%s", "?")
        return "".join(parts)
    return sql


class CursorWrapper:
    """
    Universal cursor proxy wrapping underlying DB-API cursor.
    Ensures normalized dictionary returns and query adaptation across SQLite & PostgreSQL.
    """
    def __init__(self, raw_cursor: Any, engine_type: str):
        self._cursor = raw_cursor
        self._engine_type = engine_type

    def execute(self, query: str, params: Any = None) -> "CursorWrapper":
        adapted = adapt_sql(query, self._engine_type)
        if params is not None:
            self._cursor.execute(adapted, params)
        else:
            self._cursor.execute(adapted)
        return self

    def executemany(self, query: str, seq_of_params: Any) -> "CursorWrapper":
        adapted = adapt_sql(query, self._engine_type)
        self._cursor.executemany(adapted, seq_of_params)
        return self

    def fetchone(self) -> Optional[Dict[str, Any]]:
        row = self._cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        if hasattr(self._cursor, "description") and self._cursor.description:
            return {col[0]: row[idx] for idx, col in enumerate(self._cursor.description)}
        return row

    def fetchall(self) -> List[Dict[str, Any]]:
        rows = self._cursor.fetchall()
        if not rows:
            return []
        if isinstance(rows[0], dict):
            return rows
        if hasattr(self._cursor, "description") and self._cursor.description:
            cols = [col[0] for col in self._cursor.description]
            return [{cols[idx]: r[idx] for idx in range(len(cols))} for r in rows]
        return rows

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self) -> int:
        return getattr(self._cursor, "rowcount", -1)

    @property
    def lastrowid(self) -> Optional[int]:
        return getattr(self._cursor, "lastrowid", None)

    def close(self):
        try:
            self._cursor.close()
        except Exception:
            pass


class DatabaseSession:
    """
    Unified Database Session for ReliefChain AI:
    - Provides execute, fetchone, fetchall, commit, rollback, close.
    - Adapts SQL queries transparently between PostgreSQL and SQLite.
    - Ensures connection closure and prevents resource leaks.
    """
    def __init__(self, raw_conn: Any, engine_type: str):
        self.raw_conn = raw_conn
        self.engine_type = engine_type
        self._closed = False
        self._last_cursor: Optional[CursorWrapper] = None

    def cursor(self) -> CursorWrapper:
        if self._closed:
            raise RuntimeError("Cannot open cursor on a closed DatabaseSession.")
        c = self.raw_conn.cursor()
        wrapper = CursorWrapper(c, self.engine_type)
        self._last_cursor = wrapper
        return wrapper

    def execute(self, query: str, params: Any = None) -> CursorWrapper:
        """Shortcut to execute a query on this session."""
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def fetchone(self) -> Optional[Dict[str, Any]]:
        if self._last_cursor:
            return self._last_cursor.fetchone()
        return None

    def fetchall(self) -> List[Dict[str, Any]]:
        if self._last_cursor:
            return self._last_cursor.fetchall()
        return []

    def commit(self):
        """Commits the active transaction."""
        if not self._closed:
            self.raw_conn.commit()

    def rollback(self):
        """Rolls back the active transaction."""
        if not self._closed:
            self.raw_conn.rollback()

    def close(self):
        """Closes the underlying raw connection safely."""
        if not self._closed:
            try:
                self.raw_conn.close()
            except Exception:
                pass
            finally:
                self._closed = True

    def __enter__(self) -> "DatabaseSession":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()


def create_connection(url: Optional[str] = None) -> DatabaseSession:
    """
    Creates and returns a wrapped DatabaseSession connected to PostgreSQL or SQLite:
    - If PostgreSQL URL is provided, connects using psycopg with dict_row.
    - Otherwise connects to local SQLite database with PRAGMA foreign_keys = ON and timeout.
    """
    target_url = url or get_database_url()
    engine = get_database_engine(target_url)

    if engine == "postgresql":
        if not PSYCOPG_AVAILABLE:
            raise ImportError(
                "psycopg is not installed. Run 'pip install psycopg[binary]' to connect to PostgreSQL."
            )
        # Clean postgresql connection with connect_timeout
        raw_conn = psycopg.connect(target_url, row_factory=dict_row, connect_timeout=5)
        return DatabaseSession(raw_conn, engine_type="postgresql")

    else:
        # SQLite connection
        clean_path = target_url
        if clean_path.startswith("sqlite:///"):
            clean_path = clean_path.replace("sqlite:///", "")
        elif clean_path.startswith("sqlite://"):
            clean_path = clean_path.replace("sqlite://", "")
        
        raw_conn = sqlite3.connect(clean_path, timeout=30.0)
        raw_conn.row_factory = dict_factory
        raw_conn.execute("PRAGMA foreign_keys = ON;")
        return DatabaseSession(raw_conn, engine_type="sqlite")


def get_db_connection() -> DatabaseSession:
    """Convenience factory returning an active DatabaseSession."""
    return create_connection()


def get_db_session() -> Generator[DatabaseSession, None, None]:
    """
    FastAPI dependency for database sessions:
    - Injected into routes via `db: DatabaseSession = Depends(get_db_session)`.
    - Automatically commits on successful HTTP response.
    - Automatically rolls back on any unhandled exception.
    - Guarantees `session.close()` in finally block to ensure ZERO connection leaks.
    """
    session = create_connection()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_db() -> Generator[DatabaseSession, None, None]:
    """
    Context manager for repository and service code:
    `with get_db() as conn: ...`
    Commits on normal exit, rolls back on error, always closes connection.
    """
    session = create_connection()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_health() -> bool:
    """Verifies that the configured database is reachable and operational."""
    try:
        with get_db() as session:
            cur = session.execute("SELECT 1 AS alive;")
            row = cur.fetchone()
            return row is not None
    except Exception:
        return False


def get_db_telemetry() -> Dict[str, Any]:
    """Returns database telemetry including engine type, status, and driver availability."""
    db_url = get_database_url()
    engine = get_database_engine(db_url)
    is_healthy = check_db_health()

    return {
        "engine": engine,
        "status": "CONNECTED" if is_healthy else "DISCONNECTED",
        "psycopg_available": PSYCOPG_AVAILABLE,
        "database_url_configured": bool(os.getenv("DATABASE_URL")),
        "postgres_user_configured": bool(POSTGRES_USER),
        "target_host": POSTGRES_HOST if engine == "postgresql" else "local",
        "target_database": POSTGRES_DB if engine == "postgresql" else str(DATABASE_PATH.name)
    }
