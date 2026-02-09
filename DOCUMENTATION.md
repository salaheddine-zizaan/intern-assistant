# Intern Assistant Backend Documentation

Last updated: 2026-02-07

## Overview

Local-first, backend-only AI assistant that organizes internship notes, tasks, meetings, progress, and reports.
The Obsidian vault is the primary interface. The backend exposes a FastAPI API for orchestration.

Goals:
- Clean and structure messy notes.
- Extract and manage tasks.
- Summarize meetings and capture decisions/action items.
- Track daily and weekly progress.
- Generate professional weekly internship reports.

Non-goals (MVP):
- No UI, no authentication, no notifications, no cloud storage.

## Tech Stack

- Python 3.11+
- FastAPI
- LangChain (agent logic)
- Gemini via `langchain-google-genai`
- Obsidian vault (Markdown)
- SQLite (metadata)
- APScheduler (future automation hooks)

## Project Layout

```
intern_assistant/
  app/
    main.py
    config.py
    orchestrator.py
    agents/
      notes_agent.py
      task_agent.py
      meeting_agent.py
      progress_agent.py
      report_agent.py
    services/
      obsidian_service.py
      llm_service.py
      db_service.py
    models/
      schemas.py
  vault/
  database/
  tests/
    test_api.py
  requirements.txt
  README.md
  DOCUMENTATION.md
```

## Configuration

Environment variables:
- `GOOGLE_API_KEY` (required)
- `GEMINI_MODEL` (optional, default `gemini-2-flash`)
- `OBSIDIAN_VAULT_PATH` (optional, default `intern_assistant/vault`)
- `DATABASE_PATH` (optional, default `intern_assistant/database/intern_assistant.db`)
- `INTERN_ASSISTANT_ROOT` (optional, default project root)

Example (PowerShell):
```powershell
$env:GOOGLE_API_KEY="your_key"
$env:GEMINI_MODEL="gemini-2-flash"
```

If `GOOGLE_API_KEY` is not set, the server will prompt for it on startup when running in a terminal.
The key is persisted locally in `intern_assistant/.env.local` and reused on restart.

## Profiles & Identity

Profiles scope all data (vault, memory, sessions). Only one profile is active at a time.

Profile fields:
- `profile_id`
- `name`
- `internship_name`
- `start_date`
- `vault_root`
- `active`

Switching profiles changes:
- vault root
- chat session
- memory and agent state

## Onboarding Flow

Frontend loads profiles on startup:
- If no profiles exist, onboarding is shown to collect user + internship info and vault path.
- If profiles exist but none active, profile selector is shown.
- When a profile is created, a welcome message is added to chat history once.

## Obsidian Vault Structure

Created automatically if missing:

```
vault/
  2026/
    02/
      Week-1/
        Meetings/
        Tasks/
        Progress/
        Notes/
      Week-2/
        Meetings/
        Tasks/
        Progress/
        Notes/
  Templates/
  Reports/
```

All notes are Markdown with YAML frontmatter.

Progress logs are stored as:
- Daily logs: `vault/YYYY/MM/Week-N/Progress/YYYY-MM-DD.md`
- Weekly summary: `vault/YYYY/MM/Week-N/Progress/Weekly-Summary.md`

## API Endpoints (MVP)

- `POST /notes/organize`
  - Input: raw messy notes text + category
  - Output: structured Markdown note saved in Obsidian

- `POST /tasks/extract`
  - Input: raw text or note path
  - Output: tasks extracted and written to a daily task file

- `POST /meetings/summarize`
  - Input: raw meeting notes
  - Output: meeting summary note + extracted tasks

- `POST /progress/daily`
  - Input: done / blockers / next steps
  - Output: daily progress log + weekly summary (Markdown)

- `POST /reports/weekly`
  - Output: weekly report (Markdown)

- `POST /command`
  - Input: `{ "text": "user instruction", "date": "YYYY-MM-DD" }`
  - Output: action list + file paths routed to the correct week
  - Behavior: intent-aware. May respond with a question or conversational reply without touching the vault.

- `GET /chat/history`
  - Output: most recent session messages

- `POST /chat/message`
  - Input: `{ "text": "message", "date": "YYYY-MM-DD" }`
  - Output: intent-aware response (may or may not write files)

- `GET /profiles`
  - Output: list of profiles + active profile id

- `POST /profiles`
  - Input: `{ "internship_name": "...", "name": "...", "start_date": "...", "vault_root": "..." }`
  - Output: created profile (set active)

- `POST /profiles/switch`
  - Input: `{ "profile_id": "..." }`
  - Output: active profile

All responses are JSON confirmations with vault-relative paths.

## Agent Architecture

Orchestrator pattern:
- `Orchestrator` is the entry point and coordinates all agents.
- Agents are single-responsibility and return structured output.

Agents:
- `NotesAgent` cleans and structures messy notes, applies templates, saves to vault.
- `TaskAgent` extracts tasks from raw text or notes and writes task Markdown.
- `MeetingAgent` summarizes meetings, extracts decisions/action items, and writes tasks.
- `ProgressAgent` logs daily progress and updates SQLite stats.
- `ReportAgent` generates weekly reports from daily logs.

## Intent-Aware Brain Layer

The `/command` and `/chat/message` routes first call the Brain:
- intent: `conversation`, `command`, or `ambiguous`
- action: `talk`, `act`, or `ask`
- default: talk if unsure

If intent is conversation or ambiguous, the assistant responds without writing files.
Write operations require explicit permission verbs (save/log/write/create/etc.).
If the assistant asks for confirmation, it stores the pending action and executes immediately upon confirmation.

## Services

- `ObsidianService`: Creates vault structure, writes/reads Markdown, builds frontmatter.
- `LLMService`: Wraps Gemini Chat model and supports structured outputs.
- `DBService`: Lightweight SQLite stats storage.
- `MemoryService`: Persists chat sessions and messages in SQLite.
- `ProfileService`: Manages profiles and active context.
- `ReaderService`: Builds read-only context from existing vault data.

Chat memory storage:
- SQLite file: `intern_assistant/database/intern_assistant.db`
- Tables: `chat_sessions`, `chat_messages`
Agent state storage:
- Table: `agent_state`
Profiles storage:
- Table: `profiles`

## Running the API

```powershell
uvicorn app.main:app --reload
```

## Tests

Test file: `intern_assistant/tests/test_api.py`

The test suite uses a fake orchestrator to avoid external API calls and validates:
- `/notes/organize`
- `/tasks/extract`
- `/meetings/summarize`
- `/progress/daily`
- `/reports/weekly`

Run tests:
```powershell
python -m pytest -q
```

Latest test results (2026-02-07):
- Status: PASS
- Summary: `5 passed, 40 warnings in 2.59s`

Warnings:
- FastAPI `@app.on_event` is deprecated. Recommended upgrade is to use lifespan events.
  - Source: `intern_assistant/app/main.py`

## Frontend (Minimal React)

Location: `intern_assistant/frontend`

Features:
- Single-page chat UI
- Sends free-text instructions to `/command`
- Shows status, actions, and vault-relative paths
- Restores chat history on reload
- Template buttons for common commands

Run (from `intern_assistant/frontend`):

```powershell
npm install
npm run dev
```

## Extension Points

- Add new agents under `intern_assistant/app/agents`.
- Add new services under `intern_assistant/app/services`.
- Replace LangChain chains with LangGraph by updating `LLMService` and agent logic.
