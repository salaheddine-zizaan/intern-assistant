from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


class DBService:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    profile_id TEXT PRIMARY KEY,
                    name TEXT,
                    internship_name TEXT NOT NULL,
                    start_date TEXT,
                    vault_root TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS progress_stats (
                    key TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    profile_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    content TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_state (
                    session_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    last_intent TEXT,
                    pending_action TEXT,
                    pending_payload TEXT,
                    conversation_mode TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
            self._ensure_columns(conn)

    def _ensure_columns(self, conn: sqlite3.Connection) -> None:
        self._ensure_column(conn, "chat_sessions", "profile_id", "TEXT")
        self._ensure_column(conn, "chat_messages", "profile_id", "TEXT")

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, col_type: str) -> None:
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

    def increment_stat(self, key: str, amount: int = 1) -> int:
        current = self.get_stat(key) or 0
        new_value = current + amount
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO progress_stats (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, new_value),
            )
            conn.commit()
        return new_value

    def get_stat(self, key: str) -> Optional[int]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT value FROM progress_stats WHERE key = ?", (key,))
            row = cur.fetchone()
            return row[0] if row else None
