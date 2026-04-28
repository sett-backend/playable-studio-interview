"""Configuration loading for agent-wrapper."""

import os
import re
from pathlib import Path
from typing import Any, Dict, Union

import yaml

from agent_wrapper.config.schema import AgentConfig


def load_config(source: Union[str, Path, Dict[str, Any]]) -> AgentConfig:
    """Load config from YAML file path or dict."""
    if isinstance(source, dict):
        return _load_from_dict(source)

    path = Path(source).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return _load_from_dict(data)


def _load_from_dict(data: Dict[str, Any]) -> AgentConfig:
    """Load config from a dictionary, expanding env vars."""
    # Set env vars from config before expansion
    if "env" in data and isinstance(data["env"], dict):
        for key, value in data["env"].items():
            os.environ[key] = str(value)

    # Expand environment variables in all string values
    data = _expand_vars(data)

    # Resolve cwd
    if "runtime" in data and "cwd" in data["runtime"]:
        cwd = data["runtime"]["cwd"]
        if cwd:
            data["runtime"]["cwd"] = str(Path(cwd).resolve())

    config = AgentConfig(**data)
    return config


def _expand_vars(obj: Any) -> Any:
    """Recursively expand ${ENV_VAR} and {ENV_VAR} in strings."""
    if isinstance(obj, str):
        # Expand ${VAR} syntax
        result = os.path.expandvars(obj)
        # Expand {VAR} syntax (but not {{escaped}})
        result = re.sub(
            r"(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)\}(?!\})",
            lambda m: os.environ.get(m.group(1), m.group(0)),
            result,
        )
        return result
    elif isinstance(obj, dict):
        return {k: _expand_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_expand_vars(item) for item in obj]
    return obj
