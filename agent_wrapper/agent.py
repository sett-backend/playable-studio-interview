"""Lightweight Agent wrapper over Claude Agent SDK."""

import asyncio
import atexit
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from agent_wrapper.config.loader import load_config
from agent_wrapper.config.schema import AgentConfig
from agent_wrapper.types import AgentResult, Message, MessageRole, MessageType


class Agent:
    """Minimal wrapper around Claude Agent SDK.

    Usage:
        # From config file
        agent = Agent(config="agent.yaml")
        result = await agent.run("Fix the bug")

        # From kwargs
        agent = Agent(
            model="claude-sonnet-4-6",
            system_prompt="You are helpful.",
            allowed_tools=["Read", "Grep"],
        )
        result = await agent.run("Explain this code")
        print(result.text)

        # Context manager
        async with Agent(config="agent.yaml") as agent:
            result = await agent.run("task")
    """

    def __init__(
        self,
        config: Optional[Union[str, Dict[str, Any], AgentConfig]] = None,
        **kwargs,
    ):
        if config is None and kwargs:
            config = self._build_config(kwargs)
        elif isinstance(config, (str, dict)):
            config = load_config(config)
        elif config is None:
            config = AgentConfig()

        self.config: AgentConfig = config
        self._client = None
        self._connected = False

        # Import SDK
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

            self._ClaudeSDKClient = ClaudeSDKClient
            self._ClaudeAgentOptions = ClaudeAgentOptions
        except ImportError:
            raise ImportError(
                "claude-agent-sdk is not installed. Install with: pip install claude-agent-sdk"
            )

    async def connect(self) -> None:
        """Connect to Claude Agent SDK."""
        if self._connected:
            return

        options = self._build_options()
        self._client = self._ClaudeSDKClient(self._ClaudeAgentOptions(**options))
        await self._client.connect()
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from Claude Agent SDK."""
        if self._client and self._connected:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._connected = False

    async def run(self, prompt: str) -> AgentResult:
        """Run the agent with a prompt and return the result."""
        if not self._connected:
            await self.connect()

        await self._client.query(prompt)
        return await self._collect_messages()

    async def __aenter__(self) -> "Agent":
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        await self.disconnect()

    def _build_config(self, kwargs: Dict[str, Any]) -> AgentConfig:
        """Build AgentConfig from keyword arguments."""
        provider = {
            "model": kwargs.pop("model", None),
            "api_key": kwargs.pop("api_key", None),
        }
        runtime = {
            "timeout": kwargs.pop("timeout", None),
            "permission_mode": kwargs.pop("permission_mode", "bypassPermissions"),
            "cwd": kwargs.pop("cwd", None),
            "max_turns": kwargs.pop("max_turns", None),
        }

        config_dict = {
            "provider": provider,
            "system_prompt": kwargs.pop("system_prompt", None),
            "allowed_tools": kwargs.pop("allowed_tools", None),
            "disallowed_tools": kwargs.pop("disallowed_tools", None),
            "runtime": runtime,
        }
        return AgentConfig(**config_dict)

    def _build_options(self) -> Dict[str, Any]:
        """Build ClaudeAgentOptions dict from config."""
        options: Dict[str, Any] = {}

        # Working directory
        if self.config.runtime.cwd:
            options["cwd"] = str(Path(self.config.runtime.cwd).resolve())
        else:
            options["cwd"] = str(Path.cwd())

        # System prompt
        if self.config.system_prompt:
            options["system_prompt"] = {
                "type": "preset",
                "preset": "claude_code",
                "append": self.config.system_prompt,
            }

        # Permission mode
        options["permission_mode"] = self.config.runtime.permission_mode

        # Model
        if self.config.provider.model:
            options["model"] = self.config.provider.model

        # Tools
        if self.config.allowed_tools:
            options["allowed_tools"] = list(self.config.allowed_tools)
        if self.config.disallowed_tools:
            options["disallowed_tools"] = list(self.config.disallowed_tools)

        # Max turns
        if self.config.runtime.max_turns:
            options["max_turns"] = self.config.runtime.max_turns

        return options

    async def _collect_messages(self) -> AgentResult:
        """Collect messages from the SDK response stream."""
        messages: List[Message] = []
        total_cost = None
        stop_reason = "end_turn"
        metadata: Dict[str, Any] = {}

        async for msg in self._client.receive_response():
            msg_type = type(msg).__name__

            if msg_type == "SystemMessage" or (hasattr(msg, "type") and msg.type == "system"):
                if hasattr(msg, "data") and msg.data.get("session_id"):
                    metadata["session_id"] = msg.data["session_id"]

            elif msg_type == "AssistantMessage":
                if hasattr(msg, "content"):
                    for block in msg.content:
                        if hasattr(block, "text"):
                            messages.append(
                                Message(
                                    role=MessageRole.ASSISTANT,
                                    content=block.text,
                                    type=MessageType.TEXT,
                                )
                            )
                        elif hasattr(block, "name"):
                            messages.append(
                                Message(
                                    role=MessageRole.ASSISTANT,
                                    content=f"[tool_use: {block.name}]",
                                    type=MessageType.TOOL_USE,
                                    metadata={
                                        "tool_name": block.name,
                                        "input": getattr(block, "input", {}),
                                    },
                                )
                            )

            elif msg_type == "ToolResultMessage":
                if hasattr(msg, "content"):
                    content = str(msg.content) if msg.content else ""
                    messages.append(
                        Message(
                            role=MessageRole.TOOL,
                            content=content,
                            type=MessageType.TOOL_RESULT,
                        )
                    )

            elif msg_type == "ResultMessage":
                if hasattr(msg, "stop_reason"):
                    stop_reason = msg.stop_reason or "end_turn"
                if hasattr(msg, "cost_usd"):
                    total_cost = msg.cost_usd
                if hasattr(msg, "usage"):
                    metadata["usage"] = msg.usage

        return AgentResult(
            messages=messages,
            stop_reason=stop_reason,
            total_cost_usd=total_cost,
            metadata=metadata,
        )
