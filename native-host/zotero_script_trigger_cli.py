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


def _non_empty(value: str | None, label: str) -> str:
    if value is None or not value.strip():
        raise ValueError(f"{label} must be non-empty")
    return value.strip()


def build_request(
    action: str,
    tab_id: int | None = None,
    url: str | None = None,
    contains: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
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
    elif action == "save-url":
        has_url = url is not None and bool(url.strip())
        has_contains = contains is not None and bool(contains.strip())
        if has_url == has_contains:
            raise ValueError("save-url requires exactly one of url or contains")
        if has_url:
            request["url"] = _non_empty(url, "url")
        else:
            request["urlContains"] = _non_empty(contains, "contains")
    elif action == "save-title":
        request["titleContains"] = _non_empty(contains, "contains")
    return request


def send_request(config: HostConfig, request: dict[str, Any], timeout: float) -> dict[str, Any]:
    if os.name != "nt":
        raise RuntimeError("The script trigger CLI currently supports Windows only")

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
    subparsers.add_parser("list-tabs", help="List saveable HTTP(S) browser tabs")
    subparsers.add_parser("save-active", help="Save the selected tab in the last-focused browser window")

    save_tab = subparsers.add_parser("save-tab", help="Save an exact tab ID without activating it")
    save_tab.add_argument("--tab-id", type=int, required=True)

    save_url = subparsers.add_parser("save-url", help="Save one tab selected by URL")
    url_group = save_url.add_mutually_exclusive_group(required=True)
    url_group.add_argument("--url", help="Exact tab URL")
    url_group.add_argument("--contains", help="URL substring; fails if multiple tabs match")

    save_title = subparsers.add_parser("save-title", help="Save one tab selected by title substring")
    save_title.add_argument("--contains", required=True, help="Title substring; fails if multiple tabs match")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        request = build_request(
            args.action,
            tab_id=getattr(args, "tab_id", None),
            url=getattr(args, "url", None),
            contains=getattr(args, "contains", None),
        )
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
