import io
import struct
import sys
import unittest
from pathlib import Path

NATIVE_HOST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE_HOST_DIR))

from native_protocol import NativeMessageError, read_message, write_message


class NativeProtocolTests(unittest.TestCase):
    def test_round_trip_uses_native_messaging_length_prefix(self):
        stream = io.BytesIO()
        payload = {"id": "中文-1", "action": "ping"}

        write_message(stream, payload)
        raw = stream.getvalue()
        declared_size = struct.unpack("=I", raw[:4])[0]
        self.assertEqual(declared_size, len(raw[4:]))

        stream.seek(0)
        self.assertEqual(read_message(stream), payload)

    def test_clean_eof_returns_none(self):
        self.assertIsNone(read_message(io.BytesIO(b"")))

    def test_truncated_header_raises(self):
        with self.assertRaisesRegex(NativeMessageError, "header"):
            read_message(io.BytesIO(b"\x01\x00"))

    def test_truncated_payload_raises(self):
        stream = io.BytesIO(struct.pack("=I", 5) + b"{}")
        with self.assertRaisesRegex(NativeMessageError, "payload"):
            read_message(stream)

    def test_invalid_json_raises(self):
        stream = io.BytesIO(struct.pack("=I", 3) + b"xxx")
        with self.assertRaisesRegex(NativeMessageError, "JSON"):
            read_message(stream)


if __name__ == "__main__":
    unittest.main()
