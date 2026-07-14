"""Configuration shared by the Native Messaging host and CLI."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


INSTANCE_ROUTES = {
    "ZZH": {
        "native_host_name": "org.zotero.script_trigger.zzh",
        "connector_url": "http://127.0.0.1:23119/",
    },
    "NSY": {
        "native_host_name": "org.zotero.script_trigger.nsy",
        "connector_url": "http://127.0.0.1:23120/",
    },
}


@dataclass(frozen=True)
class HostConfig:
    authkey: bytes
    pipe_name: str | None = None
    socket_path: str | None = None
    instance_id: str | None = None
    native_host_name: str | None = None
    connector_url: str | None = None


def _value(data: dict, snake: str, camel: str | None = None):
    if snake in data:
        return data[snake]
    if camel and camel in data:
        return data[camel]
    return None


def _normalize_instance_id(value: object) -> str | None:
    if value is None or value == "":
        return None
    instance_id = str(value).strip().upper()
    if instance_id not in INSTANCE_ROUTES:
        raise RuntimeError("Config instance_id must be ZZH or NSY")
    return instance_id


def _normalize_connector_url(value: object) -> str | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    try:
        parsed = urlsplit(text)
    except ValueError as exc:
        raise RuntimeError("Config connector_url must be a valid URL") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.port is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError(
            "Config connector_url must be http://127.0.0.1:<port>/ with no path, query, or fragment"
        )
    return f"http://127.0.0.1:{parsed.port}/"


def default_config_path(
    instance_id: str | None = None,
    *,
    os_name: str | None = None,
    environ: dict[str, str] | None = None,
) -> Path:
    env = os.environ if environ is None else environ
    override = str(env.get("ZOTERO_SCRIPT_TRIGGER_CONFIG", "")).strip()
    if override:
        return Path(override).expanduser()

    platform = os.name if os_name is None else os_name
    if platform == "nt":
        base = Path(env.get("LOCALAPPDATA", Path.home()))
        return base / "ZoteroScriptTrigger" / "config.json"

    selected = instance_id or env.get("ZOTERO_SCRIPT_TRIGGER_INSTANCE")
    if not selected:
        raise RuntimeError("Linux Script Trigger requires --instance ZZH|NSY or --config")
    normalized = _normalize_instance_id(selected)
    config_home = Path(env.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_home / "zotero-script-trigger" / f"{normalized.lower()}.json"


def load_config(path: Path | None = None, *, instance_id: str | None = None) -> HostConfig:
    config_path = path or default_config_path(instance_id)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        authkey = base64.b64decode(data["authkey"], validate=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Script-trigger config not found: {config_path}") from exc
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid script-trigger config: {config_path}: {exc}") from exc

    pipe_name = _value(data, "pipe_name", "pipeName")
    socket_path = _value(data, "socket_path", "socketPath")
    selected_instance = _normalize_instance_id(
        _value(data, "instance_id", "instanceId") or instance_id
    )
    native_host_name = _value(data, "native_host_name", "nativeHostName")
    connector_url = _normalize_connector_url(
        _value(data, "connector_url", "connectorUrl")
    )

    if bool(pipe_name) == bool(socket_path):
        raise RuntimeError("Config must define exactly one of pipe_name or socket_path")

    if pipe_name is not None:
        if not isinstance(pipe_name, str) or not pipe_name.startswith("\\\\.\\pipe\\"):
            raise RuntimeError("Config pipe_name must be a Windows named-pipe path")
        pipe_name = pipe_name.strip()

    if socket_path is not None:
        if not isinstance(socket_path, str) or not socket_path.strip():
            raise RuntimeError("Config socket_path must be a non-empty absolute path")
        expanded = Path(socket_path).expanduser()
        if not expanded.is_absolute():
            raise RuntimeError("Config socket_path must be an absolute path")
        socket_path = str(expanded)

    if len(authkey) < 16:
        raise RuntimeError("Config authkey must decode to at least 16 bytes")

    if selected_instance is not None:
        expected = INSTANCE_ROUTES[selected_instance]
        if native_host_name != expected["native_host_name"]:
            raise RuntimeError(
                f"Config {selected_instance} native_host_name must be {expected['native_host_name']}"
            )
        if connector_url != expected["connector_url"]:
            raise RuntimeError(
                f"Config {selected_instance} connector_url must be {expected['connector_url']}"
            )
        if socket_path is None:
            raise RuntimeError("Linux instance configuration requires socket_path")
    elif socket_path is not None:
        raise RuntimeError("Unix socket configuration requires instance_id")

    return HostConfig(
        authkey=authkey,
        pipe_name=pipe_name,
        socket_path=socket_path,
        instance_id=selected_instance,
        native_host_name=(str(native_host_name).strip() if native_host_name else None),
        connector_url=connector_url,
    )
