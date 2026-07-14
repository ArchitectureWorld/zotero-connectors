"""Chrome/Edge native host that bridges a local client channel to the extension."""

from __future__ import annotations

import errno
import json
import os
import queue
import socket
import stat
import sys
import threading
import uuid
from multiprocessing.connection import Listener
from pathlib import Path
from typing import Any

from host_config import HostConfig, load_config
from native_protocol import NativeMessageError, read_message, write_message

PIPE_REQUEST_LIMIT = 1024 * 1024
EXTENSION_RESPONSE_TIMEOUT = 60.0


def _owned_path_info(path: Path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(info.st_mode):
        raise RuntimeError(f"Refusing to use symbolic socket path: {path}")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise RuntimeError(f"Refusing to remove socket not owned by current user: {path}")
    if stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"Socket path is a directory: {path}")
    return info


def _unix_socket_is_live(path: Path) -> bool:
    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    probe.settimeout(0.2)
    try:
        result = probe.connect_ex(str(path))
    finally:
        probe.close()
    if result == 0:
        return True
    if result in (errno.ENOENT, errno.ECONNREFUSED):
        return False
    raise RuntimeError(f"Cannot determine whether Unix socket is active: {path} (errno {result})")


def remove_stale_socket(socket_path: str) -> None:
    """Remove one stale user-owned path, but never unlink a live or symbolic socket."""
    path = Path(socket_path)
    info = _owned_path_info(path)
    if info is None:
        return
    if stat.S_ISSOCK(info.st_mode) and _unix_socket_is_live(path):
        raise RuntimeError(f"Script Trigger instance is already running on live socket: {path}")
    path.unlink()


def _remove_owned_socket_after_close(socket_path: str) -> None:
    path = Path(socket_path)
    info = _owned_path_info(path)
    if info is None:
        return
    if not stat.S_ISSOCK(info.st_mode):
        raise RuntimeError(f"Refusing to remove non-socket runtime path: {path}")
    path.unlink()


def _prepare_socket_directory(socket_path: str) -> Path:
    directory = Path(socket_path).parent
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        directory.chmod(0o700)
    except OSError as exc:
        raise RuntimeError(f"Unable to secure socket directory {directory}: {exc}") from exc
    return directory


def _secure_created_socket(socket_path: str, listener) -> None:
    path = Path(socket_path)
    if not path.exists():
        # Test doubles do not create a filesystem socket. A real AF_UNIX
        # Listener always creates it before returning.
        return
    try:
        path.chmod(0o600)
    except OSError:
        listener.close()
        _remove_owned_socket_after_close(socket_path)
        raise


def create_listener(config: HostConfig):
    if config.pipe_name:
        return Listener(config.pipe_name, family="AF_PIPE", authkey=config.authkey)
    if not config.socket_path:
        raise RuntimeError("Script Trigger config has no local transport endpoint")

    _prepare_socket_directory(config.socket_path)
    remove_stale_socket(config.socket_path)
    listener = Listener(config.socket_path, family="AF_UNIX", authkey=config.authkey)
    _secure_created_socket(config.socket_path, listener)
    return listener


class NativeHostBroker:
    def __init__(self, config: HostConfig, stdin=None, stdout=None) -> None:
        self.config = config
        self.stdin = stdin or sys.stdin.buffer
        self.stdout = stdout or sys.stdout.buffer
        self._pending: dict[str, queue.Queue[dict[str, Any]]] = {}
        self._pending_lock = threading.Lock()
        self._stdout_lock = threading.Lock()
        self._stopped = threading.Event()

    def _send_to_extension(self, request: dict[str, Any]) -> None:
        with self._stdout_lock:
            write_message(self.stdout, request)

    def _register_request(self, request_id: str) -> queue.Queue[dict[str, Any]]:
        response_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
        with self._pending_lock:
            if request_id in self._pending:
                raise RuntimeError(f"Duplicate request id: {request_id}")
            self._pending[request_id] = response_queue
        return response_queue

    def _remove_request(self, request_id: str) -> None:
        with self._pending_lock:
            self._pending.pop(request_id, None)

    def _route_extension_response(self, response: dict[str, Any]) -> None:
        request_id = response.get("id")
        if not isinstance(request_id, str):
            return
        with self._pending_lock:
            response_queue = self._pending.get(request_id)
        if response_queue:
            try:
                response_queue.put_nowait(response)
            except queue.Full:
                pass

    @staticmethod
    def _error_response(request_id: str | None, code: str, message: str) -> dict[str, Any]:
        return {
            "id": request_id,
            "success": False,
            "error": {"code": code, "message": message},
        }

    def _handle_client(self, connection) -> None:
        request_id: str | None = None
        try:
            raw = connection.recv_bytes(PIPE_REQUEST_LIMIT)
            request = json.loads(raw.decode("utf-8"))
            if not isinstance(request, dict):
                raise ValueError("Request JSON must be an object")
            request_id = request.get("id")
            if not isinstance(request_id, str) or not request_id:
                request_id = str(uuid.uuid4())
                request["id"] = request_id

            response_queue = self._register_request(request_id)
            try:
                self._send_to_extension(request)
                try:
                    response = response_queue.get(timeout=EXTENSION_RESPONSE_TIMEOUT)
                except queue.Empty:
                    response = self._error_response(
                        request_id,
                        "EXTENSION_TIMEOUT",
                        "The browser extension did not respond within 60 seconds",
                    )
            finally:
                self._remove_request(request_id)
        except Exception as exc:
            response = self._error_response(request_id, type(exc).__name__, str(exc))

        try:
            connection.send_bytes(
                json.dumps(response, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            )
        except (BrokenPipeError, EOFError, OSError):
            pass
        finally:
            connection.close()

    def _serve_clients(self, listener) -> None:
        try:
            while not self._stopped.is_set():
                try:
                    connection = listener.accept()
                except (OSError, EOFError):
                    if self._stopped.is_set():
                        return
                    raise
                threading.Thread(
                    target=self._handle_client,
                    args=(connection,),
                    daemon=True,
                    name="zotero-script-trigger-client",
                ).start()
        finally:
            listener.close()

    def run(self) -> int:
        listener = create_listener(self.config)
        server_thread = threading.Thread(
            target=self._serve_clients,
            args=(listener,),
            daemon=True,
            name="zotero-script-trigger-listener",
        )
        server_thread.start()

        try:
            while True:
                response = read_message(self.stdin)
                if response is None:
                    return 0
                self._route_extension_response(response)
        finally:
            self._stopped.set()
            listener.close()
            server_thread.join(timeout=0.5)
            if self.config.socket_path:
                try:
                    _remove_owned_socket_after_close(self.config.socket_path)
                except FileNotFoundError:
                    pass


def _enable_windows_binary_stdio() -> None:
    if os.name != "nt":
        return
    import msvcrt

    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)


def main() -> int:
    try:
        _enable_windows_binary_stdio()
        config = load_config()
        return NativeHostBroker(config).run()
    except (RuntimeError, NativeMessageError, OSError) as exc:
        print(f"Zotero script-trigger native host failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
