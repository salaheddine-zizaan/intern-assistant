from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.models.schemas import (
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatSessionsResponse,
    CommandRequest,
    CommandResponse,
    ProfileCreateRequest,
    ProfileResponse,
    ProfilesListResponse,
    ProfileSwitchRequest,
    ProfileUpdateRequest,
    MeetingSummarizeRequest,
    MeetingSummarizeResponse,
    NotesOrganizeRequest,
    NotesOrganizeResponse,
    ProgressDailyRequest,
    ProgressDailyResponse,
    ReportWeeklyResponse,
    TaskExtractRequest,
    TaskExtractResponse,
)
from app.orchestrator import Orchestrator
from app.config import DATABASE_PATH, VAULT_PATH
from app.services.profile_service import ProfileService


app = FastAPI(title="Intern Assistant API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
orchestrator = Orchestrator.build()
scheduler = BackgroundScheduler()
profile_service = ProfileService(DATABASE_PATH)


@app.on_event("startup")
def startup_event() -> None:
    scheduler.start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    scheduler.shutdown(wait=False)


@app.post("/notes/organize", response_model=NotesOrganizeResponse)
def organize_notes(payload: NotesOrganizeRequest) -> NotesOrganizeResponse:
    try:
        note_path, title = orchestrator.notes_agent.organize(
            payload.raw_text, payload.category, date_value=payload.date
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return NotesOrganizeResponse(status="ok", note_path=str(note_path), title=title)


@app.post("/tasks/extract", response_model=TaskExtractResponse)
def extract_tasks(payload: TaskExtractRequest) -> TaskExtractResponse:
    if not payload.source_text and not payload.note_path:
        raise HTTPException(status_code=400, detail="source_text or note_path is required")

    if payload.source_text:
        source_text = payload.source_text
    else:
        try:
            source_text = orchestrator.task_agent.obsidian.read_markdown(Path(payload.note_path))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="note_path not found") from exc

    tasks = orchestrator.task_agent.extract_tasks(source_text)
    task_file = orchestrator.task_agent.write_tasks(tasks, date_value=payload.date)
    return TaskExtractResponse(status="ok", task_file=str(task_file), tasks_created=len(tasks))


@app.post("/meetings/summarize", response_model=MeetingSummarizeResponse)
def summarize_meeting(payload: MeetingSummarizeRequest) -> MeetingSummarizeResponse:
    try:
        meeting_path, task_file, tasks_created = orchestrator.meeting_agent.summarize(
            payload.raw_text, date_value=payload.date
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return MeetingSummarizeResponse(
        status="ok",
        meeting_note_path=str(meeting_path),
        tasks_file=str(task_file),
        tasks_created=tasks_created,
    )


@app.post("/progress/daily", response_model=ProgressDailyResponse)
def daily_progress(payload: ProgressDailyRequest) -> ProgressDailyResponse:
    log_path, weekly_path = orchestrator.progress_agent.log_daily(
        done=payload.done,
        blockers=payload.blockers,
        next_steps=payload.next_steps,
        date_value=payload.date,
    )
    return ProgressDailyResponse(
        status="ok",
        daily_log_path=str(log_path),
        weekly_log_path=str(weekly_path),
        message="Progress files created. You can review the daily log and weekly summary.",
    )


@app.post("/reports/weekly", response_model=ReportWeeklyResponse)
def weekly_report() -> ReportWeeklyResponse:
    report_path, week_ending = orchestrator.report_agent.generate_weekly()
    return ReportWeeklyResponse(status="ok", report_path=str(report_path), week_ending=week_ending)


def _parse_progress_text(text: str) -> tuple[list[str], list[str], list[str]]:
    done: list[str] = []
    blockers: list[str] = []
    next_steps: list[str] = []
    current = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("done:"):
            current = "done"
            item = line[5:].strip()
            if item:
                done.append(item)
            continue
        if lower.startswith("blockers:"):
            current = "blockers"
            item = line[9:].strip()
            if item:
                blockers.append(item)
            continue
        if lower.startswith("next:") or lower.startswith("next steps:"):
            current = "next"
            item = line.split(":", 1)[1].strip()
            if item:
                next_steps.append(item)
            continue

        if current == "done":
            done.append(line)
        elif current == "blockers":
            blockers.append(line)
        elif current == "next":
            next_steps.append(line)
        else:
            done.append(line)
    return done, blockers, next_steps


def _llm_error_message(exc: Exception) -> str:
    text = str(exc)
    if "NOT_FOUND" in text and "models/" in text:
        return "Selected model is not available. Choose another model from the selector."
    if "OPENROUTER_API_KEY" in text:
        return (
            "OpenRouter API key missing. Set OPENROUTER_API_KEY in your environment "
            "or in .env.local, then select the OpenRouter model again."
        )
    if "getaddrinfo failed" in text or "ConnectError" in text:
        return "Network error while contacting the model API. Check your internet connection."
    return "LLM request failed. Please try again or change the model."


def _route_action(text: str) -> str:
    lower = text.lower()
    if any(keyword in lower for keyword in ["meeting", "advisor", "sync"]):
        return "meeting_summarize"
    if "report" in lower:
        return "weekly_report"
    if any(keyword in lower for keyword in ["progress", "daily"]):
        return "daily_progress"
    if any(keyword in lower for keyword in ["task", "todo"]):
        return "tasks_extract"
    if "idea" in lower or "brainstorm" in lower:
        return "notes_ideas"
    return "notes_learning"


def _build_pending_payload(text: str, date_value: str | None) -> dict:
    return {
        "action_type": _route_action(text),
        "text": text,
        "date": date_value,
    }


def _execute_pending_action(state: dict, payload: CommandRequest, profile_id: str, session_id: str) -> CommandResponse:
    pending_payload = state.get("pending_payload") or {}
    action_type = pending_payload.get("action_type")
    text = pending_payload.get("text", payload.text)
    date_value = pending_payload.get("date", payload.date)
    actions: list[str] = []
    files: list[str] = []

    if action_type == "meeting_summarize":
        meeting_path, task_file, tasks_created = orchestrator.meeting_agent.summarize(
            text, date_value=date_value
        )
        actions.append("meeting_summarized")
        if tasks_created:
            actions.append("tasks_created")
        files.extend([str(meeting_path), str(task_file)])
        message = "Meeting summarized and tasks updated for the selected week."
    elif action_type == "weekly_report":
        report_path, week_ending = orchestrator.report_agent.generate_weekly(date_value)
        actions.append("weekly_report_generated")
        files.append(str(report_path))
        message = f"Weekly report generated for week ending {week_ending.isoformat()}."
    elif action_type == "daily_progress":
        done, blockers, next_steps = _parse_progress_text(text)
        log_path, weekly_path = orchestrator.progress_agent.log_daily(
            done=done,
            blockers=blockers,
            next_steps=next_steps,
            date_value=date_value,
        )
        actions.extend(["progress_logged", "weekly_progress_generated"])
        files.extend([str(log_path), str(weekly_path)])
        message = "Daily progress logged and weekly summary updated."
    elif action_type == "tasks_extract":
        tasks = orchestrator.task_agent.extract_tasks(text)
        task_file = orchestrator.task_agent.write_tasks(tasks, date_value=date_value)
        actions.append("tasks_created")
        files.append(str(task_file))
        message = "Tasks extracted and saved for the selected week."
    else:
        category = "Ideas" if action_type == "notes_ideas" else "Learning"
        note_path, title = orchestrator.notes_agent.organize(text, category, date_value=date_value)
        actions.append("notes_organized")
        files.append(str(note_path))
        message = f"Note organized for {title}."

    orchestrator.memory.add_message(profile_id, session_id, "assistant", message)
    return CommandResponse(
        status="success",
        actions=actions,
        files=files,
        message=message,
        intent="write_command",
        action="act",
        reason="Confirmed permission",
    )


def _handle_message(payload: CommandRequest) -> CommandResponse:
    text = payload.text.strip()
    lower = text.lower()
    actions: list[str] = []
    files: list[str] = []

    if payload.model:
        try:
            orchestrator.brain.llm.set_model(payload.model)
        except Exception as exc:
            return CommandResponse(
                status="error",
                actions=[],
                files=[],
                message=_llm_error_message(exc),
                intent="conversation",
                action="talk",
                reason="LLM unavailable",
            )

    active_profile = profile_service.get_active_profile()
    if not active_profile:
        return CommandResponse(
            status="success",
            actions=[],
            files=[],
            message="No active profile. Please create or select a profile to continue.",
            intent="conversation",
            action="talk",
            reason="No active profile",
        )
    if not orchestrator.profile or active_profile["profile_id"] != orchestrator.profile["profile_id"]:
        orchestrator.switch_profile(active_profile)
    profile_id = orchestrator.profile["profile_id"]
    session_id = payload.session_id or orchestrator.session_id
    if not session_id:
        session_id = orchestrator.memory.get_or_create_daily_session(profile_id, payload.date)
        orchestrator.session_id = session_id
    history = orchestrator.memory.get_context(profile_id, session_id)
    state = orchestrator.memory.get_state(profile_id, session_id)

    def is_confirmation(message: str) -> bool:
        confirmations = [
            "yes",
            "y",
            "sure",
            "do it",
            "do it.",
            "save it",
            "save",
            "ok",
            "okay",
            "please do",
            "go ahead",
            "confirm",
        ]
        return message.strip().lower() in confirmations

    if state.get("pending_action"):
        if is_confirmation(text):
            orchestrator.memory.add_message(profile_id, session_id, "user", text)
            result = _execute_pending_action(state, payload, profile_id, session_id)
            orchestrator.memory.clear_state(profile_id, session_id)
            return result
        reminder = "I’m waiting for your confirmation. Should I proceed and write to your vault?"
        orchestrator.memory.add_message(profile_id, session_id, "user", text)
        orchestrator.memory.add_message(profile_id, session_id, "assistant", reminder)
        return CommandResponse(
            status="success",
            actions=[],
            files=[],
            message=reminder,
            intent=state.get("last_intent"),
            action="ask",
            reason="Awaiting confirmation",
        )

    if "start a new internship" in lower or "new internship" in lower:
        new_profile = profile_service.create_profile(
            internship_name="New Internship",
            vault_root=orchestrator.profile["vault_root"],
            name="",
            start_date="",
            activate=True,
        )
        orchestrator.switch_profile(new_profile)
        orchestrator.memory.clear_history(new_profile["profile_id"], orchestrator.session_id)
        orchestrator.memory.clear_state(new_profile["profile_id"], orchestrator.session_id)
        return CommandResponse(
            status="success",
            actions=[],
            files=[],
            message="Started a new internship profile. You can tell me the internship name and start date.",
            intent="conversation",
            action="talk",
            reason="Profile reset",
        )

    if "reset this conversation" in lower or "reset conversation" in lower:
        orchestrator.memory.clear_history(profile_id, session_id)
        orchestrator.memory.clear_state(profile_id, session_id)
        return CommandResponse(
            status="success",
            actions=[],
            files=[],
            message="Conversation memory cleared for the active profile.",
            intent="conversation",
            action="talk",
            reason="Memory reset",
        )

    read_only_triggers = [
        "what did i achieve",
        "what did i work on",
        "summarize my progress",
        "what have i done",
        "progress today",
        "today's progress",
        "status update",
    ]
    try:
        if any(trigger in lower for trigger in read_only_triggers):
            decision = orchestrator.brain.decide(text, history=history)
            decision.intent = "read_only"
            decision.action = "talk"
        else:
            decision = orchestrator.brain.decide(text, history=history)
    except Exception as exc:
        return CommandResponse(
            status="error",
            actions=[],
            files=[],
            message=_llm_error_message(exc),
            intent="conversation",
            action="talk",
            reason="LLM unavailable",
        )
    orchestrator.memory.update_state(
        profile_id=profile_id,
        session_id=session_id,
        last_intent=decision.intent,
        conversation_mode=decision.action,
    )
    write_verbs = [
        "save",
        "log",
        "write",
        "organize",
        "create",
        "update",
        "extract",
        "summarize",
        "generate",
    ]
    has_write_verbs = any(verb in lower for verb in write_verbs)

    if decision.intent == "read_only":
        context = orchestrator.reader.build_read_context(payload.date)
        system_prompt = (
            "You are an internship companion. Answer reflective or status questions using only the provided data. "
            "Do not mention file operations or imply changes."
        )
        user_prompt = f"Question: {text}\n\nExisting data:\n{context}"
        try:
            reply = orchestrator.brain.llm.invoke(system_prompt, user_prompt)
        except Exception as exc:
            return CommandResponse(
                status="error",
                actions=[],
                files=[],
                message=_llm_error_message(exc),
                intent=decision.intent,
                action="talk",
                reason="LLM unavailable",
            )
        orchestrator.memory.add_message(profile_id, session_id, "user", text)
        orchestrator.memory.add_message(profile_id, session_id, "assistant", reply)
        return CommandResponse(
            status="success",
            actions=[],
            files=[],
            message=reply,
            intent=decision.intent,
            action="talk",
            reason=decision.reason,
            notice="Answered from existing internship data",
        )

    if decision.action == "talk":
        try:
            reply = orchestrator.brain.respond(text, history=history)
        except Exception as exc:
            return CommandResponse(
                status="error",
                actions=[],
                files=[],
                message=_llm_error_message(exc),
                intent=decision.intent,
                action=decision.action,
                reason="LLM unavailable",
            )
        orchestrator.memory.add_message(profile_id, session_id, "user", text)
        orchestrator.memory.add_message(profile_id, session_id, "assistant", reply)
        return CommandResponse(
            status="success",
            actions=[],
            files=[],
            message=reply,
            intent=decision.intent,
            action=decision.action,
            reason=decision.reason,
        )

    if decision.action == "ask" or (decision.action == "act" and decision.confidence < 0.6):
        question = decision.question or "Do you want me to take an action, or just discuss?"
        orchestrator.memory.add_message(profile_id, session_id, "user", text)
        orchestrator.memory.add_message(profile_id, session_id, "assistant", question)
        return CommandResponse(
            status="success",
            actions=[],
            files=[],
            message=question,
            intent=decision.intent,
            action="ask",
            reason=decision.reason,
        )

    if decision.intent != "write_command" or not has_write_verbs:
        question = "Do you want me to save or update anything in your vault, or just answer in chat?"
        payload_data = _build_pending_payload(text, payload.date)
        orchestrator.memory.update_state(
            profile_id=profile_id,
            session_id=session_id,
            pending_action="write",
            pending_payload=payload_data,
            conversation_mode="ask",
        )
        orchestrator.memory.add_message(profile_id, session_id, "user", text)
        orchestrator.memory.add_message(profile_id, session_id, "assistant", question)
        return CommandResponse(
            status="success",
            actions=[],
            files=[],
            message=question,
            intent=decision.intent,
            action="ask",
            reason="Explicit write permission required",
        )

    orchestrator.memory.add_message(profile_id, session_id, "user", text)

    if any(keyword in lower for keyword in ["pending tasks", "not done", "unfinished tasks", "open tasks"]):
        pending = orchestrator.task_agent.list_pending_tasks(payload.date)
        if pending:
            message = "Pending tasks:\n" + "\n".join(f"- {item}" for item in pending)
        else:
            message = "No pending tasks found for the selected day."
        orchestrator.memory.add_message(profile_id, session_id, "assistant", message)
        return CommandResponse(
            status="success",
            actions=["tasks_listed"],
            files=[],
            message=message,
            intent=decision.intent,
            action=decision.action,
            reason=decision.reason,
        )

    if any(keyword in lower for keyword in ["meeting", "advisor", "sync"]):
        meeting_path, task_file, tasks_created = orchestrator.meeting_agent.summarize(
            text, date_value=payload.date
        )
        actions.append("meeting_summarized")
        if tasks_created:
            actions.append("tasks_created")
        files.extend([str(meeting_path), str(task_file)])
        message = "Meeting summarized and tasks updated for the selected week."
        orchestrator.memory.add_message(profile_id, session_id, "assistant", message)
        return CommandResponse(
            status="success",
            actions=actions,
            files=files,
            message=message,
            intent=decision.intent,
            action=decision.action,
            reason=decision.reason,
        )

    if "report" in lower:
        report_path, week_ending = orchestrator.report_agent.generate_weekly(payload.date)
        actions.append("weekly_report_generated")
        files.append(str(report_path))
        message = f"Weekly report generated for week ending {week_ending.isoformat()}."
        orchestrator.memory.add_message(profile_id, session_id, "assistant", message)
        return CommandResponse(
            status="success",
            actions=actions,
            files=files,
            message=message,
            intent=decision.intent,
            action=decision.action,
            reason=decision.reason,
        )

    if any(keyword in lower for keyword in ["progress", "daily"]):
        done, blockers, next_steps = _parse_progress_text(text)
        log_path, weekly_path = orchestrator.progress_agent.log_daily(
            done=done,
            blockers=blockers,
            next_steps=next_steps,
            date_value=payload.date,
        )
        actions.append("progress_logged")
        actions.append("weekly_progress_generated")
        files.extend([str(log_path), str(weekly_path)])
        message = "Progress files created. You can review the daily log and weekly summary."
        if not blockers:
            message += " Share any blockers to keep the tasks follow-up accurate."
        orchestrator.memory.add_message(profile_id, session_id, "assistant", message)
        return CommandResponse(
            status="success",
            actions=actions,
            files=files,
            message=message,
            intent=decision.intent,
            action=decision.action,
            reason=decision.reason,
        )

    if any(keyword in lower for keyword in ["task", "todo"]):
        tasks = orchestrator.task_agent.extract_tasks(text)
        task_file = orchestrator.task_agent.write_tasks(tasks, date_value=payload.date)
        actions.append("tasks_created")
        files.append(str(task_file))
        message = "Tasks extracted and saved for the selected week."
        orchestrator.memory.add_message(profile_id, session_id, "assistant", message)
        return CommandResponse(
            status="success",
            actions=actions,
            files=files,
            message=message,
            intent=decision.intent,
            action=decision.action,
            reason=decision.reason,
        )

    if "idea" in lower or "brainstorm" in lower:
        note_path, title = orchestrator.notes_agent.organize(text, "Ideas", date_value=payload.date)
    else:
        note_path, title = orchestrator.notes_agent.organize(text, "Learning", date_value=payload.date)
    actions.append("notes_organized")
    files.append(str(note_path))
    message = f"Note organized for {title}."
    orchestrator.memory.add_message(profile_id, session_id, "assistant", message)
    return CommandResponse(
        status="success",
        actions=actions,
        files=files,
        message=message,
        intent=decision.intent,
        action=decision.action,
        reason=decision.reason,
    )


@app.post("/command", response_model=CommandResponse)
def command(payload: CommandRequest) -> CommandResponse:
    return _handle_message(payload)


@app.post("/chat/message", response_model=CommandResponse)
def chat_message(payload: ChatMessageRequest) -> CommandResponse:
    request = CommandRequest(
        text=payload.text,
        date=payload.date,
        session_id=payload.session_id,
        model=payload.model,
    )
    return _handle_message(request)


@app.get("/chat/history", response_model=ChatHistoryResponse)
def chat_history(session_id: str | None = None) -> ChatHistoryResponse:
    active_profile = profile_service.get_active_profile()
    if not active_profile:
        return ChatHistoryResponse(session_id="", messages=[])
    if active_profile and active_profile["profile_id"] != orchestrator.profile["profile_id"]:
        orchestrator.switch_profile(active_profile)
    selected_session = session_id or orchestrator.session_id
    if not selected_session:
        selected_session = orchestrator.memory.get_or_create_daily_session(active_profile["profile_id"])
        orchestrator.session_id = selected_session
    messages = orchestrator.memory.get_history(orchestrator.profile["profile_id"], selected_session)
    return ChatHistoryResponse(session_id=selected_session, messages=messages)


@app.get("/chat/sessions", response_model=ChatSessionsResponse)
def chat_sessions() -> ChatSessionsResponse:
    active_profile = profile_service.get_active_profile()
    if not active_profile:
        return ChatSessionsResponse(active_session_id=None, sessions=[])
    if active_profile and active_profile["profile_id"] != orchestrator.profile["profile_id"]:
        orchestrator.switch_profile(active_profile)
    session_id = orchestrator.session_id
    if not session_id:
        session_id = orchestrator.memory.get_or_create_daily_session(active_profile["profile_id"])
        orchestrator.session_id = session_id
    sessions = orchestrator.memory.list_sessions(active_profile["profile_id"])
    return ChatSessionsResponse(active_session_id=session_id, sessions=sessions)


@app.get("/profiles", response_model=ProfilesListResponse)
def profiles_list() -> ProfilesListResponse:
    profiles = profile_service.list_profiles()
    active = profile_service.get_active_profile()
    return ProfilesListResponse(
        active_profile_id=active["profile_id"] if active else None,
        profiles=[ProfileResponse(**profile) for profile in profiles],
    )


@app.post("/profiles", response_model=ProfileResponse)
def profiles_create(payload: ProfileCreateRequest) -> ProfileResponse:
    default_vault = orchestrator.profile["vault_root"] if orchestrator.profile else str(VAULT_PATH)
    vault_root = payload.vault_root or default_vault
    profile = profile_service.create_profile(
        internship_name=payload.internship_name,
        vault_root=vault_root,
        name=payload.name,
        start_date=payload.start_date,
        activate=True,
    )
    orchestrator.switch_profile(profile)
    welcome_name = payload.name or "there"
    welcome_message = (
        f"Hi {welcome_name}, I’m ready to help you with your {payload.internship_name} internship. "
        "You can start by logging today’s work, summarizing a meeting, or just talking."
    )
    orchestrator.memory.add_message(
        profile["profile_id"], orchestrator.session_id, "assistant", welcome_message
    )
    return ProfileResponse(**profile)


@app.post("/profiles/switch", response_model=ProfileResponse)
def profiles_switch(payload: ProfileSwitchRequest) -> ProfileResponse:
    profile = profile_service.switch_profile(payload.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    orchestrator.switch_profile(profile)
    return ProfileResponse(**profile)


@app.post("/profiles/update", response_model=ProfileResponse)
def profiles_update(payload: ProfileUpdateRequest) -> ProfileResponse:
    profile = profile_service.update_profile(
        profile_id=payload.profile_id,
        name=payload.name,
        internship_name=payload.internship_name,
        start_date=payload.start_date,
        vault_root=payload.vault_root,
    )
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    if orchestrator.profile and orchestrator.profile["profile_id"] == profile["profile_id"]:
        orchestrator.switch_profile(profile)
    return ProfileResponse(**profile)
