from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from PIL import Image

from tests.fixtures.meshes import write_box_stl
from toolchain.cloud3d.approval import record_approval
from toolchain.cloud3d.previews import label_and_compose
from toolchain.cloud3d.project import create_project
from toolchain.cloud3d.qa import run_generic_qa
from toolchain.cloud3d.release import release_candidate, validate_release_gate
from toolchain.cloud3d.roundtrip import reopen_candidate
from toolchain.cloud3d.state import (
    Status,
    advance_state,
    configure_requirements,
    set_current_version,
)
from toolchain.cloud3d.three_mf import BodyInput, build_candidate


IDENTITY = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


def review_fixture(root: pathlib.Path, *, blocker: bool = False):
    project = create_project(root, "fixture", "Make a test fixture.")
    configure_requirements(
        project,
        classification="FUNCTIONAL",
        concept_required=False,
        critical_questions_open=False,
    )
    advance_state(project, Status.WAITING_FOR_INPUT, "requirements drafted")
    advance_state(project, Status.READY_TO_MODEL, "requirements approved")
    advance_state(project, Status.GEOMETRY_DRAFT, "modeling started")
    set_current_version(project, "v001")
    build = project / "03_build" / "v001"
    build.mkdir()
    source = write_box_stl(build / "body.stl", (10.0, 20.0, 30.0))
    candidate = build / "fixture_v001_candidate.3mf"
    identity = build_candidate([BodyInput(source, "body", "#336699", IDENTITY)], candidate)
    reopened = reopen_candidate(candidate, build / "reopened")
    expectations = {"bounds_mm": [11.0, 20.0, 30.0]} if blocker else {}
    qa = run_generic_qa(candidate, reopened, expectations)
    review = project / "04_review" / "v001"
    review.mkdir()
    (review / "fixture_v001_qa.json").write_text(
        json.dumps(qa.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    raw = review / "raw"
    raw.mkdir()
    for view in ("front", "back", "side", "top", "isometric"):
        Image.new("RGB", (320, 320), (45, 90, 135)).save(
            raw / f"fixture_v001_{view}_raw.png"
        )
    label_and_compose(raw, review / "previews", identity, qa)
    advance_state(project, Status.READY_FOR_REVIEW, "candidate reopened and reviewed")
    return project, identity


class ReleaseGateTest(unittest.TestCase):
    def test_rejects_missing_approval_wrong_version_short_id_or_full_sha(self):
        with tempfile.TemporaryDirectory() as temporary:
            project, identity = review_fixture(pathlib.Path(temporary))
            with self.assertRaisesRegex(ValueError, "approval"):
                validate_release_gate(project, "v001")
            with self.assertRaisesRegex(ValueError, "exact model, version, and ID"):
                record_approval(
                    project,
                    "v002",
                    identity.short_id,
                    identity.sha256,
                    f"Утверждаю fixture v001, ID {identity.short_id}.",
                )
            with self.assertRaisesRegex(ValueError, "short ID"):
                record_approval(
                    project,
                    "v001",
                    "00000000",
                    identity.sha256,
                    "Утверждаю fixture v001, ID 00000000.",
                )
            with self.assertRaisesRegex(ValueError, "full SHA-256"):
                record_approval(
                    project,
                    "v001",
                    identity.short_id,
                    "0" * 64,
                    f"Утверждаю fixture v001, ID {identity.short_id}.",
                )

    def test_rejects_qa_with_any_blocker(self):
        with tempfile.TemporaryDirectory() as temporary:
            project, identity = review_fixture(pathlib.Path(temporary), blocker=True)
            with self.assertRaisesRegex(ValueError, "BLOCKER"):
                record_approval(
                    project,
                    "v001",
                    identity.short_id,
                    identity.sha256,
                    f"Утверждаю fixture v001, ID {identity.short_id}.",
                )

    def test_release_refuses_existing_release_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            project, identity = review_fixture(pathlib.Path(temporary))
            record_approval(
                project,
                "v001",
                identity.short_id,
                identity.sha256,
                f"Утверждаю fixture v001, ID {identity.short_id}.",
            )
            (project / "05_release" / "v001").mkdir()
            with self.assertRaises(FileExistsError):
                release_candidate(project, "v001")

    def test_release_copies_bytes_reopens_and_writes_matching_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            project, identity = review_fixture(pathlib.Path(temporary))
            record_approval(
                project,
                "v001",
                identity.short_id,
                identity.sha256,
                f"Утверждаю fixture v001, ID {identity.short_id}.",
            )
            release = release_candidate(project, "v001")
            geometry = release / "fixture_v001_geometry.3mf"
            self.assertEqual(geometry.read_bytes(), identity.path.read_bytes())
            manifest = json.loads(
                (release / "fixture_v001_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["candidate_sha256"], identity.sha256)
            self.assertEqual(manifest["release_sha256"], identity.sha256)
            self.assertEqual(manifest["short_id"], identity.short_id)
            self.assertEqual(manifest["roundtrip"]["body_names"], ["body"])

    def test_same_short_id_with_different_full_sha_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            project, identity = review_fixture(pathlib.Path(temporary))
            approval = record_approval(
                project,
                "v001",
                identity.short_id,
                identity.sha256,
                f"Утверждаю fixture v001, ID {identity.short_id}.",
            )
            data = json.loads(approval.read_text(encoding="utf-8"))
            data["sha256"] = identity.short_id.lower() + "0" * 56
            approval.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "full SHA-256"):
                validate_release_gate(project, "v001")


if __name__ == "__main__":
    unittest.main()
