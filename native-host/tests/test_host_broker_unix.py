import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

NATIVE_HOST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE_HOST_DIR))

import zotero_script_trigger_host as host


class UnixHostBrokerTests(unittest.TestCase):
    def test_create_listener_uses_configured_unix_socket_and_permissions(self):
        calls = []
        fake_listener = object()

        def fake_listener_factory(address, family, authkey):
            calls.append((address, family, authkey))
            return fake_listener

        with tempfile.TemporaryDirectory() as tmp:
            socket_path = str(Path(tmp) / "runtime" / "zzh.sock")
            config = SimpleNamespace(
                pipe_name=None,
                socket_path=socket_path,
                authkey=b"0123456789abcdef",
            )
            with patch.object(host, "Listener", fake_listener_factory):
                listener = host.create_listener(config)

            self.assertIs(listener, fake_listener)
            self.assertEqual(calls, [(socket_path, "AF_UNIX", b"0123456789abcdef")])
            self.assertEqual((Path(tmp) / "runtime").stat().st_mode & 0o777, 0o700)

    def test_stale_socket_cleanup_is_scoped_to_selected_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            zzh = Path(tmp) / "zzh.sock"
            nsy = Path(tmp) / "nsy.sock"
            zzh.write_text("stale", encoding="utf-8")
            nsy.write_text("other-instance", encoding="utf-8")

            host.remove_stale_socket(str(zzh))

            self.assertFalse(zzh.exists())
            self.assertTrue(nsy.exists())


if __name__ == "__main__":
    unittest.main()
