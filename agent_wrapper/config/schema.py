"""Configuration schema for agent-wrapper."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ProviderConfig:
    """Provider configuration."""

    model: Optional[str] = None
    api_key: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeConfig:
    """Runtime configuration."""

    timeout: Optional[int] = None
    permission_mode: str = "bypassPermissions"
    cwd: Optional[str] = None
    max_turns: Optional[int] = None


@dataclass
class AgentConfig:
    """Complete agent configuration."""

    provider: ProviderConfig = field(default_factory=ProviderConfig)
    system_prompt: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    disallowed_tools: Optional[List[str]] = None
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    env: Optional[Dict[str, str]] = None

    def __post_init__(self):
        if isinstance(self.provider, dict):
            self.provider = ProviderConfig(**self.provider)
        if isinstance(self.runtime, dict):
            self.runtime = RuntimeConfig(**self.runtime)
