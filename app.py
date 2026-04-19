"""Sett Chat — simple browser chat UI powered by agent-wrapper."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from agent_wrapper import Agent
from storage_service import StorageService

# ---------------------------------------------------------------------------
# Agent + storage singletons
# ---------------------------------------------------------------------------

_agent: Agent | None = None
_svc: StorageService | None = None

CHAT_ROOT = Path(__file__).parent / "chat_root"
ENV_PATH = Path(__file__).parent / ".env"


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env(ENV_PATH)


async def _run_initial_task_if_needed() -> None:
    if os.environ.get("SETT_SKIP_AUTO_TASK") == "1":
        return
    task = os.environ.get("MODIFICATION_TASK", "").strip()
    if not task:
        return
    if _svc.has_chats():
        return

    print(f"[auto-task] seeding conversation with MODIFICATION_TASK ({len(task)} chars)")
    _svc.initialize_chats(task)
    result = await _agent.run(task)
    _svc.write_chat_request(_svc.next_chat_id(), result.text)
    print("[auto-task] agent reply written")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent, _svc
    _svc = StorageService(CHAT_ROOT)
    _agent = Agent(
        model="claude-sonnet-4-6",
        system_prompt="You are a helpful assistant. Be concise and clear.",
        permission_mode="bypassPermissions",
    )
    await _agent.connect()
    await _run_initial_task_if_needed()
    yield
    await _agent.disconnect()


app = FastAPI(lifespan=lifespan)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    cost_usd: float | None = None


@app.get("/history")
async def history():
    return {"messages": _svc.read_chat_history()}


@app.get("/playable")
async def playable():
    return {
        "url": os.environ.get("PLAYABLE_URL"),
        "aspect": os.environ.get("PLAYABLE_ASPECT", "9:16"),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    user_msg = req.message

    if not _svc.has_chats():
        _svc.initialize_chats(user_msg)
    else:
        latest = _svc.chat_manager.get_latest_chat_id()
        open_id = latest if latest is not None else "0001"
        _svc.write_chat_response(open_id, user_msg)

    result = await _agent.run(user_msg)
    reply = result.text

    _svc.write_chat_request(_svc.next_chat_id(), reply)

    return ChatResponse(reply=reply, cost_usd=result.total_cost_usd)


def main():
    import argparse
    import shutil
    import uvicorn

    parser = argparse.ArgumentParser(description="Sett Chat server")
    parser.add_argument("--clear", action="store_true", help="Wipe chat_root before starting")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    if args.clear and CHAT_ROOT.exists():
        shutil.rmtree(CHAT_ROOT)
        print(f"Cleared {CHAT_ROOT}")

    if args.reload:
        os.environ["SETT_SKIP_AUTO_TASK"] = "1"

    uvicorn.run("app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
