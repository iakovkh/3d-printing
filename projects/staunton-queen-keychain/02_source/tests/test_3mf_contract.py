import pathlib
import sys
import tempfile
import unittest
import zipfile

import trimesh


TOOLS_DIR = pathlib.Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from build_candidate import build_candidate
from inspect_3mf import inspect_package


def write_3mf_fixture(path, unit="millimeter", object_count=1, build_item_count=1):
    objects = []
    for object_id in range(1, object_count + 1):
        objects.append(
            f'<object id="{object_id}" type="model"><mesh>'
            '<vertices><vertex x="0" y="0" z="0"/>'
            '<vertex x="1" y="0" z="0"/><vertex x="0" y="1" z="0"/></vertices>'
            '<triangles><triangle v1="0" v2="1" v3="2"/></triangles>'
            '</mesh></object>'
        )
    items = "".join(
        f'<item objectid="{1 + (index % object_count)}"/>'
        for index in range(build_item_count)
    )
    model = (
        f'<model unit="{unit}" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        f'<resources>{"".join(objects)}</resources><build>{items}</build></model>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
        )
        archive.writestr("3D/3dmodel.model", model)


class ThreeMFContractTest(unittest.TestCase):
    def test_round_trip_preserves_mm_and_one_object(self):
        mesh = trimesh.creation.box(extents=[10.0, 20.0, 30.0])
        mesh.units = "mm"
        payload = trimesh.Scene({"fixture": mesh}).export(file_type="3mf")
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "fixture.3mf"
            path.write_bytes(payload)
            info = inspect_package(path)
            self.assertEqual(info["unit"], "millimeter")
            self.assertEqual(info["object_count"], 1)
            self.assertEqual(info["build_item_count"], 1)

    def test_refuses_existing_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp) / "existing.3mf"
            target.write_bytes(b"sentinel")
            with self.assertRaises(FileExistsError):
                build_candidate(pathlib.Path(tmp) / "unused.stl", target)
            self.assertEqual(target.read_bytes(), b"sentinel")

    def test_inspector_rejects_two_build_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "two-items.3mf"
            write_3mf_fixture(path, build_item_count=2)
            with self.assertRaisesRegex(ValueError, "one object and one build item"):
                inspect_package(path)

    def test_inspector_rejects_inches(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "inches.3mf"
            write_3mf_fixture(path, unit="inch")
            with self.assertRaisesRegex(ValueError, "expected 'millimeter'"):
                inspect_package(path)


if __name__ == "__main__":
    unittest.main()
