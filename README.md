# Intern Assistant (Backend MVP)

Local-first AI assistant that organizes internship notes, tasks, meetings, progress, and reports using an Obsidian vault as the primary knowledge base.

## Architecture

- FastAPI provides a clean API surface.
- Orchestrator agent routes requests to specialized agents.
- Obsidian vault stores human-readable Markdown with YAML frontmatter.
- SQLite stores lightweight progress stats.
- APScheduler is wired for future automation.

Project layout:

```
intern_assistant/
  app/
    main.py
    config.py
    orchestrator.py
    agents/
    services/
    models/
  vault/
  database/
  requirements.txt
  README.md
```

## Setup

1. Create a virtual environment (Python 3.11+).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set environment variables:

```bash
set GOOGLE_API_KEY=your_key
set GEMINI_MODEL=gemini-2-flash
set OBSIDIAN_VAULT_PATH=path\to\vault  (optional)
set DATABASE_PATH=path\to\database\intern_assistant.db  (optional)
set OLLAMA_BASE_URL=http://localhost:11434  (optional)
```

If `GOOGLE_API_KEY` is not set, the server will prompt for it on startup when running in a terminal.
The key is persisted locally in `intern_assistant/.env.local`.

## Local LLM (Ollama)

You can run the assistant with a local model via Ollama.

Install Ollama (once):

1. Install the Ollama app for your OS.
2. Start the Ollama app (or run `ollama serve`).
3. Pull a model:

```bash
ollama pull llama3.1
```

Then in the UI model selector choose:

- `ollama:llama3.1` (recommended)
- `ollama:phi3`

If Ollama is not installed or running, the API will respond with a message telling you to install
and start Ollama first.

4. Run the API:

```bash
uvicorn app.main:app --reload
```

The vault structure is created automatically at startup if missing:

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
  Reports/
  Templates/
```

## API Endpoints (MVP)

- `POST /notes/organize` -> organize messy notes into structured Markdown.
- `POST /tasks/extract` -> extract tasks from raw text or a note.
- `POST /meetings/summarize` -> summarize meeting notes + tasks.
- `POST /progress/daily` -> create daily progress log.
- `POST /reports/weekly` -> generate weekly internship report.
- `POST /command` -> free-text command router for hybrid vault structure.
  - Intent-aware: may respond without writing files.
- `GET /chat/history` -> returns recent chat history.
- `POST /chat/message` -> intent-aware response, may or may not write files.
- `GET /profiles` -> list profiles and active profile.
- `POST /profiles` -> create a new profile and set active.
- `POST /profiles/switch` -> switch active profile.

The assistant classifies each message as conversation, command, or ambiguous before acting.

All responses are JSON confirmations with paths to Markdown files in the vault.
Daily progress also updates `Weekly-Summary.md` in the same week folder.

Chat memory is stored in `intern_assistant/database/intern_assistant.db` (tables: `chat_sessions`, `chat_messages`).
Agent state is stored in the same SQLite DB (`agent_state`).
Profiles are stored in `profiles` and scope vault + memory.

On startup, the frontend loads profiles:
- No profiles: onboarding appears to collect user + internship info and vault path.
- Profiles exist: profile selector appears if none active.

## Frontend (Optional)

A minimal React frontend is available in `intern_assistant/frontend` and calls `/command`.

## Extension Points

- Add new agents in `intern_assistant/app/agents`.
- Add new services (calendar, email, etc.) in `intern_assistant/app/services`.
- Replace LangChain chains with LangGraph later by updating `LLMService` and agent logic.
