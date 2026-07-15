import importlib.util
import json
import os
import shlex
import stat
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "packaging" / "linux" / "dual_instance.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dual_instance", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class LinuxDualInstanceProvisioningTests(unittest.TestCase):
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

    def install(self):
        return self.module.install_dual_instance(
            source_root=self.source_root,
            home=self.home,
            config_home=self.config_home,
            runtime_dir=self.runtime_dir,
            extension_id="anakemdifclhajhpbjlgfpeokaphddam",
            zzh_profile_dir=self.root / "chrome-zzh",
            nsy_profile_dir=self.root / "chrome-nsy",
            token_bytes=lambda count: b"A" * count,
        )

    def test_installs_two_isolated_configs_manifests_and_launchers(self):
        result = self.install()

        zzh_config_path = self.config_home / "zotero-script-trigger" / "zzh.json"
        nsy_config_path = self.config_home / "zotero-script-trigger" / "nsy.json"
        zzh = json.loads(zzh_config_path.read_text(encoding="utf-8"))
        nsy = json.loads(nsy_config_path.read_text(encoding="utf-8"))

        self.assertEqual(zzh["instance_id"], "ZZH")
        self.assertEqual(zzh["connector_url"], "http://127.0.0.1:23119/")
        self.assertTrue(zzh["socket_path"].endswith("/zzh.sock"))
        self.assertEqual(nsy["instance_id"], "NSY")
        self.assertEqual(nsy["connector_url"], "http://127.0.0.1:23120/")
        self.assertTrue(nsy["socket_path"].endswith("/nsy.sock"))
        self.assertNotEqual(zzh["native_host_name"], nsy["native_host_name"])
        self.assertNotEqual(zzh["authkey"], nsy["authkey"])

        manifest_dir = self.config_home / "google-chrome" / "NativeMessagingHosts"
        for instance in ("zzh", "nsy"):
            manifest = json.loads(
                (manifest_dir / f"org.zotero.script_trigger.{instance}.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                manifest["allowed_origins"],
                ["chrome-extension://anakemdifclhajhpbjlgfpeokaphddam/"],
            )
            self.assertTrue(Path(manifest["path"]).is_absolute())
            self.assertTrue(Path(manifest["path"]).exists())

        self.assertEqual(stat.S_IMODE(zzh_config_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(nsy_config_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.runtime_dir / "zotero-script-trigger").stat().st_mode), 0o700)
        self.assertIn("ZZH", result["settings_pages"])
        self.assertIn("NSY", result["settings_pages"])

    def test_profile_directories_are_optional_for_installation(self):
        result = self.module.install_dual_instance(
            source_root=self.source_root,
            home=self.home,
            config_home=self.config_home,
            runtime_dir=self.runtime_dir,
            extension_id="anakemdifclhajhpbjlgfpeokaphddam",
            zzh_profile_dir=None,
            nsy_profile_dir=None,
            token_bytes=lambda count: b"C" * count,
        )

        self.assertEqual(result["profiles"], {})
        self.assertTrue((self.config_home / "zotero-script-trigger" / "zzh.json").exists())
        self.assertTrue((self.config_home / "zotero-script-trigger" / "nsy.json").exists())

    def test_generated_shell_commands_quote_paths_containing_spaces(self):
        spaced_home = self.root / "home with space"
        spaced_config = self.root / "config with space"
        spaced_runtime = self.root / "runtime with space"
        self.module.install_dual_instance(
            source_root=self.source_root,
            home=spaced_home,
            config_home=spaced_config,
            runtime_dir=spaced_runtime,
            extension_id="anakemdifclhajhpbjlgfpeokaphddam",
            zzh_profile_dir=self.root / "chrome zzh",
            nsy_profile_dir=self.root / "chrome nsy",
            token_bytes=lambda count: b"B" * count,
        )

        library_dir = spaced_home / ".local" / "lib" / "zotero-script-trigger"
        launcher_line = (library_dir / "launch-zzh").read_text(encoding="utf-8").splitlines()[-1]
        launcher_tokens = shlex.split(launcher_line)
        self.assertEqual(launcher_tokens[0:2], ["exec", "python3"])
        self.assertEqual(launcher_tokens[2], str(library_dir / "launch-instance.py"))
        self.assertEqual(launcher_tokens[3], "--config")
        self.assertEqual(
            launcher_tokens[4],
            str(spaced_config / "zotero-script-trigger" / "zzh.json"),
        )

        cli_line = (spaced_home / ".local" / "bin" / "zotero-script-trigger").read_text(
            encoding="utf-8"
        ).splitlines()[-1]
        cli_tokens = shlex.split(cli_line)
        self.assertEqual(cli_tokens[0:2], ["exec", "python3"])
        self.assertEqual(cli_tokens[2], str(library_dir / "zotero_script_trigger_cli.py"))
        self.assertEqual(cli_tokens[3], "$@")

    def test_does_not_edit_chrome_profile_internal_files(self):
        zzh_profile = self.root / "chrome-zzh"
        nsy_profile = self.root / "chrome-nsy"
        zzh_profile.mkdir()
        nsy_profile.mkdir()
        (zzh_profile / "Preferences").write_text("keep-zzh", encoding="utf-8")
        (nsy_profile / "Preferences").write_text("keep-nsy", encoding="utf-8")

        self.install()

        self.assertEqual((zzh_profile / "Preferences").read_text(encoding="utf-8"), "keep-zzh")
        self.assertEqual((nsy_profile / "Preferences").read_text(encoding="utf-8"), "keep-nsy")
        self.assertFalse((zzh_profile / "Local Extension Settings").exists())
        self.assertFalse((nsy_profile / "Local Extension Settings").exists())

    def test_rejects_shared_profile_directory(self):
        same = self.root / "same-profile"
        with self.assertRaisesRegex(ValueError, "distinct"):
            self.module.install_dual_instance(
                source_root=self.source_root,
                home=self.home,
                config_home=self.config_home,
                runtime_dir=self.runtime_dir,
                extension_id="anakemdifclhajhpbjlgfpeokaphddam",
                zzh_profile_dir=same,
                nsy_profile_dir=same,
            )

    def test_uninstall_removes_only_managed_files(self):
        self.install()
        keep = self.config_home / "zotero-script-trigger" / "keep.txt"
        keep.write_text("user", encoding="utf-8")

        removed = self.module.uninstall_dual_instance(
            home=self.home,
            config_home=self.config_home,
            runtime_dir=self.runtime_dir,
        )

        self.assertTrue(keep.exists())
        self.assertFalse((self.config_home / "zotero-script-trigger" / "zzh.json").exists())
        self.assertFalse((self.config_home / "zotero-script-trigger" / "nsy.json").exists())
        self.assertGreater(len(removed), 0)


if __name__ == "__main__":
    unittest.main()
