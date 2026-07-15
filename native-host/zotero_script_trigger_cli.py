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

SAVE_ACTIONS = {"save-active", "save-tab", "save-url", "save-title"}
DEFAULT_LIBRARY_TARGET = "L1"
INSTANCE_IDS = ("ZZH", "NSY")


def _non_empty(value: str | None, label: str) -> str:
    if value is None or not value.strip():
        raise ValueError(f"{label} must be non-empty")
    return value.strip()


def _collection_path(value: str | None) -> str | None:
    if value is None:
        return None
    path = _non_empty(value, "collection")
    segments = [segment.strip() for segment in path.split("/")]
    if any(not segment for segment in segments):
        raise ValueError("collection must not contain empty path segments")
    return "/".join(segments)


def build_request(
    action: str,
    tab_id: int | None = None,
    url: str | None = None,
    contains: str | None = None,
    collection_path: str | None = None,
    library_target: str = DEFAULT_LIBRARY_TARGET,
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

    normalized_collection = _collection_path(collection_path)
    if normalized_collection is not None:
        if action not in SAVE_ACTIONS:
            raise ValueError("collection is supported only for save actions")
        target = _non_empty(library_target, "library-target")
        if not target.startswith("L") or not target[1:].isdigit():
            raise ValueError("library-target must be a Zotero library tree ID such as L1")
        request["collectionPath"] = normalized_collection
        request["libraryTarget"] = target
    return request


def _transport(config: HostConfig) -> tuple[str, str]:
    if os.name == "nt":
        if not config.pipe_name:
            raise RuntimeError("Windows Script Trigger config is missing pipe_name")
        return config.pipe_name, "AF_PIPE"
    if not config.socket_path:
        raise RuntimeError("Linux Script Trigger config is missing socket_path")
    return config.socket_path, "AF_UNIX"


def send_request(config: HostConfig, request: dict[str, Any], timeout: float) -> dict[str, Any]:
    address, family = _transport(config)
    connection = Client(address, family=family, authkey=config.authkey)
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


def _add_collection_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--collection",
        dest="collection_path",
        help="Existing collection path relative to the selected library, e.g. Parent/Child",
    )
    parser.add_argument(
        "--library-target",
        default=DEFAULT_LIBRARY_TARGET,
        help="Zotero library tree ID used with --collection (default: L1)",
    )


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Trigger the official Zotero Connector save action without focusing the browser."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to generated script-trigger config.json",
    )
    parser.add_argument(
        "--instance",
        type=lambda value: value.upper(),
        choices=INSTANCE_IDS,
        help="Linux Connector instance identity (ZZH or NSY)",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="Response timeout in seconds")

    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("ping", help="Check native-host and extension connectivity")
    subparsers.add_parser("list-tabs", help="List saveable HTTP(S) browser tabs")

    save_active = subparsers.add_parser(
        "save-active",
        help="Save the selected tab in the last-focused browser window",
    )
    _add_collection_options(save_active)

    save_tab = subparsers.add_parser("save-tab", help="Save an exact tab ID without activating it")
    save_tab.add_argument("--tab-id", type=int, required=True)
    _add_collection_options(save_tab)

    save_url = subparsers.add_parser("save-url", help="Save one tab selected by URL")
    url_group = save_url.add_mutually_exclusive_group(required=True)
    url_group.add_argument("--url", help="Exact tab URL")
    url_group.add_argument("--contains", help="URL substring; fails if multiple tabs match")
    _add_collection_options(save_url)

    save_title = subparsers.add_parser("save-title", help="Save one tab selected by title substring")
    save_title.add_argument("--contains", required=True, help="Title substring; fails if multiple tabs match")
    _add_collection_options(save_title)
    return parser


def resolve_config(args: argparse.Namespace) -> HostConfig:
    path = args.config or default_config_path(args.instance)
    config = load_config(path, instance_id=args.instance)
    if args.instance and config.instance_id != args.instance:
        raise RuntimeError(
            f"Requested instance {args.instance} does not match config instance {config.instance_id or '(legacy)'}"
        )
    return config


def main(argv: list[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    try:
        config = resolve_config(args)
        request = build_request(
            args.action,
            tab_id=getattr(args, "tab_id", None),
            url=getattr(args, "url", None),
            contains=getattr(args, "contains", None),
            collection_path=getattr(args, "collection_path", None),
            library_target=getattr(args, "library_target", DEFAULT_LIBRARY_TARGET),
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
