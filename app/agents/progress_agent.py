from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from pydantic import BaseModel, Field

from app.services.db_service import DBService
from app.services.llm_service import LLMService
from app.services.obsidian_service import ObsidianService


class DailyProgress(BaseModel):
    summary: str
    done: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)


class WeeklyProgress(BaseModel):
    summary: str
    accomplishments: List[str] = Field(default_factory=list)
    meetings: List[str] = Field(default_factory=list)
    tasks_completed: List[str] = Field(default_factory=list)
    tasks_pending: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    next_week: List[str] = Field(default_factory=list)


@dataclass
class ProgressAgent:
    obsidian: ObsidianService
    db: DBService
    llm: LLMService

    def log_daily(
        self,
        done: List[str],
        blockers: List[str],
        next_steps: List[str],
        date_value: str | None = None,
    ) -> Tuple[Path, Path]:
        date_str = self.obsidian.parse_date(date_value).isoformat()
        progress_base = self.obsidian.week_subpath(date_value, "Progress")
        log_path = progress_base / f"{date_str}.md"

        context = self._build_context(date_value)
        daily = self._generate_daily(
            date_str=date_str,
            done=done,
            blockers=blockers,
            next_steps=next_steps,
            context=context,
        )

        section_lines = [
            "## Summary",
            daily.summary.strip(),
            "",
            "## Highlights",
            *([f"- {item}" for item in daily.highlights] or ["- None noted."]),
            "",
            "## Done",
            *([f"- {item}" for item in daily.done] or ["- None noted."]),
            "",
            "## Blockers",
            *([f"- {item}" for item in daily.blockers] or ["- None noted."]),
            "",
            "## Next Steps",
            *([f"- {item}" for item in daily.next_steps] or ["- None noted."]),
        ]

        if (self.obsidian.vault_path / log_path).exists():
            timestamp = self.obsidian.timestamp()
            update_block = [f"## Update {timestamp}", ""] + section_lines
            content = "\n".join(update_block).rstrip() + "\n"
            self.obsidian.append_markdown(log_path, content)
        else:
            frontmatter = self.obsidian.build_frontmatter(f"Daily Progress {date_str}", ["progress", "daily"])
            header_lines = [frontmatter, "", f"# Daily Progress {date_str}", ""]
            content = "\n".join(header_lines + section_lines).rstrip() + "\n"
            self.obsidian.write_markdown(log_path, content)

        self.db.increment_stat("daily_logs")
        weekly_path = self.generate_weekly(date_value)
        return log_path, weekly_path

    def generate_weekly(self, date_value: str | None = None) -> Path:
        week_base = self.obsidian.week_base_path(self.obsidian.parse_date(date_value))
        progress_base = week_base / "Progress"
        notes_base = week_base / "Notes"
        meetings_base = week_base / "Meetings"
        tasks_base = week_base / "Tasks"

        weekly_path = progress_base / "Weekly-Summary.md"

        context = self._build_context(date_value)
        weekly = self._generate_weekly(context)
        sections = [
            "# Weekly Progress Summary",
            "",
            "## Summary",
            weekly.summary.strip(),
            "",
            "## Accomplishments",
            *([f"- {item}" for item in weekly.accomplishments] or ["- None noted."]),
            "",
            "## Meetings",
            *([f"- {item}" for item in weekly.meetings] or ["- None noted."]),
            "",
            "## Tasks Completed",
            *([f"- {item}" for item in weekly.tasks_completed] or ["- None noted."]),
            "",
            "## Tasks Pending",
            *([f"- {item}" for item in weekly.tasks_pending] or ["- None noted."]),
            "",
            "## Blockers",
            *([f"- {item}" for item in weekly.blockers] or ["- None noted."]),
            "",
            "## Next Week",
            *([f"- {item}" for item in weekly.next_week] or ["- None noted."]),
        ]

        frontmatter = self.obsidian.build_frontmatter(
            "Weekly Progress Summary", ["progress", "weekly"]
        )
        content = "\n".join([frontmatter, ""] + sections).rstrip() + "\n"
        self.obsidian.write_markdown(weekly_path, content)
        return weekly_path

    def _list_files(self, relative_folder: Path) -> List[str]:
        folder = self.obsidian.vault_path / relative_folder
        if not folder.exists():
            return ["- None found."]
        files = sorted(
            [
                p
                for p in folder.rglob("*.md")
                if p.is_file() and p.name.lower() != "weekly-summary.md"
            ]
        )
        if not files:
            return ["- None found."]
        return [f"- {p.relative_to(self.obsidian.vault_path)}" for p in files]

    def _build_context(self, date_value: str | None) -> str:
        week_base = self.obsidian.week_base_path(self.obsidian.parse_date(date_value))
        meetings = self._read_folder(week_base / "Meetings")
        notes = self._read_folder(week_base / "Notes")
        tasks = self._read_folder(week_base / "Tasks")
        progress = self._read_folder(week_base / "Progress")

        done_tasks, pending_tasks = self._extract_tasks(tasks)
        task_summary = f"Tasks completed: {len(done_tasks)}; pending: {len(pending_tasks)}"

        context_parts = [
            "Meetings:",
            meetings or "None.",
            "",
            "Notes:",
            notes or "None.",
            "",
            "Tasks:",
            tasks or "None.",
            "",
            f"{task_summary}",
            "",
            "Progress logs:",
            progress or "None.",
        ]
        return "\n".join(context_parts).strip()

    def _read_folder(self, relative_folder: Path) -> str:
        folder = self.obsidian.vault_path / relative_folder
        if not folder.exists():
            return ""
        contents: List[str] = []
        for file_path in sorted(folder.rglob("*.md")):
            if file_path.is_file() and file_path.name.lower() != "weekly-summary.md":
                contents.append(f"## {file_path.name}\n{file_path.read_text(encoding='utf-8')}")
        return "\n\n".join(contents)

    def _extract_tasks(self, tasks_content: str) -> Tuple[List[str], List[str]]:
        done: List[str] = []
        pending: List[str] = []
        for line in tasks_content.splitlines():
            stripped = line.strip()
            if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
                done.append(stripped[5:].strip())
            elif stripped.startswith("- [ ]"):
                pending.append(stripped[5:].strip())
        return done, pending

    def _generate_daily(
        self,
        date_str: str,
        done: List[str],
        blockers: List[str],
        next_steps: List[str],
        context: str,
    ) -> DailyProgress:
        system_prompt = (
            "You are an internship progress assistant. Create a concise daily progress update "
            "using the provided context from notes, meetings, tasks, and progress logs. "
            "Do not invent facts."
        )
        user_prompt = (
            f"Date: {date_str}\n"
            f"User inputs:\n- Done: {done}\n- Blockers: {blockers}\n- Next steps: {next_steps}\n\n"
            f"Context:\n{context}"
        )
        return self.llm.structured_invoke(system_prompt, user_prompt, DailyProgress)

    def _generate_weekly(self, context: str) -> WeeklyProgress:
        system_prompt = (
            "You are an internship progress assistant. Create a professional weekly summary "
            "for reporting. Use only the provided context. Do not invent facts."
        )
        user_prompt = f"Context:\n{context}"
        return self.llm.structured_invoke(system_prompt, user_prompt, WeeklyProgress)
