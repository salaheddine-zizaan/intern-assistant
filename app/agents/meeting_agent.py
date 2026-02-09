from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from app.agents.task_agent import TaskAgent, TaskItem
from app.services.llm_service import LLMService
from app.services.obsidian_service import ObsidianService


class MeetingSummary(BaseModel):
    title: str
    summary: str
    decisions: List[str] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)
    participants: List[str] = Field(default_factory=list)


@dataclass
class MeetingAgent:
    llm: LLMService
    obsidian: ObsidianService
    task_agent: TaskAgent

    def summarize(self, raw_text: str, date_value: str | None = None) -> tuple[Path, Path, int]:
        system_prompt = (
            "Summarize internship meetings. Provide clear decisions and action items. "
            "Do not invent participants."
        )
        user_prompt = f"Meeting notes:\n{raw_text}"
        summary = self.llm.structured_invoke(system_prompt, user_prompt, MeetingSummary)

        title = summary.title.strip()
        frontmatter = self.obsidian.build_frontmatter(title, ["meeting"], summary.summary)
        lines = [
            frontmatter,
            "",
            f"# {title}",
            "",
            "## Summary",
            summary.summary.strip(),
            "",
            "## Decisions",
        ]
        if summary.decisions:
            lines.extend([f"- {item}" for item in summary.decisions])
        else:
            lines.append("- None recorded.")
        lines.extend(["", "## Action Items"])
        if summary.action_items:
            lines.extend([f"- {item}" for item in summary.action_items])
        else:
            lines.append("- None recorded.")
        if summary.participants:
            lines.extend(["", "## Participants"] + [f"- {p}" for p in summary.participants])

        content = "\n".join(lines).rstrip() + "\n"
        slug = self.obsidian.slugify(title)
        meetings_base = self.obsidian.week_subpath(date_value, "Meetings")
        meeting_path = meetings_base / f"{slug}.md"
        self.obsidian.write_markdown(meeting_path, content)

        tasks = [TaskItem(description=item) for item in summary.action_items]
        task_file = self.task_agent.write_tasks(tasks, date_value=date_value)
        return meeting_path, task_file, len(tasks)
