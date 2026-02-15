# Electron Desktop Runner

This folder contains a desktop wrapper for Intern Assistant.

## What it does

- Starts the FastAPI backend on `http://127.0.0.1:8000`
- Opens the built frontend (`intern_assistant/frontend/dist/index.html`) in Electron
- In exported `.exe`, frontend and backend are bundled into `resources`

## First-time setup

1. Install backend dependencies:
   - From `intern_assistant`: `pip install -r requirements.txt`
2. Install frontend dependencies:
   - From `intern_assistant/frontend`: `npm install`
3. Build frontend:
   - From `intern_assistant/frontend`: `npm run build`
4. Install Electron dependencies:
   - From `electron`: `npm install`

## Run desktop app

From `electron`:

```bash
npm run start
```

or build frontend + run in one step:

```bash
npm run start:desktop
```

## Export portable Windows build

From `electron`:

```bash
npm run dist:win
```

Output is generated in `electron/release`.

## Runtime note

- The exported app still requires a local Python with backend dependencies installed (`fastapi`, `uvicorn`, etc.).
