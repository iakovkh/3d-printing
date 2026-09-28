from __future__ import annotations

import pathlib
import tempfile
import unittest
import warnings

import trimesh

from tests.fixtures.meshes import write_box_stl
from toolchain.cloud3d.qa import Severity, run_generic_qa
from toolchain.cloud3d.roundtrip import reopen_candidate
from toolchain.cloud3d.three_mf import BodyInput, build_candidate


IDENTITY = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


def make_box_candidate(root: pathlib.Path):
    stl = write_box_stl(root / "body.stl", (10.0, 20.0, 30.0))
    candidate = root / "fixture_v001_candidate.3mf"
    identity = build_candidate([BodyInput(stl, "body", "#336699", IDENTITY)], candidate)
    return identity, reopen_candidate(candidate, root / "reopened")


class QaContractTest(unittest.TestCase):
    def test_qa_marks_non_watertight_missing_body_and_dimension_mismatch_as_blocker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            mesh = trimesh.Trimesh(
                vertices=[[0, 0, 0], [10, 0, 0], [0, 10, 0]],
                faces=[[0, 1, 2]],
                process=False,
            )
            source = root / "open.stl"
            source.write_bytes(mesh.export(file_type="stl"))
            candidate = root / "fixture_v001_candidate.3mf"
            build_candidate([BodyInput(source, "open", "#112233", IDENTITY)], candidate)
            with warnings.catch_warnings():
                warnings.simplefilter("error", RuntimeWarning)
                roundtrip = reopen_candidate(candidate, root / "reopened")
            qa = run_generic_qa(
                candidate,
                roundtrip,
                {
                    "body_names": ["open", "missing"],
                    "bounds_mm": [12.0, 10.0, 1.0],
                    "bounds_tolerance_mm": 0.01,
                },
            )
            blocker_codes = {
                finding.code
                for finding in qa.findings
                if finding.severity == Severity.BLOCKER
            }
            self.assertTrue({"NOT_WATERTIGHT", "BODY_SET_MISMATCH", "BOUNDS_MISMATCH"} <= blocker_codes)

    def test_qa_keeps_support_risk_as_warning_not_blocker(self):
        with tempfile.TemporaryDirectory() as temporary:
            identity, roundtrip = make_box_candidate(pathlib.Path(temporary))
            qa = run_generic_qa(
                identity.path,
                roundtrip,
                {"support_risk": "horizontal bridge needs slicer review"},
            )
            support = [item for item in qa.findings if item.code == "SUPPORT_RISK"]
            self.assertEqual(len(support), 1)
            self.assertEqual(support[0].severity, Severity.WARNING)
            self.assertFalse(qa.has_blocker)

    def test_qa_records_unavailable_reliable_check_explicitly(self):
        with tempfile.TemporaryDirectory() as temporary:
            identity, roundtrip = make_box_candidate(pathlib.Path(temporary))
            qa = run_generic_qa(identity.path, roundtrip, {})
            self.assertEqual(qa.checks["self_intersections"], "NOT_VERIFIED")
            self.assertEqual(qa.checks["minimum_wall_thickness"], "NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main()
