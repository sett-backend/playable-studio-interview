"""Sett Chat — simple browser chat UI powered by agent-wrapper."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent_wrapper import Agent
from storage_service import StorageService

# ---------------------------------------------------------------------------
# Agent + storage singletons
# ---------------------------------------------------------------------------

_agent: Agent | None = None
_svc: StorageService | None = None

CHAT_ROOT = Path(__file__).parent / "chat_root"


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
    yield
    await _agent.disconnect()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    cost_usd: float | None = None


@app.get("/", response_class=HTMLResponse)
async def index():
    html = (Path(__file__).parent / "static" / "index.html").read_text()
    return HTMLResponse(content=html)


@app.get("/history")
async def history():
    return {"messages": _svc.read_chat_history()}


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
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
