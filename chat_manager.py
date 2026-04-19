"""Chat history persistence. Ported from apollo's ChatManager, task/solution stripped."""

from __future__ import annotations

import json
from typing import Optional

from storage import Storage


class ChatManager:
    """Manages chat history via chats.json + chat/<id>/ folders on disk."""

    def __init__(self, storage: Storage):
        self.storage = storage
        self.chats_key = "chats.json"

    def read_chats(self) -> dict:
        try:
            if self.storage.exists(self.chats_key):
                content = self.storage.get(self.chats_key).read_text(encoding="utf-8")
                return json.loads(content)
            return {"version": 1, "chats": []}
        except Exception as e:
            print(f"Error reading chats.json: {e}")
            return {"version": 1, "chats": []}

    def update_chats(self, chat_entry: dict) -> None:
        try:
            chats_data = self.read_chats()
            chats_data["chats"].append(chat_entry)

            self.storage.put_text(self.chats_key, json.dumps(chats_data, indent=2))

            print(
                f"Updated chats.json: chat_id={chat_entry.get('chat_id')}, "
                f"role={chat_entry.get('role')}"
            )
        except Exception as e:
            print(f"Error updating chats.json: {e}")
            raise

    def initialize_chats(self) -> None:
        try:
            chats_data = {"version": 1, "chats": []}
            self.storage.put_text(self.chats_key, json.dumps(chats_data, indent=2))
            print("Initialized chats.json")
        except Exception as e:
            print(f"Error initializing chats.json: {e}")
            raise

    def get_all_messages(self) -> list[dict]:
        return self.read_chats().get("chats", [])

    def get_latest_chat_id(self) -> Optional[str]:
        try:
            chat_prefix = "chat/"
            chat_keys = list(self.storage.list(chat_prefix))
            chat_ids: set[str] = set()
            for key in chat_keys:
                relative = key.replace(chat_prefix, "", 1)
                if "/" in relative:
                    cid = relative.split("/")[0]
                    if cid.isdigit():
                        chat_ids.add(cid)
            if not chat_ids:
                return None
            return sorted(chat_ids)[-1]
        except Exception as e:
            print(f"Error getting latest chat_id: {e}")
            return None
