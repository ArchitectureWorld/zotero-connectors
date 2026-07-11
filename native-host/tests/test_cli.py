import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

NATIVE_HOST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE_HOST_DIR))

from zotero_script_trigger_cli import build_request, create_parser, load_config


class CliTests(unittest.TestCase):
    def test_build_ping_request(self):
        request = build_request("ping", request_id="r1")
        self.assertEqual(request, {"id": "r1", "action": "ping"})

    def test_build_list_tabs_request(self):
        request = build_request("list-tabs", request_id="r-list")
        self.assertEqual(request, {"id": "r-list", "action": "list-tabs"})

    def test_build_save_active_request(self):
        request = build_request("save-active", request_id="r2")
        self.assertEqual(request, {"id": "r2", "action": "save-active"})

    def test_build_save_tab_requires_tab_id(self):
        with self.assertRaisesRegex(ValueError, "tab ID"):
            build_request("save-tab", request_id="r3")

    def test_build_save_tab_request(self):
        request = build_request("save-tab", tab_id=42, request_id="r4")
        self.assertEqual(request, {"id": "r4", "action": "save-tab", "tabId": 42})

    def test_build_save_url_exact_request(self):
        request = build_request(
            "save-url",
            url="https://bcras.hbut.edu.cn/s/net/cnki/detail?id=123",
            request_id="r5",
        )
        self.assertEqual(request, {
            "id": "r5",
            "action": "save-url",
            "url": "https://bcras.hbut.edu.cn/s/net/cnki/detail?id=123",
        })

    def test_build_save_url_contains_request(self):
        request = build_request("save-url", contains="detail?id=123", request_id="r6")
        self.assertEqual(request, {
            "id": "r6",
            "action": "save-url",
            "urlContains": "detail?id=123",
        })

    def test_build_save_url_requires_one_selector(self):
        with self.assertRaisesRegex(ValueError, "exactly one"):
            build_request("save-url", request_id="r7")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            build_request("save-url", url="https://example.org", contains="example", request_id="r8")

    def test_build_save_title_request(self):
        request = build_request("save-title", contains="目标论文", request_id="r9")
        self.assertEqual(request, {
            "id": "r9",
            "action": "save-title",
            "titleContains": "目标论文",
        })

    def test_parser_exposes_agent_commands(self):
        parser = create_parser()
        args = parser.parse_args(["save-url", "--url", "https://example.org/paper"])
        self.assertEqual(args.action, "save-url")
        self.assertEqual(args.url, "https://example.org/paper")
        args = parser.parse_args(["save-title", "--contains", "论文标题"])
        self.assertEqual(args.action, "save-title")
        self.assertEqual(args.contains, "论文标题")

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
