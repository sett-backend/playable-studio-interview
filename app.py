"""Sett Chat — simple browser chat UI powered by agent-wrapper."""

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
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


def _persist_user_message(user_msg: str) -> None:
    if not _svc.has_chats():
        _svc.initialize_chats(user_msg)
    else:
        latest = _svc.chat_manager.get_latest_chat_id()
        open_id = latest if latest is not None else "0001"
        _svc.write_chat_response(open_id, user_msg)


def _sse(event: str, data: dict) -> bytes:
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


def _log(line: str) -> None:
    print(line, flush=True)


@app.post("/chat")
async def chat_stream(req: ChatRequest):
    user_msg = req.message
    _persist_user_message(user_msg)

    async def event_stream():
        text_parts: list[str] = []
        cost_usd: float | None = None

        _log(f"━━━ User: {user_msg!r}")

        try:
            await _agent._client.query(user_msg)
            async for msg in _agent._client.receive_response():
                msg_type = type(msg).__name__

                if msg_type == "AssistantMessage":
                    for block in getattr(msg, "content", []) or []:
                        block_type = type(block).__name__
                        if block_type == "ThinkingBlock":
                            thinking = getattr(block, "thinking", "")
                            if thinking:
                                _log(f"<Thinking>\n{thinking}\n</Thinking>")
                        elif hasattr(block, "text") and block.text:
                            text_parts.append(block.text)
                            _log(f"🤖 Assistant: {block.text}")
                        elif hasattr(block, "name"):
                            tool_name = block.name
                            tool_input = getattr(block, "input", {}) or {}
                            _log(f"🔧 Tool use: {tool_name}")
                            if tool_input:
                                _log(f"   Parameters: {json.dumps(tool_input, indent=2, default=str)}")

                elif msg_type == "UserMessage":
                    for block in getattr(msg, "content", []) or []:
                        if hasattr(block, "tool_use_id"):
                            is_error = getattr(block, "is_error", False)
                            content = str(getattr(block, "content", "") or "")
                            if is_error:
                                _log(f"❌ Tool failed: {content[:400]}")
                            else:
                                preview = content if len(content) <= 400 else content[:400] + "…"
                                _log(f"   ↳ Tool result: {preview}")

                elif msg_type == "ResultMessage":
                    cost_usd = getattr(msg, "cost_usd", None)
                    _log(f"━━━ Done (cost_usd={cost_usd})")

            reply = "".join(text_parts)
            _svc.write_chat_request(_svc.next_chat_id(), reply)
            yield _sse("done", {"cost_usd": cost_usd, "reply": reply})
        except Exception as exc:
            _log(f"💥 Stream error: {exc!r}")
            yield _sse("error", {"message": str(exc)})
            raise

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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

    uvicorn.run("app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
