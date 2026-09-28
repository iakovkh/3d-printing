from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile
import unittest

from PIL import Image

from tests.fixtures.meshes import write_box_stl


ROOT = pathlib.Path(__file__).resolve().parents[1]
BLENDER = ROOT / "tools" / "blender-5.2.1-windows-x64" / "blender.exe"
SCRIPT = ROOT / "toolchain" / "blender" / "render_reopened.py"


@unittest.skipUnless(BLENDER.is_file(), "local Blender fixture is not installed")
class BlenderRenderTest(unittest.TestCase):
    def test_renders_all_required_raw_views_from_reopened_bodies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            body = write_box_stl(root / "reopened_body.stl", (10.0, 20.0, 30.0))
            manifest = root / "render-manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "model": "fixture",
                        "version": "v001",
                        "short_id": "deadbeef",
                        "bodies": [
                            {
                                "name": "body",
                                "path": str(body.resolve()),
                                "color": "#336699",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "raw"
            completed = subprocess.run(
                [
                    str(BLENDER),
                    "--background",
                    "--python",
                    str(SCRIPT),
                    "--",
                    "--manifest",
                    str(manifest),
                    "--output-dir",
                    str(output),
                ],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            for view in ("front", "back", "side", "top", "isometric"):
                path = output / f"fixture_v001_{view}_raw.png"
                self.assertTrue(path.is_file(), path)
                with Image.open(path) as image:
                    self.assertGreaterEqual(image.width, 512)
                    self.assertGreaterEqual(image.height, 512)


if __name__ == "__main__":
    unittest.main()
