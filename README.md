# playable-studio-interview

**Playable Studio** — a chat UI for iterating on a playable with a developer agent. The left pane is the chat; the right pane is a live iframe of the playable being edited.

- **Backend:** FastAPI (`app.py`), port `8000`
- **Frontend:** React + Vite (`frontend/`), port `5173`
- **Agent:** `agent_wrapper/` — a small wrapper around the Claude Agent SDK, vendored into this repo

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- An `ANTHROPIC_API_KEY`
- A running playable server (by default, something serving at `http://localhost:3000`)

## Configuration

Create a `.env` file (or export the variables in your shell):

```bash
ANTHROPIC_API_KEY=sk-ant-...
PLAYABLE_URL=http://localhost:3000   # URL the right-pane iframe loads
PLAYABLE_ASPECT=9:16                 # aspect ratio of the preview pane
```

## Install

### Backend

```bash
cd playable-studio-interview
pip install -e .
```

This installs the backend along with the embedded `agent_wrapper` package.

### Frontend

```bash
cd playable-studio-interview/frontend
npm install
```

## Run

You need **three** processes running at the same time: the playable, the backend, and the frontend.

### 1. Playable server

Start whatever serves your playable on `PLAYABLE_URL` (default `http://localhost:3000`).

### 2. Backend

```bash
cd playable-studio-interview
python app.py --clear
```

Options:

| Flag | Default | Notes |
|---|---|---|
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8000` | Backend port |
| `--reload` | off | Auto-reload on code changes |
| `--clear` | off | Wipe `chat_root/` on start |

### 3. Frontend

```bash
cd playable-studio-interview/frontend
npm run dev
```

Vite proxies `/chat`, `/history`, and `/playable` to the backend, so you only visit the frontend URL.

Open **http://localhost:5173**.

## How it fits together

```
[Frontend :5173] ──(vite proxy)──> [Backend :8000] ──> [agent_wrapper] ──> Claude
       │                                                         │
       └── iframe ─────────────────> [Playable :3000] <─── agent file edits
```

Chats are persisted to `chat_root/` on disk.

## Troubleshooting

- **Blank right pane:** check `PLAYABLE_URL` is reachable and the playable server is running.
- **401 / auth errors in backend logs:** `ANTHROPIC_API_KEY` is missing or invalid.
- **Stale frontend proxy:** restart `npm run dev` after changing backend ports.
