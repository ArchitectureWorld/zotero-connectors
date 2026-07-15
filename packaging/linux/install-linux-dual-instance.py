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
        help=(
            "Optional ZZH Chrome --user-data-dir root; "
            "defaults to $XDG_CONFIG_HOME/google-chrome-zzh."
        ),
    )
    parser.add_argument(
        "--nsy-profile-dir",
        type=Path,
        help=(
            "Optional NSY Chrome --user-data-dir root; "
            "defaults to $XDG_CONFIG_HOME/google-chrome-nsy."
        ),
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
    print("\n本地助手、Connector 文件与 Profile 本地 Native Messaging 注册已安装。")
    print("Native Host 注册位置：")
    print(f"   ZZH: {result['profile_manifests']['ZZH']}")
    print(f"   NSY: {result['profile_manifests']['NSY']}")
    print("\nChrome 不会自动启用解压扩展，请完成以下一次性操作：")
    print("1. 分别在 ZZH 和 NSY Chrome Profile 中打开 chrome://extensions。")
    print("2. 开启右上角“开发者模式”。")
    print("3. 点击“加载已解压的扩展程序”，两个 Profile 都选择同一目录：")
    print(f"   {result['extension_directory']}")
    print("4. 确认扩展 ID 为：")
    print(f"   {result['extension_id']}")
    print("5. 在 ZZH Profile 打开并应用：")
    print(f"   {result['settings_pages']['ZZH']}")
    print("6. 在 NSY Profile 打开并应用：")
    print(f"   {result['settings_pages']['NSY']}")
    print("7. 完全退出两个 Chrome 实例并重新启动一次。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
