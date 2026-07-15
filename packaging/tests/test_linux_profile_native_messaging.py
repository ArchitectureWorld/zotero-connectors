import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "packaging" / "linux" / "dual_instance.py"
EXTENSION_ID = "anakemdifclhajhpbjlgfpeokaphddam"


def load_module():
    spec = importlib.util.spec_from_file_location("dual_instance", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class LinuxProfileNativeMessagingTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.config_home = self.root / "config"
        self.runtime_dir = self.root / "runtime"
        self.source_root = self.root / "source"

        native_host = self.source_root / "native-host"
        native_host.mkdir(parents=True)
        for filename in (
            "zotero_script_trigger_host.py",
            "zotero_script_trigger_cli.py",
            "host_config.py",
            "native_protocol.py",
        ):
            (native_host / filename).write_text(f"# {filename}\n", encoding="utf-8")

        browser_extension = self.source_root / "browser-extension"
        browser_extension.mkdir()
        (browser_extension / "manifest.json").write_text(
            json.dumps({"manifest_version": 3, "name": "Test Connector", "version": "1.0"}),
            encoding="utf-8",
        )

    def install(self, **overrides):
        arguments = {
            "source_root": self.source_root,
            "home": self.home,
            "config_home": self.config_home,
            "runtime_dir": self.runtime_dir,
            "extension_id": EXTENSION_ID,
            "token_bytes": lambda count: b"D" * count,
        }
        arguments.update(overrides)
        return self.module.install_dual_instance(**arguments)

    def test_zero_argument_profile_selection_registers_each_host_in_its_user_data_dir(self):
        result = self.install(zzh_profile_dir=None, nsy_profile_dir=None)

        zzh_root = self.config_home / "google-chrome-zzh"
        nsy_root = self.config_home / "google-chrome-nsy"
        zzh_manifest = zzh_root / "NativeMessagingHosts" / "org.zotero.script_trigger.zzh.json"
        nsy_manifest = nsy_root / "NativeMessagingHosts" / "org.zotero.script_trigger.nsy.json"

        self.assertEqual(result["profiles"], {"ZZH": str(zzh_root), "NSY": str(nsy_root)})
        self.assertTrue(zzh_manifest.is_file())
        self.assertTrue(nsy_manifest.is_file())
        self.assertFalse(
            (zzh_root / "NativeMessagingHosts" / "org.zotero.script_trigger.nsy.json").exists()
        )
        self.assertFalse(
            (nsy_root / "NativeMessagingHosts" / "org.zotero.script_trigger.zzh.json").exists()
        )

        zzh = json.loads(zzh_manifest.read_text(encoding="utf-8"))
        nsy = json.loads(nsy_manifest.read_text(encoding="utf-8"))
        self.assertEqual(zzh["name"], "org.zotero.script_trigger.zzh")
        self.assertEqual(nsy["name"], "org.zotero.script_trigger.nsy")
        self.assertEqual(zzh["allowed_origins"], [f"chrome-extension://{EXTENSION_ID}/"])
        self.assertEqual(nsy["allowed_origins"], [f"chrome-extension://{EXTENSION_ID}/"])

    def test_explicit_user_data_directories_receive_profile_local_manifests(self):
        zzh_root = self.root / "custom zzh"
        nsy_root = self.root / "custom nsy"

        result = self.install(
            zzh_profile_dir=zzh_root,
            nsy_profile_dir=nsy_root,
        )

        self.assertEqual(result["profiles"], {"ZZH": str(zzh_root), "NSY": str(nsy_root)})
        self.assertTrue(
            (zzh_root / "NativeMessagingHosts" / "org.zotero.script_trigger.zzh.json").is_file()
        )
        self.assertTrue(
            (nsy_root / "NativeMessagingHosts" / "org.zotero.script_trigger.nsy.json").is_file()
        )

    def test_uninstall_removes_profile_local_manifests(self):
        self.install(zzh_profile_dir=None, nsy_profile_dir=None)

        zzh_manifest = (
            self.config_home
            / "google-chrome-zzh"
            / "NativeMessagingHosts"
            / "org.zotero.script_trigger.zzh.json"
        )
        nsy_manifest = (
            self.config_home
            / "google-chrome-nsy"
            / "NativeMessagingHosts"
            / "org.zotero.script_trigger.nsy.json"
        )
        self.assertTrue(zzh_manifest.exists())
        self.assertTrue(nsy_manifest.exists())

        self.module.uninstall_dual_instance(
            home=self.home,
            config_home=self.config_home,
            runtime_dir=self.runtime_dir,
        )

        self.assertFalse(zzh_manifest.exists())
        self.assertFalse(nsy_manifest.exists())


if __name__ == "__main__":
    unittest.main()
