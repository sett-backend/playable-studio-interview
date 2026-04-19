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

    def has_chats(self) -> bool:
        return self.storage.exists("chats.json")

    def initialize_chats(self, prompt: str) -> str:
        ts = _utc_ts()
        self.chat_manager.initialize_chats({
            "chat_id": "0000",
            "timestamp": ts,
            "role": "user",
            "message": prompt,
            "attachments": [],
        })
        return ts

    def write_chat_request(self, chat_id: str, message: str) -> str:
        ts = _utc_ts()
        key = f"chat/{chat_id}/request-{ts}/message.txt"
        self.storage.put_text(key, message)
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
        self.storage.put_text(key, message)
        self.chat_manager.update_chats({
            "chat_id": chat_id,
            "timestamp": ts,
            "role": "user",
            "message": message,
            "attachments": [],
        })
        return ts

    def read_chat_history(self) -> list[dict]:
        return self.chat_manager.get_all_messages()

    def next_chat_id(self) -> str:
        latest = self.chat_manager.get_latest_chat_id()
        if latest is None:
            return "0001"
        return f"{int(latest) + 1:04d}"
