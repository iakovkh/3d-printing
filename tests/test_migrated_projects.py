from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PROJECTS = ("skull-egg-cup", "staunton-queen-keychain")
BINARY_SUFFIXES = {".3mf", ".blend", ".stl", ".png"}
LFS_SUFFIXES = {".blend", ".stl", ".step", ".stp"}


def manifest(slug: str):
    return json.loads(
        (ROOT / "projects" / slug / "migration-manifest.json").read_text(encoding="utf-8")
    )


class MigratedProjectsTest(unittest.TestCase):
    def test_every_included_binary_matches_recorded_pre_migration_sha256(self):
        for slug in PROJECTS:
            project = ROOT / "projects" / slug
            data = manifest(slug)
            included = set(data["included_paths"])
            hashes = data["binary_sha256"]
            binary_paths = {path for path in included if pathlib.Path(path).suffix.lower() in BINARY_SUFFIXES}
            self.assertEqual(set(hashes), binary_paths)
            for relative, expected in hashes.items():
                actual = hashlib.sha256((project / relative).read_bytes()).hexdigest()
                self.assertEqual(actual, expected, f"{slug}/{relative}")

    def test_no_cache_vendor_failed_candidate_or_noncanonical_blend_is_tracked(self):
        forbidden = ("__pycache__", "/vendor/", "failed_candidate", "reference_draft")
        for slug in PROJECTS:
            data = manifest(slug)
            for relative in data["included_paths"]:
                normalized = "/" + relative.replace("\\", "/")
                self.assertFalse(any(item in normalized for item in forbidden), relative)
            skull_blends = [
                path
                for path in data["included_paths"]
                if slug == "skull-egg-cup" and path.endswith(".blend") and path.startswith("03_build/")
            ]
            if slug == "skull-egg-cup":
                self.assertEqual(skull_blends, ["03_build/v001/skull_egg_cup_v001_source.blend"])

    def test_skull_release_geometry_still_matches_its_release_manifest(self):
        release = ROOT / "projects" / "skull-egg-cup" / "05_release" / "v001"
        data = json.loads((release / "skull_egg_cup_v001_manifest.json").read_text(encoding="utf-8"))
        geometry = release / "skull_egg_cup_v001_geometry.3mf"
        self.assertEqual(hashlib.sha256(geometry.read_bytes()).hexdigest(), data["candidate_sha256"])

    def test_queen_has_candidates_and_reviews_but_no_fabricated_release(self):
        project = ROOT / "projects" / "staunton-queen-keychain"
        data = manifest("staunton-queen-keychain")
        self.assertEqual(data["recorded_status"], "READY_FOR_REVIEW")
        self.assertEqual(data["approval_evidence"], None)
        self.assertTrue((project / "03_build" / "v001" / "staunton_queen_keychain_v001_candidate.3mf").is_file())
        self.assertTrue((project / "03_build" / "v002" / "staunton_queen_keychain_v002_candidate.3mf").is_file())
        self.assertFalse(any((project / "05_release").rglob("*.3mf")))

    def test_all_lfs_eligible_included_files_are_lfs_tracked(self):
        for slug in PROJECTS:
            for relative in manifest(slug)["included_paths"]:
                path = pathlib.Path(relative)
                if path.suffix.lower() not in LFS_SUFFIXES:
                    continue
                repo_relative = f"projects/{slug}/{relative}"
                result = subprocess.check_output(
                    ["git", "check-attr", "filter", "--", repo_relative],
                    cwd=ROOT,
                    text=True,
                )
                self.assertTrue(result.rstrip().endswith("filter: lfs"), result)

    def test_only_manifest_selected_project_files_are_staged(self):
        tracked = set(
            subprocess.check_output(
                ["git", "ls-files", "projects"], cwd=ROOT, text=True
            ).splitlines()
        )
        expected = set()
        for slug in PROJECTS:
            expected.add(f"projects/{slug}/migration-manifest.json")
            expected.update(
                f"projects/{slug}/{relative}" for relative in manifest(slug)["included_paths"]
            )
        self.assertEqual(tracked, expected)


if __name__ == "__main__":
    unittest.main()
