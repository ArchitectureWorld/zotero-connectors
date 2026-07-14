import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

NATIVE_HOST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE_HOST_DIR))

from host_config import load_config


class LinuxHostConfigTests(unittest.TestCase):
    def test_loads_linux_instance_config(self):
        authkey = b"0123456789abcdef"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nsy.json"
            path.write_text(json.dumps({
                "instance_id": "NSY",
                "socket_path": str(Path(tmp) / "nsy.sock"),
                "native_host_name": "org.zotero.script_trigger.nsy",
                "connector_url": "http://127.0.0.1:23120/",
                "authkey": base64.b64encode(authkey).decode("ascii"),
            }), encoding="utf-8")

            config = load_config(path)

        self.assertEqual(config.instance_id, "NSY")
        self.assertEqual(config.socket_path, str(Path(tmp) / "nsy.sock"))
        self.assertIsNone(config.pipe_name)
        self.assertEqual(config.native_host_name, "org.zotero.script_trigger.nsy")
        self.assertEqual(config.connector_url, "http://127.0.0.1:23120/")
        self.assertEqual(config.authkey, authkey)

    def test_rejects_relative_socket_path(self):
        authkey = base64.b64encode(b"0123456789abcdef").decode("ascii")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps({
                "instance_id": "ZZH",
                "socket_path": "relative/zzh.sock",
                "native_host_name": "org.zotero.script_trigger.zzh",
                "connector_url": "http://127.0.0.1:23119/",
                "authkey": authkey,
            }), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "absolute"):
                load_config(path)

    def test_rejects_non_loopback_connector_url(self):
        authkey = base64.b64encode(b"0123456789abcdef").decode("ascii")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps({
                "instance_id": "NSY",
                "socket_path": str(Path(tmp) / "nsy.sock"),
                "native_host_name": "org.zotero.script_trigger.nsy",
                "connector_url": "http://192.168.1.8:23120/",
                "authkey": authkey,
            }), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "127.0.0.1"):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
