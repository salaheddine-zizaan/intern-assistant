from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import List, Dict, Optional


@dataclass
class ProfileService:
    db_path: Path

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def get_active_profile(self) -> Optional[Dict[str, str]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT profile_id, name, internship_name, start_date, vault_root, active "
                "FROM profiles WHERE active = 1 LIMIT 1"
            ).fetchone()
        return self._row_to_profile(row) if row else None

    def list_profiles(self) -> List[Dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT profile_id, name, internship_name, start_date, vault_root, active "
                "FROM profiles ORDER BY internship_name ASC"
            ).fetchall()
        return [self._row_to_profile(row) for row in rows]

    def create_profile(
        self,
        internship_name: str,
        vault_root: str,
        name: Optional[str] = None,
        start_date: Optional[str] = None,
        activate: bool = True,
    ) -> Dict[str, str]:
        profile_id = datetime.now().strftime("profile-%Y%m%d-%H%M%S")
        with self._connect() as conn:
            if activate:
                conn.execute("UPDATE profiles SET active = 0")
            conn.execute(
                "INSERT INTO profiles (profile_id, name, internship_name, start_date, vault_root, active) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (profile_id, name, internship_name, start_date, vault_root, 1 if activate else 0),
            )
            conn.commit()
        return {
            "profile_id": profile_id,
            "name": name or "",
            "internship_name": internship_name,
            "start_date": start_date or "",
            "vault_root": vault_root,
            "active": 1 if activate else 0,
        }

    def switch_profile(self, profile_id: str) -> Optional[Dict[str, str]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT profile_id FROM profiles WHERE profile_id = ?", (profile_id,)
            ).fetchone()
            if not row:
                return None
            conn.execute("UPDATE profiles SET active = 0")
            conn.execute("UPDATE profiles SET active = 1 WHERE profile_id = ?", (profile_id,))
            conn.commit()
        return self.get_active_profile()

    def update_profile(
        self,
        profile_id: str,
        name: Optional[str] = None,
        internship_name: Optional[str] = None,
        start_date: Optional[str] = None,
        vault_root: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        fields = []
        values = []
        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if internship_name is not None:
            fields.append("internship_name = ?")
            values.append(internship_name)
        if start_date is not None:
            fields.append("start_date = ?")
            values.append(start_date)
        if vault_root is not None:
            fields.append("vault_root = ?")
            values.append(vault_root)
        if not fields:
            return self.get_active_profile()
        values.append(profile_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE profiles SET {', '.join(fields)} WHERE profile_id = ?",
                values,
            )
            conn.commit()
        return self.get_profile(profile_id)

    def get_profile(self, profile_id: str) -> Optional[Dict[str, str]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT profile_id, name, internship_name, start_date, vault_root, active "
                "FROM profiles WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
        return self._row_to_profile(row) if row else None

    def ensure_default_profile(self, vault_root: str) -> Dict[str, str]:
        active = self.get_active_profile()
        if active:
            return active
        return self.create_profile(
            internship_name="Default Internship",
            vault_root=vault_root,
            name="",
            start_date="",
            activate=True,
        )

    def _row_to_profile(self, row) -> Dict[str, str]:
        return {
            "profile_id": row[0],
            "name": row[1] or "",
            "internship_name": row[2],
            "start_date": row[3] or "",
            "vault_root": row[4],
            "active": row[5],
        }
