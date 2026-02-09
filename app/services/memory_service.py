from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import List, Dict, Optional
import json


@dataclass
class MemoryService:
    db_path: Path

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def get_or_create_latest_session(self, profile_id: str) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT session_id FROM chat_sessions WHERE profile_id = ? "
                "ORDER BY updated_at DESC LIMIT 1",
                (profile_id,),
            ).fetchone()
            if row:
                return row[0]
            session_id = datetime.now().strftime("session-%Y%m%d-%H%M%S")
            now = datetime.now().isoformat()
            conn.execute(
                "INSERT INTO chat_sessions (session_id, profile_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, profile_id, now, now),
            )
            conn.commit()
            return session_id

    def update_session_timestamp(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
                (datetime.now().isoformat(), session_id),
            )
            conn.commit()

    def add_message(self, profile_id: str, session_id: str, role: str, content: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO chat_messages (session_id, profile_id, role, timestamp, content) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, profile_id, role, datetime.now().isoformat(), content),
            )
            conn.commit()
        self.update_session_timestamp(session_id)

    def get_history(self, profile_id: str, session_id: str, limit: int = 50) -> List[Dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, timestamp, content FROM chat_messages "
                "WHERE session_id = ? AND profile_id = ? ORDER BY id ASC LIMIT ?",
                (session_id, profile_id, limit),
            ).fetchall()
        return [
            {"role": row[0], "timestamp": row[1], "content": row[2]} for row in rows
        ]

    def get_context(self, profile_id: str, session_id: str, limit: int = 12) -> str:
        messages = self.get_history(profile_id, session_id, limit=limit)
        lines = []
        for msg in messages:
            lines.append(f"{msg['role']}: {msg['content']}")
        return "\n".join(lines).strip()

    def clear_history(self, profile_id: str, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM chat_messages WHERE session_id = ? AND profile_id = ?",
                (session_id, profile_id),
            )
            conn.commit()

    def get_state(self, profile_id: str, session_id: str) -> Dict[str, str | None]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT last_intent, pending_action, pending_payload, conversation_mode "
                "FROM agent_state WHERE session_id = ? AND profile_id = ?",
                (session_id, profile_id),
            ).fetchone()
        if not row:
            return {
                "last_intent": None,
                "pending_action": None,
                "pending_payload": None,
                "conversation_mode": None,
            }
        payload = row[2]
        parsed_payload = None
        if payload:
            try:
                parsed_payload = json.loads(payload)
            except json.JSONDecodeError:
                parsed_payload = None
        return {
            "last_intent": row[0],
            "pending_action": row[1],
            "pending_payload": parsed_payload,
            "conversation_mode": row[3],
        }

    def update_state(
        self,
        profile_id: str,
        session_id: str,
        last_intent: Optional[str] = None,
        pending_action: Optional[str] = None,
        pending_payload: Optional[dict] = None,
        conversation_mode: Optional[str] = None,
    ) -> None:
        payload_text = json.dumps(pending_payload) if pending_payload is not None else None
        with self._connect() as conn:
            exists = conn.execute(
                "SELECT session_id FROM agent_state WHERE session_id = ? AND profile_id = ?",
                (session_id, profile_id),
            ).fetchone()
            if exists:
                conn.execute(
                    "UPDATE agent_state SET last_intent = ?, pending_action = ?, "
                    "pending_payload = ?, conversation_mode = ?, updated_at = ? "
                    "WHERE session_id = ? AND profile_id = ?",
                    (
                        last_intent,
                        pending_action,
                        payload_text,
                        conversation_mode,
                        datetime.now().isoformat(),
                        session_id,
                        profile_id,
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO agent_state (session_id, profile_id, last_intent, pending_action, "
                    "pending_payload, conversation_mode, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        session_id,
                        profile_id,
                        last_intent,
                        pending_action,
                        payload_text,
                        conversation_mode,
                        datetime.now().isoformat(),
                    ),
                )
            conn.commit()

    def clear_state(self, profile_id: str, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM agent_state WHERE session_id = ? AND profile_id = ?",
                (session_id, profile_id),
            )
            conn.commit()
