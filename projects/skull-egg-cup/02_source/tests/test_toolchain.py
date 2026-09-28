import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[4]
PROJECT = ROOT / "projects" / "skull-egg-cup"


class ToolchainTest(unittest.TestCase):
    def test_blender_and_vendor_are_available(self):
        blender = ROOT / "tools" / "blender-5.2.1-windows-x64" / "blender.exe"
        self.assertTrue(blender.is_file(), f"missing Blender executable: {blender}")

        toolchain_path = PROJECT / "02_source" / "toolchain.json"
        self.assertTrue(toolchain_path.is_file(), f"missing toolchain manifest: {toolchain_path}")
        data = json.loads(toolchain_path.read_text("utf-8"))
        self.assertEqual(data["blender"], "5.2.1 LTS")
        self.assertEqual(data["python"], "3.12")

        import PIL
        import lxml
        import numpy
        import scipy
        import trimesh

        self.assertEqual(numpy.__version__, "2.5.3")
        self.assertEqual(scipy.__version__, "1.18.1")
        self.assertEqual(trimesh.__version__, "5.1.0")
        self.assertEqual(lxml.__version__, "6.1.3")
        self.assertEqual(PIL.__version__, "12.2.0")


if __name__ == "__main__":
    unittest.main()
