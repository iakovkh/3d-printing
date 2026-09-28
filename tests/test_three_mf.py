from __future__ import annotations

import hashlib
import json
import pathlib
import tempfile
import unittest
import zipfile

import numpy as np
import trimesh

from tests.fixtures.meshes import write_box_stl
from toolchain.cloud3d.roundtrip import reopen_candidate
from toolchain.cloud3d.three_mf import BodyInput, build_candidate, inspect_package


IDENTITY = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


def translated(x: float, y: float = 0.0, z: float = 0.0):
    matrix = np.eye(4)
    matrix[:3, 3] = (x, y, z)
    return tuple(tuple(float(value) for value in row) for row in matrix)


def write_minimal_3mf(path: pathlib.Path, unit: str) -> None:
    model = (
        f'<model unit="{unit}" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        '<resources><object id="1" name="fixture" type="model"><mesh>'
        '<vertices><vertex x="0" y="0" z="0"/><vertex x="1" y="0" z="0"/>'
        '<vertex x="0" y="1" z="0"/></vertices>'
        '<triangles><triangle v1="0" v2="1" v3="2"/></triangles>'
        '</mesh></object></resources><build><item objectid="1" partnumber="fixture"/>'
        '</build></model>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("_rels/.rels", "<Relationships/>")
        archive.writestr("3D/3dmodel.model", model)


class ThreeMFTest(unittest.TestCase):
    def test_build_candidate_refuses_existing_destination_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            candidate = root / "fixture_v001_candidate.3mf"
            candidate.write_bytes(b"sentinel")
            with self.assertRaises(FileExistsError):
                build_candidate(
                    [BodyInput(root / "missing.stl", "body", "#112233", IDENTITY)],
                    candidate,
                )
            self.assertEqual(candidate.read_bytes(), b"sentinel")

    def test_single_body_roundtrip_preserves_millimeters_bounds_and_volume(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            stl = write_box_stl(root / "body.stl", (10.0, 20.0, 30.0))
            candidate = root / "fixture_v001_candidate.3mf"
            build_candidate([BodyInput(stl, "body", "#336699", IDENTITY)], candidate)
            report = reopen_candidate(candidate, root / "reopened")
            self.assertEqual(report.unit, "millimeter")
            self.assertEqual(report.body_names, ("body",))
            np.testing.assert_allclose(report.extents_mm, (10.0, 20.0, 30.0), atol=0.001)
            self.assertAlmostEqual(report.body_volumes_mm3["body"], 6000.0, places=2)

    def test_multibody_roundtrip_preserves_names_transforms_and_colors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            a = write_box_stl(root / "base.stl", (10.0, 10.0, 2.0))
            b = write_box_stl(root / "inlay.stl", (2.0, 2.0, 4.0))
            candidate = root / "fixture_v001_candidate.3mf"
            build_candidate(
                [
                    BodyInput(a, "base", "#112233", IDENTITY),
                    BodyInput(b, "inlay", "#AABBCC", translated(20.0)),
                ],
                candidate,
            )
            package = inspect_package(candidate)
            report = reopen_candidate(candidate, root / "reopened")
            self.assertEqual(package.body_names, ("base", "inlay"))
            self.assertEqual(package.colors, {"base": "#112233", "inlay": "#AABBCC"})
            np.testing.assert_allclose(package.transforms["inlay"], translated(20.0), atol=1e-9)
            self.assertEqual(report.body_names, ("base", "inlay"))
            self.assertEqual(report.colors, package.colors)

    def test_candidate_must_match_source_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            stl = write_box_stl(root / "body.stl", (1.0, 2.0, 3.0))
            manifest = root / "source-manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "bodies": [
                            {
                                "name": "different-name",
                                "color": "#112233",
                                "transform": [value for row in IDENTITY for value in row],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "source manifest"):
                build_candidate(
                    [BodyInput(stl, "body", "#112233", IDENTITY)],
                    root / "fixture_v001_candidate.3mf",
                    source_manifest=manifest,
                )

    def test_inspector_rejects_missing_members_and_non_mm_units(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            missing = root / "missing.3mf"
            with zipfile.ZipFile(missing, "w") as archive:
                archive.writestr("3D/3dmodel.model", "<model/>")
            with self.assertRaisesRegex(ValueError, "missing"):
                inspect_package(missing)
            inches = root / "inches.3mf"
            write_minimal_3mf(inches, "inch")
            with self.assertRaisesRegex(ValueError, "millimeter"):
                inspect_package(inches)

    def test_roundtrip_exports_reopened_bodies_not_changed_original_stl(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            stl = write_box_stl(root / "body.stl", (10.0, 20.0, 30.0))
            candidate = root / "fixture_v001_candidate.3mf"
            build_candidate([BodyInput(stl, "body", "#112233", IDENTITY)], candidate)
            write_box_stl(stl, (1.0, 1.0, 1.0))
            report = reopen_candidate(candidate, root / "reopened")
            reopened = trimesh.load_mesh(report.reopened_bodies["body"], process=False)
            np.testing.assert_allclose(reopened.extents, (10.0, 20.0, 30.0), atol=0.001)

    def test_short_id_is_first_eight_uppercase_sha256_characters(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            stl = write_box_stl(root / "body.stl", (1.0, 2.0, 3.0))
            candidate = root / "fixture_v001_candidate.3mf"
            identity = build_candidate(
                [BodyInput(stl, "body", "#112233", IDENTITY)], candidate
            )
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            self.assertEqual(identity.sha256, digest)
            self.assertEqual(identity.short_id, digest[:8].upper())


if __name__ == "__main__":
    unittest.main()
