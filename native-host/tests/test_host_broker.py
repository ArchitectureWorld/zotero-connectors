import io
import sys
import unittest
from pathlib import Path

NATIVE_HOST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE_HOST_DIR))

from host_config import HostConfig
from native_protocol import read_message
from zotero_script_trigger_host import NativeHostBroker


class NativeHostBrokerTests(unittest.TestCase):
    def setUp(self):
        self.stdout = io.BytesIO()
        self.broker = NativeHostBroker(
            HostConfig(pipe_name=r"\\.\pipe\test", authkey=b"0123456789abcdef"),
            stdin=io.BytesIO(),
            stdout=self.stdout,
        )

    def test_send_to_extension_uses_native_message_protocol(self):
        request = {"id": "r1", "action": "ping"}
        self.broker._send_to_extension(request)
        self.stdout.seek(0)
        self.assertEqual(read_message(self.stdout), request)

    def test_route_extension_response_matches_pending_request_id(self):
        response_queue = self.broker._register_request("r2")
        response = {"id": "r2", "success": True}
        self.broker._route_extension_response(response)
        self.assertEqual(response_queue.get_nowait(), response)
        self.broker._remove_request("r2")


if __name__ == "__main__":
    unittest.main()
