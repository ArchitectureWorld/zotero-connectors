#!/usr/bin/env python3
"""Remove files managed by the Linux dual-instance installer."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dual_instance import uninstall_dual_instance


def main() -> int:
    home = Path.home()
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR", home / ".local" / "run"))
    removed = uninstall_dual_instance(
        home=home,
        config_home=config_home,
        runtime_dir=runtime_dir,
    )
    print(json.dumps({"removed": removed}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
