from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from PIL import Image

from tests.test_release_gate import review_fixture
from toolchain.cloud3d.repository import validate_repository
from toolchain.run_smoke_test import run_smoke


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def codes(report):
    return {finding.code for finding in report.findings if finding.severity == "BLOCKER"}


class RepositoryValidationTest(unittest.TestCase):
    def test_rejects_mixed_versions_and_duplicate_candidate_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            project, identity = review_fixture(root)
            duplicate_dir = project / "03_build" / "v002"
            duplicate_dir.mkdir()
            shutil.copyfile(identity.path, duplicate_dir / "fixture_v002_candidate.3mf")
            report = validate_repository(root)
            self.assertIn("DUPLICATE_CANDIDATE_IDENTITY", codes(report))
            self.assertIn("MIXED_ACTIVE_VERSIONS", codes(report))

    def test_rejects_geometry_created_before_requirements_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            project, _ = review_fixture(root)
            state_path = project / "project-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["requirements_approval"] = None
            state["history"] = [entry for entry in state["history"] if entry["to"] != "READY_TO_MODEL"]
            state_path.write_text(json.dumps(state), encoding="utf-8")
            self.assertIn("GEOMETRY_BEFORE_REQUIREMENTS_APPROVAL", codes(validate_repository(root)))

    def test_rejects_release_without_approval_or_matching_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            project, identity = review_fixture(root)
            release = project / "05_release" / "v001"
            release.mkdir()
            geometry = release / "fixture_v001_geometry.3mf"
            geometry.write_bytes(identity.path.read_bytes() + b"tampered")
            (release / "fixture_v001_manifest.json").write_text(
                json.dumps(
                    {
                        "version": "v001",
                        "short_id": identity.short_id,
                        "candidate_sha256": identity.sha256,
                        "release_sha256": hashlib.sha256(geometry.read_bytes()).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )
            found = codes(validate_repository(root))
            self.assertIn("RELEASE_WITHOUT_APPROVAL", found)
            self.assertIn("RELEASE_HASH_MISMATCH", found)

    def test_accepts_complete_candidate_that_has_not_yet_been_approved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            review_fixture(root)
            report = validate_repository(root)
            self.assertTrue(report.ok, report.findings)

    def test_rejects_modified_committed_candidate_against_base_ref(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            candidate = root / "projects" / "fixture" / "03_build" / "v001" / "fixture_v001_candidate.3mf"
            candidate.parent.mkdir(parents=True)
            candidate.write_bytes(b"first")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
            base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            candidate.write_bytes(b"second")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "mutate"], cwd=root, check=True)
            report = validate_repository(root, base_ref=base)
            self.assertIn("IMMUTABLE_ARTIFACT_CHANGED", codes(report))

    def test_smoke_run_stops_at_ready_for_review_without_creating_release(self):
        def fake_renderer(manifest: pathlib.Path, output: pathlib.Path):
            data = json.loads(manifest.read_text(encoding="utf-8"))
            output.mkdir()
            for view in ("front", "back", "side", "top", "isometric"):
                Image.new("RGB", (720, 720), (60, 100, 140)).save(
                    output / f"{data['model']}_{data['version']}_{view}_raw.png"
                )

        with tempfile.TemporaryDirectory() as temporary:
            project = run_smoke(pathlib.Path(temporary), renderer=fake_renderer)
            state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "READY_FOR_REVIEW")
            self.assertEqual(state["current_version"], "v001")
            self.assertTrue(list((project / "03_build" / "v001").glob("*_candidate.3mf")))
            self.assertTrue((project / "04_review" / "v001" / "previews").is_dir())
            self.assertFalse((project / "05_release" / "v001").exists())


class WorkflowDefinitionTest(unittest.TestCase):
    def test_contract_workflow_exposes_required_status_and_validator(self):
        text = (REPO_ROOT / ".github" / "workflows" / "contract.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("contract:", text)
        self.assertIn("python -m unittest discover -s tests -v", text)
        self.assertIn("python -m toolchain.validate_repository", text)

    def test_cloud_smoke_installs_pinned_toolchain_and_never_releases(self):
        text = (REPO_ROOT / ".github" / "workflows" / "cloud-smoke.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("bash toolchain/setup_cloud.sh", text)
        self.assertIn("python -m toolchain.run_smoke_test", text)
        self.assertIn("05_release/v001", text)


if __name__ == "__main__":
    unittest.main()
