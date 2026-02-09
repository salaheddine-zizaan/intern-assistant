from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from app.services.llm_service import LLMService
from app.services.obsidian_service import ObsidianService


class OrganizedNote(BaseModel):
    title: str
    summary: str
    cleaned_markdown: str
    tags: List[str] = Field(default_factory=list)


@dataclass
class NotesAgent:
    llm: LLMService
    obsidian: ObsidianService

    def organize(self, raw_text: str, category: str, date_value: str | None = None) -> tuple[Path, str]:
        normalized_category = category.strip().title()
        if normalized_category not in {"Meetings", "Learning", "Ideas"}:
            normalized_category = "Learning"
        system_prompt = (
            "You clean messy internship notes. Return concise Markdown that is human-readable, "
            "structured with headings and bullet points. Do not invent facts."
        )
        user_prompt = f"Raw notes:\n{raw_text}"
        organized = self.llm.structured_invoke(system_prompt, user_prompt, OrganizedNote)

        title = organized.title.strip()
        frontmatter = self.obsidian.build_frontmatter(title, organized.tags, organized.summary)
        body = f"# {title}\n\n{organized.cleaned_markdown.strip()}"
        content = f"{frontmatter}\n\n{body}\n"

        slug = self.obsidian.slugify(title)
        notes_base = self.obsidian.week_subpath(date_value, "Notes")
        note_path = notes_base / normalized_category / f"{slug}.md"
        self.obsidian.write_markdown(note_path, content)
        return note_path, title
