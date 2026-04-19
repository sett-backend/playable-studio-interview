"""Storage service — mirrors apollo-backend's StorageService, chat-only."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from chat_manager import ChatManager
from storage import Storage


def _utc_ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S") + "Z"


class StorageService:
    def __init__(self, root: Path):
        self.storage = Storage(root)
        self.chat_manager = ChatManager(self.storage)

    TASK_DESCRIPTION_KEY = "task_input/task_description.txt"

    def has_chats(self) -> bool:
        return self.storage.exists("chats.json")

    def initialize_chats(self, prompt: str) -> str:
        ts = _utc_ts()
        tmp = Path(f"/tmp/sett_chat_task_description.txt")
        tmp.write_text(prompt, encoding="utf-8")
        self.storage.put(self.TASK_DESCRIPTION_KEY, str(tmp))
        tmp.unlink()
        self.chat_manager.initialize_chats()
        return ts

    def read_task_description(self) -> str | None:
        if not self.storage.exists(self.TASK_DESCRIPTION_KEY):
            return None
        return self.storage.get(self.TASK_DESCRIPTION_KEY).read_text(encoding="utf-8")

    def write_chat_request(self, chat_id: str, message: str) -> str:
        ts = _utc_ts()
        key = f"chat/{chat_id}/request-{ts}/message.txt"
        tmp = Path(f"/tmp/sett_chat_{chat_id}_req.txt")
        tmp.write_text(message, encoding="utf-8")
        self.storage.put(key, str(tmp))
        tmp.unlink()
        self.chat_manager.update_chats({
            "chat_id": chat_id,
            "timestamp": ts,
            "role": "agent",
            "message": message,
            "attachments": [],
        })
        return ts

    def write_chat_response(self, chat_id: str, message: str) -> str:
        ts = _utc_ts()
        key = f"chat/{chat_id}/response-{ts}/message.txt"
        tmp = Path(f"/tmp/sett_chat_{chat_id}_resp.txt")
        tmp.write_text(message, encoding="utf-8")
        self.storage.put(key, str(tmp))
        tmp.unlink()
        self.chat_manager.update_chats({
            "chat_id": chat_id,
            "timestamp": ts,
            "role": "user",
            "message": message,
            "attachments": [],
        })
        return ts

    def read_chat_history(self) -> list[dict]:
        messages: list[dict] = []
        task_description = self.read_task_description()
        if task_description is not None:
            messages.append({
                "chat_id": "task_description",
                "role": "user",
                "message": task_description,
                "attachments": [],
            })
        messages.extend(self.chat_manager.get_all_messages())
        return messages

    def next_chat_id(self) -> str:
        latest = self.chat_manager.get_latest_chat_id()
        if latest is None:
            return "0001"
        return f"{int(latest) + 1:04d}"
