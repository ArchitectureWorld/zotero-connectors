#!/usr/bin/env python3
"""Install the ZZH and NSY Linux Script Trigger instances for one user."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dual_instance import install_dual_instance

DEFAULT_EXTENSION_ID = "anakemdifclhajhpbjlgfpeokaphddam"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install two isolated Zotero Connector Script Trigger instances."
    )
    parser.add_argument(
        "--extension-id",
        default=DEFAULT_EXTENSION_ID,
        help="Chrome extension ID; defaults to the packaged Connector ID.",
    )
    parser.add_argument(
        "--zzh-profile-dir",
        type=Path,
        help="Optional ZZH Chrome profile path, used only for deployment records.",
    )
    parser.add_argument(
        "--nsy-profile-dir",
        type=Path,
        help="Optional NSY Chrome profile path, used only for deployment records.",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    args = parser.parse_args(argv)

    home = Path.home()
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR", home / ".local" / "run"))
    result = install_dual_instance(
        source_root=args.source_root,
        home=home,
        config_home=config_home,
        runtime_dir=runtime_dir,
        extension_id=args.extension_id,
        zzh_profile_dir=args.zzh_profile_dir,
        nsy_profile_dir=args.nsy_profile_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("\n在两个对应 Chrome Profile 中分别打开 settings_pages 并点击“应用并重载 Connector”。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
