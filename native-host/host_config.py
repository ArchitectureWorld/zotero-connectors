"""Configuration shared by the native host and CLI."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HostConfig:
    pipe_name: str
    authkey: bytes


def default_config_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    return base / "ZoteroScriptTrigger" / "config.json"


def load_config(path: Path | None = None) -> HostConfig:
    config_path = path or default_config_path()
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        pipe_name = data["pipe_name"]
        authkey = base64.b64decode(data["authkey"], validate=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Script-trigger config not found: {config_path}") from exc
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid script-trigger config: {config_path}: {exc}") from exc

    if not isinstance(pipe_name, str) or not pipe_name.startswith("\\\\.\\pipe\\"):
        raise RuntimeError("Config pipe_name must be a Windows named-pipe path")
    if len(authkey) < 16:
        raise RuntimeError("Config authkey must decode to at least 16 bytes")
    return HostConfig(pipe_name=pipe_name, authkey=authkey)
