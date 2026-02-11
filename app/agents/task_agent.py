from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Optional

from pydantic import BaseModel, Field

from app.services.llm_service import LLMService
from app.services.obsidian_service import ObsidianService


class TaskItem(BaseModel):
    description: str
    due_date: Optional[str] = Field(default=None, description="YYYY-MM-DD or null")
    status: str = Field(default="todo", description="todo or done")


class TaskList(BaseModel):
    tasks: List[TaskItem] = Field(default_factory=list)


@dataclass
class TaskAgent:
    llm: LLMService
    obsidian: ObsidianService

    def extract_tasks(self, source_text: str) -> List[TaskItem]:
        system_prompt = (
            "Extract actionable tasks from the text. Prefer short, concrete task descriptions. "
            "Use status 'todo' unless clearly completed."
        )
        user_prompt = f"Text:\n{source_text}"
        result = self.llm.structured_invoke(system_prompt, user_prompt, TaskList)
        return result.tasks

    def write_tasks(
        self,
        tasks: List[TaskItem],
        date_value: str | None = None,
        blockers: Optional[List[str]] = None,
    ) -> Path:
        date_str = self.obsidian.parse_date(date_value).isoformat()
        tasks_base = self.obsidian.week_subpath(date_value, "Tasks")
        task_file = tasks_base / f"{date_str}-tasks.md"
        file_exists = (self.obsidian.vault_path / task_file).exists()
        if file_exists:
            lines = [f"## Extracted Tasks ({date_str})", ""]
        else:
            lines = [
                self.obsidian.build_frontmatter(f"Tasks {date_str}", ["tasks"]),
                "",
                f"# Tasks {date_str}",
                "",
            ]
        if tasks:
            for task in tasks:
                due = f" (due: {task.due_date})" if task.due_date else ""
                checkbox = "[x]" if task.status.lower() == "done" else "[ ]"
                lines.append(f"- {checkbox} {task.description.strip()}{due}")
        else:
            lines.append("- [ ] No tasks extracted.")

        if not file_exists:
            lines.extend(["", "## Blockers"])
            blockers_list = blockers or []
            if blockers_list:
                lines.extend([f"- {item}" for item in blockers_list])
            else:
                lines.append("- None noted.")

        content = "\n".join(lines).rstrip() + "\n"
        if file_exists:
            self.obsidian.append_markdown(task_file, content)
        else:
            self.obsidian.write_markdown(task_file, content)
        return task_file

    def list_pending_tasks(self, date_value: str | None = None) -> List[str]:
        date_str = self.obsidian.parse_date(date_value).isoformat()
        tasks_base = self.obsidian.week_subpath(date_value, "Tasks")
        task_file = tasks_base / f"{date_str}-tasks.md"
        try:
            content = self.obsidian.read_markdown(task_file)
        except FileNotFoundError:
            return []

        pending: List[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("- [ ]"):
                pending.append(stripped[5:].strip())
        return pending

    def mark_tasks_done(self, done_items: List[str], date_value: str | None = None) -> tuple[Optional[Path], int]:
        if not done_items:
            return None, 0
        date_str = self.obsidian.parse_date(date_value).isoformat()
        tasks_base = self.obsidian.week_subpath(date_value, "Tasks")
        task_file = tasks_base / f"{date_str}-tasks.md"
        full_path = self.obsidian.vault_path / task_file
        if not full_path.exists():
            return None, 0

        content = full_path.read_text(encoding="utf-8")
        done_norm = [self._normalize_text(item) for item in done_items if item.strip()]
        if not done_norm:
            return task_file, 0

        updated_lines: List[str] = []
        marked = 0
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("- [ ]"):
                task_text = stripped[5:].strip()
                task_norm = self._normalize_text(task_text)
                if self._matches_done(task_norm, done_norm):
                    indent_match = re.match(r"^\s*", line)
                    indent = indent_match.group(0) if indent_match else ""
                    updated_lines.append(f"{indent}- [x] {task_text}")
                    marked += 1
                    continue
            updated_lines.append(line)

        if marked > 0:
            full_path.write_text("\n".join(updated_lines).rstrip() + "\n", encoding="utf-8")
        return task_file, marked

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = re.sub(r"[^a-z0-9\s]", " ", text.lower())
        return re.sub(r"\s+", " ", normalized).strip()

    def _matches_done(self, task_norm: str, done_norm_list: List[str]) -> bool:
        if not task_norm:
            return False
        for done_norm in done_norm_list:
            if not done_norm:
                continue
            if done_norm in task_norm or task_norm in done_norm:
                return True
            task_tokens = set(task_norm.split())
            done_tokens = set(done_norm.split())
            if len(task_tokens & done_tokens) >= 3:
                return True
        return False
