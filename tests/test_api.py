from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

from app.services.db_service import DBService
from app.services.obsidian_service import ObsidianService


@dataclass
class BrainFake:
    llm: object

    def decide(self, text: str, history: str = ""):
        class Decision:
            intent = "write_command"
            confidence = 0.9
            action = "act"
            reason = "test"
            question = None

        return Decision()

    def respond(self, text: str, history: str = "") -> str:
        return "test response"


@dataclass
class MemoryFake:
    messages: list

    def get_or_create_daily_session(self, profile_id: str, day: str | None = None) -> str:
        return f"day-{day or 'today'}-{profile_id}"

    def get_context(self, profile_id: str, session_id: str) -> str:
        return ""

    def add_message(self, profile_id: str, session_id: str, role: str, content: str) -> None:
        self.messages.append((profile_id, session_id, role, content))

    def get_history(self, profile_id: str, session_id: str, limit: int = 50):
        return []

    def get_state(self, profile_id: str, session_id: str):
        return {
            "last_intent": None,
            "pending_action": None,
            "pending_payload": None,
            "conversation_mode": None,
        }

    def update_state(self, **kwargs):
        return None

    def clear_state(self, profile_id: str, session_id: str):
        return None

    def clear_history(self, profile_id: str, session_id: str):
        return None


@dataclass
class ReaderFake:
    def build_read_context(self, date_value=None) -> str:
        return ""


@dataclass
class LLMFake:
    model_name: str = "gemini-2.5-flash"
    api_key: str | None = None

    def set_model(self, model_name: str) -> None:
        self.model_name = model_name

    def set_google_api_key(self, api_key: str) -> None:
        self.api_key = api_key

    def set_openrouter_credentials(self, api_key: str | None, base_url: str | None = None) -> None:
        return None


@dataclass
class NotesAgentFake:
    obsidian: ObsidianService

    def organize(self, raw_text: str, category: str, date_value: str | None = None) -> tuple[Path, str]:
        title = "Test Note"
        frontmatter = self.obsidian.build_frontmatter(title, ["test"], "summary")
        body = f"# {title}\n\n{raw_text.strip()}"
        normalized = category.strip().title()
        if normalized not in {"Meetings", "Learning", "Ideas"}:
            normalized = "Learning"
        note_path = Path(f"Notes/{normalized}/test-note.md")
        self.obsidian.write_markdown(note_path, f"{frontmatter}\n\n{body}\n")
        return note_path, title


@dataclass
class TaskAgentFake:
    obsidian: ObsidianService

    def extract_tasks(self, source_text: str):
        return [{"description": "Follow up", "status": "todo", "due_date": None}]

    def write_tasks(self, tasks, date_value: str | None = None) -> Path:
        date_str = self.obsidian.timestamp()
        task_file = Path(f"Tasks/{date_str}-tasks.md")
        lines = [
            self.obsidian.build_frontmatter(f"Tasks {date_str}", ["tasks"]),
            "",
            f"# Tasks {date_str}",
            "",
            "- [ ] Follow up",
        ]
        self.obsidian.write_markdown(task_file, "\n".join(lines).rstrip() + "\n")
        return task_file


@dataclass
class MeetingAgentFake:
    obsidian: ObsidianService
    task_agent: TaskAgentFake

    def summarize(self, raw_text: str, date_value: str | None = None):
        title = "Advisor Sync"
        frontmatter = self.obsidian.build_frontmatter(title, ["meeting"], "summary")
        note_path = Path("Notes/Meetings/advisor-sync.md")
        self.obsidian.write_markdown(note_path, f"{frontmatter}\n\n# {title}\n\n{raw_text}\n")
        task_file = self.task_agent.write_tasks([{"description": "Follow up"}])
        return note_path, task_file, 1


@dataclass
class ProgressAgentFake:
    obsidian: ObsidianService
    db: DBService

    def log_daily(self, done, blockers, next_steps, date_value=None):
        date_str = self.obsidian.timestamp()
        log_path = Path(f"Progress/Daily/{date_str}.md")
        frontmatter = self.obsidian.build_frontmatter(f"Daily Progress {date_str}", ["progress", "daily"])
        self.obsidian.write_markdown(log_path, f"{frontmatter}\n\n# Daily Progress\n")
        self.db.increment_stat("daily_logs")
        weekly_path = Path("Progress/Daily/Weekly-Summary.md")
        self.obsidian.write_markdown(weekly_path, f"{frontmatter}\n\n# Weekly Progress\n")
        return log_path, weekly_path


@dataclass
class ReportAgentFake:
    obsidian: ObsidianService

    def generate_weekly(self):
        date_str = self.obsidian.timestamp()
        report_path = Path(f"Reports/{date_str}.md")
        frontmatter = self.obsidian.build_frontmatter(f"Weekly Report {date_str}", ["report", "weekly"])
        self.obsidian.write_markdown(report_path, f"{frontmatter}\n\n# Weekly Report\n")
        from datetime import datetime

        return report_path, datetime.now().date()


def build_fake_orchestrator(base_path: Path):
    vault_path = base_path / "vault"
    db_path = base_path / "database" / "test.db"
    obsidian = ObsidianService(vault_path)
    db = DBService(db_path)

    task_agent = TaskAgentFake(obsidian=obsidian)
    llm = LLMFake()
    return type(
        "FakeOrchestrator",
        (),
        {
            "obsidian": obsidian,
            "notes_agent": NotesAgentFake(obsidian=obsidian),
            "task_agent": task_agent,
            "meeting_agent": MeetingAgentFake(obsidian=obsidian, task_agent=task_agent),
            "progress_agent": ProgressAgentFake(obsidian=obsidian, db=db),
            "report_agent": ReportAgentFake(obsidian=obsidian),
            "brain": BrainFake(llm=llm),
            "memory": MemoryFake(messages=[]),
            "reader": ReaderFake(),
            "session_id": "test-session",
            "profile": {
                "profile_id": "test-profile",
                "vault_root": str(vault_path),
            },
            "switch_profile": lambda profile: None,
        },
    )()


def create_client(tmp_path, monkeypatch) -> TestClient:
    import app.orchestrator as orchestrator_module

    fake = build_fake_orchestrator(tmp_path)
    monkeypatch.setattr(
        orchestrator_module.Orchestrator, "build", classmethod(lambda cls: fake)
    )

    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    app_main = importlib.import_module("app.main")
    importlib.reload(app_main)
    return TestClient(app_main.app)


def test_notes_organize(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)
    response = client.post(
        "/notes/organize",
        json={"raw_text": "messy notes", "category": "Learning"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["note_path"].endswith(".md")


def test_tasks_extract(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)
    response = client.post("/tasks/extract", json={"source_text": "Do the thing"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["tasks_created"] >= 1


def test_meetings_summarize(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)
    response = client.post("/meetings/summarize", json={"raw_text": "Meeting notes"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["tasks_created"] == 1


def test_progress_daily(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)
    response = client.post(
        "/progress/daily",
        json={"done": ["A"], "blockers": [], "next_steps": ["B"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["daily_log_path"].endswith(".md")
    assert payload["weekly_log_path"].endswith(".md")


def test_reports_weekly(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)
    response = client.post("/reports/weekly")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["report_path"].endswith(".md")


def test_model_settings_roundtrip(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)
    post = client.post(
        "/settings/models",
        json={
            "selected_model": "gemini-2-flash",
            "google_api_key": "test-google-key",
            "openrouter_api_key": "test-openrouter-key",
            "openrouter_base_url": "https://openrouter.ai/api/v1",
        },
    )
    assert post.status_code == 200
    updated = post.json()
    assert updated["selected_model"] == "gemini-2-flash"
    assert updated["google_api_key_configured"] is True
    assert updated["openrouter_api_key_configured"] is True

    get_response = client.get("/settings/models")
    assert get_response.status_code == 200
    settings = get_response.json()
    assert settings["selected_model"] == "gemini-2-flash"
