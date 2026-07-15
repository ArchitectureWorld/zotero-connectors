import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
LINUX_DIR = ROOT / "packaging" / "linux"
INSTALLER_PATH = LINUX_DIR / "install-linux-dual-instance.py"
sys.path.insert(0, str(LINUX_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location("install_linux_dual_instance", INSTALLER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class LinuxInstallerCliTests(unittest.TestCase):
    def test_no_argument_install_uses_fixed_defaults(self):
        module = load_module()
        calls = []

        def fake_install(**kwargs):
            calls.append(kwargs)
            return {
                "settings_pages": {
                    "ZZH": "chrome-extension://anakemdifclhajhpbjlgfpeokaphddam/instanceSettings/instance-settings.html?instance=ZZH",
                    "NSY": "chrome-extension://anakemdifclhajhpbjlgfpeokaphddam/instanceSettings/instance-settings.html?instance=NSY",
                }
            }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            config_home = root / "config"
            runtime_dir = root / "runtime"
            home.mkdir()
            with (
                patch.object(module.Path, "home", return_value=home),
                patch.dict(
                    os.environ,
                    {
                        "XDG_CONFIG_HOME": str(config_home),
                        "XDG_RUNTIME_DIR": str(runtime_dir),
                    },
                    clear=False,
                ),
                patch.object(module, "install_dual_instance", side_effect=fake_install),
            ):
                exit_code = module.main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 1)
        request = calls[0]
        self.assertEqual(request["extension_id"], "anakemdifclhajhpbjlgfpeokaphddam")
        self.assertIsNone(request["zzh_profile_dir"])
        self.assertIsNone(request["nsy_profile_dir"])
        self.assertEqual(request["home"], home)
        self.assertEqual(request["config_home"], config_home)
        self.assertEqual(request["runtime_dir"], runtime_dir)


if __name__ == "__main__":
    unittest.main()
