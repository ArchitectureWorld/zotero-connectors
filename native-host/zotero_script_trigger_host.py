"""Chrome/Edge native host that bridges a Windows named pipe to the extension."""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import uuid
from multiprocessing.connection import Listener
from typing import Any

from host_config import HostConfig, load_config
from native_protocol import NativeMessageError, read_message, write_message

PIPE_REQUEST_LIMIT = 1024 * 1024
EXTENSION_RESPONSE_TIMEOUT = 60.0


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
        finally:
            connection.close()

    def _serve_pipe(self, listener) -> None:
        try:
            while not self._stopped.is_set():
                connection = listener.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(connection,),
                    daemon=True,
                    name="zotero-script-trigger-client",
                ).start()
        finally:
            listener.close()

    def run(self) -> int:
        if os.name != "nt":
            raise RuntimeError("The V1 native host currently supports Windows only")

        listener = Listener(
            self.config.pipe_name,
            family="AF_PIPE",
            authkey=self.config.authkey,
        )
        threading.Thread(
            target=self._serve_pipe,
            args=(listener,),
            daemon=True,
            name="zotero-script-trigger-pipe",
        ).start()

        try:
            while True:
                response = read_message(self.stdin)
                if response is None:
                    return 0
                self._route_extension_response(response)
        finally:
            self._stopped.set()


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
