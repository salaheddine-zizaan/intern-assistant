from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.services.obsidian_service import ObsidianService


@dataclass
class ReaderService:
    obsidian: ObsidianService

    def build_read_context(self, date_value: Optional[str] = None) -> str:
        date_str = self.obsidian.parse_date(date_value).isoformat()
        week_base = self.obsidian.week_base_path(self.obsidian.parse_date(date_value))
        progress_base = week_base / "Progress"
        tasks_base = week_base / "Tasks"
        meetings_base = week_base / "Meetings"
        notes_base = week_base / "Notes"

        daily_path = progress_base / f"{date_str}.md"
        tasks_path = tasks_base / f"{date_str}-tasks.md"

        daily = self._safe_read(daily_path)
        tasks = self._safe_read(tasks_path)
        meetings = self._read_folder(meetings_base)
        notes = self._read_folder(notes_base)

        parts = [
            f"Date: {date_str}",
            "",
            "Daily progress log:",
            daily or "None found.",
            "",
            "Tasks for the day:",
            tasks or "None found.",
            "",
            "Meetings this week:",
            meetings or "None found.",
            "",
            "Notes this week:",
            notes or "None found.",
        ]
        return "\n".join(parts).strip()

    def _safe_read(self, relative_path: Path) -> str:
        try:
            return self.obsidian.read_markdown(relative_path)
        except FileNotFoundError:
            return ""

    def _read_folder(self, relative_folder: Path) -> str:
        folder = self.obsidian.vault_path / relative_folder
        if not folder.exists():
            return ""
        contents = []
        for file_path in sorted(folder.rglob("*.md")):
            if file_path.is_file() and file_path.name.lower() != "weekly-summary.md":
                contents.append(f"## {file_path.name}\n{file_path.read_text(encoding='utf-8')}")
        return "\n\n".join(contents)
