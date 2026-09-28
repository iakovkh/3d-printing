from __future__ import annotations

import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class ToolchainManifestTest(unittest.TestCase):
    def test_manifest_pins_cloud_modeling_tools(self):
        from toolchain.verify_toolchain import load_expected_versions

        manifest = load_expected_versions(ROOT / "toolchain" / "versions.json")
        self.assertEqual(manifest["python"], "3.12")
        self.assertEqual(manifest["blender"]["version"], "5.2.1")
        self.assertEqual(manifest["openscad"], "2021.01")
        self.assertEqual(manifest["packages"]["cadquery"], "2.8.0")

    def test_manifest_uses_verified_official_linux_blender_archive(self):
        from toolchain.verify_toolchain import load_expected_versions

        manifest = load_expected_versions(ROOT / "toolchain" / "versions.json")
        blender = manifest["blender"]
        self.assertEqual(
            blender["url"],
            "https://download.blender.org/release/Blender5.2/blender-5.2.1-linux-x64.tar.xz",
        )
        self.assertEqual(
            blender["sha256"],
            "a31f524fa99a527d3d52b7f5aaa68c34e1a19d5a1c9473f79c5cc610fd5b10e9",
        )

    def test_python_lock_preserves_qa_dependency_versions(self):
        required = {
            "numpy": "2.5.3",
            "scipy": "1.18.1",
            "trimesh": "5.1.0",
            "lxml": "6.1.3",
            "Pillow": "12.2.0",
            "networkx": "3.6.1",
            "cadquery": "2.8.0",
        }
        lines = (ROOT / "toolchain" / "requirements.lock").read_text(
            encoding="utf-8"
        ).splitlines()
        actual = dict(line.split("==", 1) for line in lines if line and not line.startswith("#"))
        self.assertEqual(actual, required)

    def test_probe_rejects_missing_or_mismatched_required_tool(self):
        from toolchain.verify_toolchain import probe_toolchain

        manifest = {
            "python": "3.12",
            "blender": {"version": "5.2.1", "url": "https://example.invalid/blender", "sha256": "a" * 64},
            "openscad": "2021.01",
            "packages": {"cadquery": "2.8.0"},
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "toolchain").mkdir()
            (root / "toolchain" / "versions.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )

            def fake_probe(name: str) -> str | None:
                return {
                    "python": "3.12.7",
                    "blender": None,
                    "openscad": "OpenSCAD version 2021.01",
                    "cadquery": "2.7.0",
                }[name]

            with self.assertRaisesRegex(RuntimeError, "blender.*missing.*cadquery.*2.7.0"):
                probe_toolchain(root, probe=fake_probe)


if __name__ == "__main__":
    unittest.main()
