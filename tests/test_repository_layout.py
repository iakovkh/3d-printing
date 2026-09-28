from __future__ import annotations

import pathlib
import re
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={ROOT.as_posix()}",
            *args,
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


class RepositoryLayoutTest(unittest.TestCase):
    def test_normative_documents_exist_at_repository_root(self):
        for name in ("AGENTS.md", "00_PROJECT_INSTRUCTIONS.md", "01_CLOUD_WORKFLOW.md"):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_local_toolchains_caches_vendors_and_raw_renders_are_ignored(self):
        ignored = (
            "tools/blender/bin/blender.exe",
            ".superpowers/sdd/example/progress.md",
            ".venv/Scripts/python.exe",
            "projects/demo/02_source/vendor/pkg.py",
            "projects/demo/02_source/__pycache__/module.pyc",
            "projects/demo/03_build/v001/model.blend1",
            "projects/demo/04_review/v001/previews/model_v001_front_raw.png",
        )
        result = git("check-ignore", "--no-index", *ignored)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(result.stdout.splitlines()), set(ignored))

    def test_lfs_tracks_large_sources_but_keeps_deliverables_in_git(self):
        expected = {
            "fixture.blend": "lfs",
            "fixture.stl": "lfs",
            "fixture.step": "lfs",
            "fixture.stp": "lfs",
            "fixture.3mf": "unspecified",
            "fixture.png": "unspecified",
        }
        for path, wanted in expected.items():
            result = git("check-attr", "filter", "--", path)
            self.assertEqual(result.returncode, 0, result.stderr)
            actual = result.stdout.strip().rsplit(": ", 1)[-1]
            self.assertEqual(actual, wanted, path)

    def test_readme_contract_links_resolve(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        links = re.findall(r"\[[^]]+\]\(([^)]+\.md)\)", readme)
        self.assertGreaterEqual(len(links), 3)
        for link in links:
            self.assertTrue((ROOT / link).is_file(), link)

    def test_readme_shows_the_exact_machine_accepted_approval_sentence(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Утверждаю <model> v003, ID 8F21C4A9.", readme)


if __name__ == "__main__":
    unittest.main()
