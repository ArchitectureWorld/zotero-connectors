import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

NATIVE_HOST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE_HOST_DIR))

from zotero_script_trigger_cli import build_request, load_config


class CliTests(unittest.TestCase):
    def test_build_ping_request(self):
        request = build_request("ping", tab_id=None, request_id="r1")
        self.assertEqual(request, {"id": "r1", "action": "ping"})

    def test_build_save_active_request(self):
        request = build_request("save-active", tab_id=None, request_id="r2")
        self.assertEqual(request, {"id": "r2", "action": "save-active"})

    def test_build_save_tab_requires_tab_id(self):
        with self.assertRaisesRegex(ValueError, "tab ID"):
            build_request("save-tab", tab_id=None, request_id="r3")

    def test_build_save_tab_request(self):
        request = build_request("save-tab", tab_id=42, request_id="r4")
        self.assertEqual(request, {"id": "r4", "action": "save-tab", "tabId": 42})

    def test_load_config_decodes_authkey(self):
        authkey = b"0123456789abcdef"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({
                "pipe_name": r"\\.\pipe\zotero-script-trigger-test",
                "authkey": base64.b64encode(authkey).decode("ascii"),
            }), encoding="utf-8")

            config = load_config(path)

        self.assertEqual(config.pipe_name, r"\\.\pipe\zotero-script-trigger-test")
        self.assertEqual(config.authkey, authkey)


if __name__ == "__main__":
    unittest.main()
