from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from pathlib import Path
import re
from typing import Iterable, Optional


VAULT_STRUCTURE = [
    "Reports",
    "Templates",
]


class ObsidianService:
    def __init__(self, vault_path: Path):
        self.vault_path = Path(vault_path)
        self.ensure_vault()

    def ensure_vault(self) -> None:
        self.vault_path.mkdir(parents=True, exist_ok=True)
        for subpath in VAULT_STRUCTURE:
            (self.vault_path / subpath).mkdir(parents=True, exist_ok=True)

    def write_markdown(self, relative_path: Path, content: str) -> Path:
        full_path = self.vault_path / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return full_path

    def append_markdown(self, relative_path: Path, content: str) -> Path:
        full_path = self.vault_path / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if full_path.exists():
            existing = full_path.read_text(encoding="utf-8").rstrip()
            full_path.write_text(existing + "\n\n" + content, encoding="utf-8")
        else:
            full_path.write_text(content, encoding="utf-8")
        return full_path

    def read_markdown(self, relative_path: Path) -> str:
        full_path = self.vault_path / relative_path
        return full_path.read_text(encoding="utf-8")

    def slugify(self, text: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9\\s-]", "", text).strip().lower()
        normalized = re.sub(r"\\s+", "-", normalized)
        return normalized or "note"

    def timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def build_frontmatter(self, title: str, tags: Optional[Iterable[str]] = None, summary: str | None = None) -> str:
        tags_list = list(tags or [])
        lines = ["---", f"title: {title}", f"date: {datetime.now().date().isoformat()}"]
        if tags_list:
            tags_yaml = "[" + ", ".join(tags_list) + "]"
            lines.append(f"tags: {tags_yaml}")
        if summary:
            lines.append(f"summary: {summary}")
        lines.append("---")
        return "\n".join(lines)

    def parse_date(self, date_input: str | date_type | None) -> date_type:
        if isinstance(date_input, date_type):
            return date_input
        if isinstance(date_input, str) and date_input.strip():
            return datetime.strptime(date_input, "%Y-%m-%d").date()
        return datetime.now().date()

    def week_of_month(self, date_value: date_type) -> int:
        return ((date_value.day - 1) // 7) + 1

    def week_base_path(self, date_input: str | date_type | None) -> Path:
        date_value = self.parse_date(date_input)
        year = f"{date_value.year:04d}"
        month = f"{date_value.month:02d}"
        week = f"Week-{self.week_of_month(date_value)}"
        return Path(year) / month / week

    def ensure_week_folders(self, date_input: str | date_type | None) -> Path:
        base = self.week_base_path(date_input)
        for subdir in ["Meetings", "Tasks", "Progress", "Notes"]:
            (self.vault_path / base / subdir).mkdir(parents=True, exist_ok=True)
        return base

    def week_subpath(self, date_input: str | date_type | None, kind: str) -> Path:
        base = self.ensure_week_folders(date_input)
        return base / kind

    def report_base_path(self, date_input: str | date_type | None) -> Path:
        date_value = self.parse_date(date_input)
        return Path("Reports") / f"{date_value.year:04d}" / f"{date_value.month:02d}"
