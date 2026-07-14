"""User-level provisioning for two isolated Linux Zotero Connector instances."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
import stat
from pathlib import Path
from typing import Callable

EXTENSION_ID_PATTERN = re.compile(r"^[a-p]{32}$")
HOST_FILES = (
    "zotero_script_trigger_host.py",
    "zotero_script_trigger_cli.py",
    "host_config.py",
    "native_protocol.py",
)
ROUTES = {
    "ZZH": {
        "connector_url": "http://127.0.0.1:23119/",
        "native_host_name": "org.zotero.script_trigger.zzh",
        "socket_name": "zzh.sock",
        "config_name": "zzh.json",
        "launcher_name": "launch-zzh",
    },
    "NSY": {
        "connector_url": "http://127.0.0.1:23120/",
        "native_host_name": "org.zotero.script_trigger.nsy",
        "socket_name": "nsy.sock",
        "config_name": "nsy.json",
        "launcher_name": "launch-nsy",
    },
}


def _absolute(path: Path | str) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _secure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def _atomic_write(path: Path, content: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(content, encoding="utf-8")
    temporary.chmod(mode)
    os.replace(temporary, path)
    path.chmod(mode)


def _json_write(path: Path, value: dict, mode: int = 0o600) -> None:
    _atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n", mode)


def _instance_authkey(token_bytes: Callable[[int], bytes], instance_id: str) -> str:
    random_material = token_bytes(32)
    if not isinstance(random_material, bytes) or len(random_material) < 16:
        raise ValueError("token_bytes must return at least 16 bytes")
    key = hashlib.sha256(random_material + b":" + instance_id.encode("ascii")).digest()
    return base64.b64encode(key).decode("ascii")


def _validate_extension_id(extension_id: str) -> str:
    candidate = str(extension_id or "").strip().lower()
    if not EXTENSION_ID_PATTERN.fullmatch(candidate):
        raise ValueError("extension_id must be a 32-character Chrome extension ID")
    return candidate


def _validate_profiles(zzh_profile_dir: Path | str, nsy_profile_dir: Path | str) -> tuple[Path, Path]:
    zzh = _absolute(zzh_profile_dir)
    nsy = _absolute(nsy_profile_dir)
    if zzh == nsy:
        raise ValueError("ZZH and NSY Chrome profile directories must be distinct")
    return zzh, nsy


def _launcher_source(config_path: Path, launcher_module: Path) -> str:
    return """#!/bin/sh
set -eu
exec python3 {launcher} --config {config}
""".format(
        launcher=shlex.quote(str(launcher_module)),
        config=shlex.quote(str(config_path)),
    )


def _cli_wrapper_source(cli_path: Path) -> str:
    return """#!/bin/sh
set -eu
exec python3 {cli} "$@"
""".format(cli=shlex.quote(str(cli_path)))


def managed_paths(
    *,
    home: Path | str,
    config_home: Path | str,
    runtime_dir: Path | str,
) -> dict[str, object]:
    home_path = _absolute(home)
    config_path = _absolute(config_home)
    runtime_path = _absolute(runtime_dir) / "zotero-script-trigger"
    library_dir = home_path / ".local" / "lib" / "zotero-script-trigger"
    bin_dir = home_path / ".local" / "bin"
    instance_config_dir = config_path / "zotero-script-trigger"
    manifest_dir = config_path / "google-chrome" / "NativeMessagingHosts"
    return {
        "home": home_path,
        "config_home": config_path,
        "runtime_dir": runtime_path,
        "library_dir": library_dir,
        "bin_dir": bin_dir,
        "config_dir": instance_config_dir,
        "manifest_dir": manifest_dir,
        "cli_wrapper": bin_dir / "zotero-script-trigger",
    }


def install_dual_instance(
    *,
    source_root: Path | str,
    home: Path | str,
    config_home: Path | str,
    runtime_dir: Path | str,
    extension_id: str,
    zzh_profile_dir: Path | str,
    nsy_profile_dir: Path | str,
    token_bytes: Callable[[int], bytes] = secrets.token_bytes,
) -> dict[str, object]:
    source = _absolute(source_root)
    native_source = source / "native-host"
    extension = _validate_extension_id(extension_id)
    profiles = dict(zip(("ZZH", "NSY"), _validate_profiles(zzh_profile_dir, nsy_profile_dir)))
    paths = managed_paths(home=home, config_home=config_home, runtime_dir=runtime_dir)

    missing = [name for name in HOST_FILES if not (native_source / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Native Host package is incomplete: {', '.join(missing)}")

    library_dir = _secure_directory(paths["library_dir"])
    _secure_directory(paths["bin_dir"])
    config_dir = _secure_directory(paths["config_dir"])
    manifest_dir = _secure_directory(paths["manifest_dir"])
    socket_dir = _secure_directory(paths["runtime_dir"])

    copied = []
    for filename in HOST_FILES:
        destination = library_dir / filename
        shutil.copy2(native_source / filename, destination)
        destination.chmod(0o600)
        copied.append(destination)

    launcher_module_source = source / "packaging" / "linux" / "launch-instance.py"
    launcher_module = library_dir / "launch-instance.py"
    if launcher_module_source.is_file():
        shutil.copy2(launcher_module_source, launcher_module)
    else:
        launcher_module.write_text(
            "#!/usr/bin/env python3\nimport argparse, os, sys\n"
            "p=argparse.ArgumentParser(); p.add_argument('--config', required=True); a=p.parse_args(); "
            "os.environ['ZOTERO_SCRIPT_TRIGGER_CONFIG']=a.config; "
            "os.execv(sys.executable,[sys.executable,os.path.join(os.path.dirname(__file__),'zotero_script_trigger_host.py')])\n",
            encoding="utf-8",
        )
    launcher_module.chmod(0o700)

    cli_wrapper = paths["cli_wrapper"]
    _atomic_write(
        cli_wrapper,
        _cli_wrapper_source(library_dir / "zotero_script_trigger_cli.py"),
        0o700,
    )

    settings_pages: dict[str, str] = {}
    installed_files = [*copied, launcher_module, cli_wrapper]
    for instance_id, route in ROUTES.items():
        config_path = config_dir / route["config_name"]
        socket_path = socket_dir / route["socket_name"]
        launcher_path = library_dir / route["launcher_name"]
        manifest_path = manifest_dir / f"{route['native_host_name']}.json"

        _json_write(config_path, {
            "instance_id": instance_id,
            "socket_path": str(socket_path),
            "native_host_name": route["native_host_name"],
            "connector_url": route["connector_url"],
            "authkey": _instance_authkey(token_bytes, instance_id),
        })
        _atomic_write(
            launcher_path,
            _launcher_source(config_path, launcher_module),
            0o700,
        )
        _json_write(manifest_path, {
            "name": route["native_host_name"],
            "description": f"Zotero Connector Script Trigger ({instance_id})",
            "path": str(launcher_path),
            "type": "stdio",
            "allowed_origins": [f"chrome-extension://{extension}/"],
        }, mode=0o600)
        installed_files.extend((config_path, launcher_path, manifest_path))
        settings_pages[instance_id] = (
            f"chrome-extension://{extension}/instanceSettings/instance-settings.html"
            f"?instance={instance_id}"
        )

    return {
        "extension_id": extension,
        "profiles": {key: str(value) for key, value in profiles.items()},
        "settings_pages": settings_pages,
        "cli": str(cli_wrapper),
        "installed_files": [str(path) for path in installed_files],
    }


def _remove_file(path: Path, removed: list[str]) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISDIR(info.st_mode):
        return
    path.unlink()
    removed.append(str(path))


def _remove_if_empty(path: Path) -> None:
    try:
        path.rmdir()
    except (FileNotFoundError, OSError):
        pass


def uninstall_dual_instance(
    *,
    home: Path | str,
    config_home: Path | str,
    runtime_dir: Path | str,
) -> list[str]:
    paths = managed_paths(home=home, config_home=config_home, runtime_dir=runtime_dir)
    library_dir = paths["library_dir"]
    config_dir = paths["config_dir"]
    manifest_dir = paths["manifest_dir"]
    socket_dir = paths["runtime_dir"]
    removed: list[str] = []

    for route in ROUTES.values():
        _remove_file(config_dir / route["config_name"], removed)
        _remove_file(library_dir / route["launcher_name"], removed)
        _remove_file(manifest_dir / f"{route['native_host_name']}.json", removed)
        _remove_file(socket_dir / route["socket_name"], removed)

    for filename in (*HOST_FILES, "launch-instance.py"):
        _remove_file(library_dir / filename, removed)
    _remove_file(paths["cli_wrapper"], removed)

    for directory in (
        library_dir,
        paths["bin_dir"],
        config_dir,
        manifest_dir,
        manifest_dir.parent,
        socket_dir,
    ):
        _remove_if_empty(directory)
    return removed
