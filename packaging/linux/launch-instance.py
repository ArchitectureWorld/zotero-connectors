#!/usr/bin/env python3
"""Launch the shared Native Messaging host with one explicit instance config."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    config = args.config.expanduser().resolve(strict=False)
    if not config.is_file():
        parser.error(f"config does not exist: {config}")

    host = Path(__file__).resolve().with_name("zotero_script_trigger_host.py")
    if not host.is_file():
        parser.error(f"Native Host does not exist: {host}")

    os.environ["ZOTERO_SCRIPT_TRIGGER_CONFIG"] = str(config)
    os.execv(sys.executable, [sys.executable, str(host)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
