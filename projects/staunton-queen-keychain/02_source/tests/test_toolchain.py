import importlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[4]
TOOLCHAIN_PATH = ROOT / "projects/staunton-queen-keychain/02_source/toolchain.json"


class ToolchainTest(unittest.TestCase):
    def test_recorded_executables_and_dependencies_are_real(self):
        config = json.loads(TOOLCHAIN_PATH.read_text(encoding="utf-8"))
        blender = ROOT / config["blender_path"]
        vendor = ROOT / config["vendor_path"]
        self.assertTrue(blender.is_file(), blender)
        self.assertTrue(vendor.is_dir(), vendor)

        output = subprocess.run(
            [str(blender), "--version"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertIn(config["blender"], output)

        expected = config["packages"]
        module_names = {
            "pillow": "PIL",
            "numpy": "numpy",
            "scipy": "scipy",
            "trimesh": "trimesh",
            "lxml": "lxml",
            "networkx": "networkx",
        }
        for package_name, module_name in module_names.items():
            module = importlib.import_module(module_name)
            self.assertEqual(module.__version__, expected[package_name])


if __name__ == "__main__":
    unittest.main()

