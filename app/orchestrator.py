from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.brain import Brain
from app.agents.meeting_agent import MeetingAgent
from app.agents.notes_agent import NotesAgent
from app.agents.progress_agent import ProgressAgent
from app.agents.report_agent import ReportAgent
from app.agents.task_agent import TaskAgent
from app.config import (
    DATABASE_PATH,
    LOCAL_ENV_PATH,
    VAULT_PATH,
    get_gemini_model,
    get_google_api_key,
)
from app.services.db_service import DBService
from app.services.llm_service import LLMService
from app.services.obsidian_service import ObsidianService
from app.services.memory_service import MemoryService
from app.services.reader_service import ReaderService
from app.services.profile_service import ProfileService


@dataclass
class Orchestrator:
    obsidian: ObsidianService
    notes_agent: NotesAgent
    task_agent: TaskAgent
    meeting_agent: MeetingAgent
    progress_agent: ProgressAgent
    report_agent: ReportAgent
    brain: Brain
    memory: MemoryService
    reader: ReaderService
    session_id: str | None
    profile: dict | None

    def switch_profile(self, profile: dict) -> None:
        self.profile = profile
        self.obsidian.vault_path = Path(profile["vault_root"])
        self.obsidian.ensure_vault()
        self.reader.obsidian = self.obsidian
        self.session_id = self.memory.get_or_create_daily_session(profile["profile_id"])

    @classmethod
    def build(cls) -> "Orchestrator":
        obsidian = ObsidianService(VAULT_PATH)
        llm = LLMService(get_google_api_key(), get_gemini_model(), str(LOCAL_ENV_PATH))
        db = DBService(DATABASE_PATH)
        memory = MemoryService(DATABASE_PATH)
        profile_service = ProfileService(DATABASE_PATH)
        profile = profile_service.get_active_profile()

        task_agent = TaskAgent(llm=llm, obsidian=obsidian)
        notes_agent = NotesAgent(llm=llm, obsidian=obsidian)
        meeting_agent = MeetingAgent(llm=llm, obsidian=obsidian, task_agent=task_agent)
        progress_agent = ProgressAgent(obsidian=obsidian, db=db, llm=llm)
        report_agent = ReportAgent(llm=llm, obsidian=obsidian)
        brain = Brain(llm=llm)
        reader = ReaderService(obsidian=obsidian)
        if profile:
            obsidian.vault_path = Path(profile["vault_root"])
            obsidian.ensure_vault()
            session_id = memory.get_or_create_daily_session(profile["profile_id"])
        else:
            session_id = None

        return cls(
            obsidian=obsidian,
            notes_agent=notes_agent,
            task_agent=task_agent,
            meeting_agent=meeting_agent,
            progress_agent=progress_agent,
            report_agent=report_agent,
            brain=brain,
            memory=memory,
            reader=reader,
            session_id=session_id,
            profile=profile,
        )
