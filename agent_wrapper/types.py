"""Type definitions for agent-wrapper."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageType(str, Enum):
    TEXT = "text"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


@dataclass
class Message:
    role: MessageRole
    content: str
    type: MessageType = MessageType.TEXT
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result from an agent run."""

    messages: List[Message]
    stop_reason: str
    total_cost_usd: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """Get the last assistant text message."""
        for msg in reversed(self.messages):
            if msg.role == MessageRole.ASSISTANT and msg.type == MessageType.TEXT:
                return msg.content
        return ""
