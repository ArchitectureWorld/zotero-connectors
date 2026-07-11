"""Command-line client for the Zotero Connector script trigger."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from multiprocessing.connection import Client
from pathlib import Path
from typing import Any

from host_config import HostConfig, default_config_path, load_config


def build_request(action: str, tab_id: int | None, request_id: str | None = None) -> dict[str, Any]:
    request: dict[str, Any] = {
        "id": request_id or str(uuid.uuid4()),
        "action": action,
    }
    if action == "save-tab":
        if tab_id is None:
            raise ValueError("save-tab requires a tab ID")
        if tab_id < 0:
            raise ValueError("tab ID must be non-negative")
        request["tabId"] = tab_id
    return request


def send_request(config: HostConfig, request: dict[str, Any], timeout: float) -> dict[str, Any]:
    if os.name != "nt":
        raise RuntimeError("The V1 script trigger CLI currently supports Windows only")

    connection = Client(config.pipe_name, family="AF_PIPE", authkey=config.authkey)
    try:
        payload = json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        connection.send_bytes(payload)
        if not connection.poll(timeout):
            raise TimeoutError(f"No response from browser extension within {timeout:g} seconds")
        response = json.loads(connection.recv_bytes().decode("utf-8"))
        if not isinstance(response, dict):
            raise RuntimeError("Native host returned a non-object response")
        return response
    finally:
        connection.close()


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Trigger the official Zotero Connector save action without focusing the browser."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config_path(),
        help="Path to generated script-trigger config.json",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="Response timeout in seconds")

    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("ping", help="Check native-host and extension connectivity")
    subparsers.add_parser("save-active", help="Save the selected tab in the last-focused browser window")
    save_tab = subparsers.add_parser("save-tab", help="Save an exact tab ID without activating it")
    save_tab.add_argument("--tab-id", type=int, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        request = build_request(args.action, getattr(args, "tab_id", None))
        response = send_request(config, request, args.timeout)
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0 if response.get("success") else 2
    except Exception as exc:
        print(json.dumps({
            "success": False,
            "error": {"code": type(exc).__name__, "message": str(exc)},
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
