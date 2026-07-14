import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

NATIVE_HOST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE_HOST_DIR))

import zotero_script_trigger_cli as cli


class FakeConnection:
    def __init__(self):
        self.sent = []
        self.closed = False

    def send_bytes(self, payload):
        self.sent.append(payload)

    def poll(self, timeout):
        return True

    def recv_bytes(self):
        return b'{"success":true,"action":"ping"}'

    def close(self):
        self.closed = True


class UnixCliTests(unittest.TestCase):
    def test_uses_only_configured_unix_socket(self):
        connection = FakeConnection()
        calls = []

        def fake_client(address, family, authkey):
            calls.append((address, family, authkey))
            return connection

        config = SimpleNamespace(
            pipe_name=None,
            socket_path="/tmp/zotero-script-trigger/nsy.sock",
            authkey=b"0123456789abcdef",
        )
        with patch.object(cli.os, "name", "posix"), patch.object(cli, "Client", fake_client):
            response = cli.send_request(config, {"id": "1", "action": "ping"}, 1.0)

        self.assertEqual(response["success"], True)
        self.assertEqual(calls, [(
            "/tmp/zotero-script-trigger/nsy.sock",
            "AF_UNIX",
            b"0123456789abcdef",
        )])
        self.assertTrue(connection.closed)

    def test_parser_accepts_explicit_instance(self):
        parser = cli.create_parser()
        args = parser.parse_args(["--instance", "NSY", "ping"])
        self.assertEqual(args.instance, "NSY")


if __name__ == "__main__":
    unittest.main()
