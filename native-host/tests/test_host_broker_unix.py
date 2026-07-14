import socket
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

    def test_live_socket_is_not_removed_by_a_second_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            socket_path = Path(tmp) / "nsy.sock"
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(socket_path))
            server.listen(1)
            try:
                with self.assertRaisesRegex(RuntimeError, "already running|live socket"):
                    host.remove_stale_socket(str(socket_path))
                self.assertTrue(socket_path.exists())
            finally:
                server.close()
                if socket_path.exists():
                    socket_path.unlink()

    def test_symbolic_socket_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            link = Path(tmp) / "zzh.sock"
            target.write_text("data", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaisesRegex(RuntimeError, "symbolic"):
                host.remove_stale_socket(str(link))
            self.assertTrue(target.exists())
            self.assertTrue(link.is_symlink())


if __name__ == "__main__":
    unittest.main()
