from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from app.services.llm_service import LLMService
from app.services.obsidian_service import ObsidianService


class WeeklyReport(BaseModel):
    title: str
    summary: str
    highlights: List[str] = Field(default_factory=list)
    challenges: List[str] = Field(default_factory=list)
    next_week: List[str] = Field(default_factory=list)


@dataclass
class ReportAgent:
    llm: LLMService
    obsidian: ObsidianService

    def generate_weekly(self, date_value: str | None = None) -> tuple[Path, date]:
        week_ending = self.obsidian.parse_date(date_value)
        start_date = week_ending - timedelta(days=6)

        daily_logs = self._load_daily_logs(start_date, week_ending)
        prompt_context = "\n\n".join(daily_logs) if daily_logs else "No daily logs found."

        system_prompt = (
            "Write a professional weekly internship report in Markdown with clear sections. "
            "Focus on achievements, learning, challenges, and next steps."
        )
        user_prompt = f"Daily logs:\n{prompt_context}"
        report = self.llm.structured_invoke(system_prompt, user_prompt, WeeklyReport)

        title = report.title or f"Weekly Report {week_ending.isoformat()}"
        frontmatter = self.obsidian.build_frontmatter(title, ["report", "weekly"], report.summary)
        lines = [
            frontmatter,
            "",
            f"# {title}",
            "",
            "## Summary",
            report.summary.strip(),
            "",
            "## Highlights",
        ]
        lines.extend([f"- {item}" for item in report.highlights] or ["- None noted."])
        lines.extend(["", "## Challenges"])
        lines.extend([f"- {item}" for item in report.challenges] or ["- None noted."])
        lines.extend(["", "## Next Week"])
        lines.extend([f"- {item}" for item in report.next_week] or ["- None noted."])

        content = "\n".join(lines).rstrip() + "\n"
        report_base = self.obsidian.report_base_path(week_ending)
        report_path = report_base / f"{week_ending.isoformat()}-weekly-report.md"
        self.obsidian.write_markdown(report_path, content)
        return report_path, week_ending

    def _load_daily_logs(self, start: date, end: date) -> List[str]:
        logs = []
        current = start
        while current <= end:
            progress_base = self.obsidian.week_subpath(current, "Progress")
            rel_path = progress_base / f"{current.isoformat()}.md"
            try:
                logs.append(self.obsidian.read_markdown(rel_path))
            except FileNotFoundError:
                pass
            current += timedelta(days=1)
        return logs
