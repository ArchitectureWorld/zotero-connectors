"""Chrome native-messaging framing helpers."""

from __future__ import annotations

import json
import struct
from typing import Any, BinaryIO

MAX_HOST_MESSAGE_BYTES = 1024 * 1024
MAX_EXTENSION_MESSAGE_BYTES = 64 * 1024 * 1024


class NativeMessageError(RuntimeError):
    """Raised when a native-messaging frame is malformed."""


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_message(stream: BinaryIO, max_bytes: int = MAX_EXTENSION_MESSAGE_BYTES) -> dict[str, Any] | None:
    """Read one length-prefixed JSON message; return None for clean EOF."""

    first = stream.read(1)
    if first == b"":
        return None
    header = first + _read_exact(stream, 3)
    if len(header) != 4:
        raise NativeMessageError("Truncated native-message header")

    size = struct.unpack("=I", header)[0]
    if size > max_bytes:
        raise NativeMessageError(f"Native-message payload exceeds {max_bytes} bytes")

    payload = _read_exact(stream, size)
    if len(payload) != size:
        raise NativeMessageError("Truncated native-message payload")

    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NativeMessageError(f"Invalid native-message JSON: {exc}") from exc
    if not isinstance(message, dict):
        raise NativeMessageError("Native-message JSON must be an object")
    return message


def write_message(stream: BinaryIO, message: dict[str, Any], max_bytes: int = MAX_HOST_MESSAGE_BYTES) -> None:
    """Write one length-prefixed JSON message and flush the stream."""

    payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(payload) > max_bytes:
        raise NativeMessageError(f"Native-message payload exceeds {max_bytes} bytes")
    stream.write(struct.pack("=I", len(payload)))
    stream.write(payload)
    stream.flush()
