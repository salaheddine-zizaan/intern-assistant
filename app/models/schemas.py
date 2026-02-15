from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class NotesOrganizeRequest(BaseModel):
    raw_text: str = Field(..., description="Raw messy notes text")
    category: str = Field("Learning", description="Notes subfolder: Meetings, Learning, Ideas")
    date: Optional[str] = Field(None, description="YYYY-MM-DD to route into week folder")


class NotesOrganizeResponse(BaseModel):
    status: str
    note_path: str
    title: str


class TaskExtractRequest(BaseModel):
    source_text: Optional[str] = Field(None, description="Raw text to extract tasks from")
    note_path: Optional[str] = Field(None, description="Existing note path in vault to extract tasks from")
    date: Optional[str] = Field(None, description="YYYY-MM-DD to route into week folder")


class TaskExtractResponse(BaseModel):
    status: str
    task_file: str
    tasks_created: int


class MeetingSummarizeRequest(BaseModel):
    raw_text: str = Field(..., description="Raw meeting notes")
    date: Optional[str] = Field(None, description="YYYY-MM-DD to route into week folder")


class MeetingSummarizeResponse(BaseModel):
    status: str
    meeting_note_path: str
    tasks_file: str
    tasks_created: int


class ProgressDailyRequest(BaseModel):
    done: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    date: Optional[str] = Field(None, description="YYYY-MM-DD to route into week folder")


class ProgressDailyResponse(BaseModel):
    status: str
    daily_log_path: str
    weekly_log_path: str
    message: Optional[str] = None


class ProgressCacheResponse(BaseModel):
    cache_path: str
    last_entry: str
    updated_at: str


class ReportWeeklyResponse(BaseModel):
    status: str
    report_path: str
    week_ending: date


class CommandRequest(BaseModel):
    text: str = Field(..., description="Free-text instruction")
    date: Optional[str] = Field(None, description="YYYY-MM-DD to route into week folder")
    session_id: Optional[str] = Field(None, description="Chat session id")
    model: Optional[str] = Field(None, description="LLM model override")


class CommandResponse(BaseModel):
    status: str
    actions: List[str]
    files: List[str]
    message: str
    intent: Optional[str] = None
    action: Optional[str] = None
    reason: Optional[str] = None
    notice: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[dict]


class ChatSessionsResponse(BaseModel):
    active_session_id: Optional[str] = None
    sessions: List[dict]


class ChatMessageRequest(BaseModel):
    text: str
    date: Optional[str] = None
    session_id: Optional[str] = None
    model: Optional[str] = None


class ProfileCreateRequest(BaseModel):
    internship_name: str
    vault_root: Optional[str] = None
    name: Optional[str] = None
    start_date: Optional[str] = None


class ProfileSwitchRequest(BaseModel):
    profile_id: str


class ProfileResponse(BaseModel):
    profile_id: str
    name: str
    internship_name: str
    start_date: str
    vault_root: str
    active: int


class ProfilesListResponse(BaseModel):
    active_profile_id: Optional[str]
    profiles: List[ProfileResponse]


class ProfileUpdateRequest(BaseModel):
    profile_id: str
    name: Optional[str] = None
    internship_name: Optional[str] = None
    start_date: Optional[str] = None
    vault_root: Optional[str] = None


class ModelSettingsResponse(BaseModel):
    selected_model: str
    available_models: List[str]
    google_api_key_configured: bool
    openrouter_api_key_configured: bool
    openrouter_base_url: str


class ModelSettingsUpdateRequest(BaseModel):
    selected_model: Optional[str] = None
    google_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: Optional[str] = None
