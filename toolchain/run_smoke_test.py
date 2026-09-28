"""Build a complete disposable candidate/review cycle without creating a release."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
from collections.abc import Callable

from cadquery import exporters

from tests.fixtures.smoke_project.model import build_model
from toolchain.cloud3d.previews import label_and_compose
from toolchain.cloud3d.project import create_project
from toolchain.cloud3d.qa import run_generic_qa
from toolchain.cloud3d.roundtrip import reopen_candidate
from toolchain.cloud3d.state import (
    Status,
    advance_state,
    configure_requirements,
    set_current_version,
)
from toolchain.cloud3d.three_mf import BodyInput, build_candidate


Renderer = Callable[[pathlib.Path, pathlib.Path], None]
IDENTITY = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


def _blender_renderer(manifest: pathlib.Path, output: pathlib.Path) -> None:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    executable = os.environ.get("CLOUD3D_BLENDER") or shutil.which("blender")
    local = repo_root / "tools" / "blender-5.2.1-windows-x64" / "blender.exe"
    if executable is None and local.is_file():
        executable = str(local)
    if executable is None:
        raise RuntimeError("Blender 5.2.1 is required for the smoke render")
    completed = subprocess.run(
        [
            executable,
            "--background",
            "--python",
            str(repo_root / "toolchain" / "blender" / "render_reopened.py"),
            "--",
            "--manifest",
            str(manifest),
            "--output-dir",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout + completed.stderr)


def run_smoke(output: pathlib.Path, renderer: Renderer | None = None) -> pathlib.Path:
    project = create_project(output, "cloud-smoke", "Create the pinned cloud toolchain smoke fixture.")
    configure_requirements(
        project,
        classification="FUNCTIONAL",
        concept_required=False,
        critical_questions_open=False,
    )
    advance_state(project, Status.WAITING_FOR_INPUT, "smoke requirements drafted")
    advance_state(project, Status.READY_TO_MODEL, "smoke requirements explicitly approved")
    advance_state(project, Status.GEOMETRY_DRAFT, "start smoke v001")
    set_current_version(project, "v001")

    build = project / "03_build" / "v001"
    build.mkdir()
    source = build / "cloud_smoke_body.stl"
    exporters.export(build_model(), str(source), exportType="STL")
    candidate = build / "cloud_smoke_v001_candidate.3mf"
    identity = build_candidate(
        [BodyInput(source, "body", "#3B82F6", IDENTITY)], candidate
    )
    roundtrip = reopen_candidate(candidate, build / "reopened")
    qa = run_generic_qa(
        candidate,
        roundtrip,
        {"body_names": ["body"], "bounds_mm": [30.0, 20.0, 8.0], "bounds_tolerance_mm": 0.05},
    )
    if qa.has_blocker:
        raise RuntimeError(f"smoke QA contains BLOCKER: {qa.findings}")
    review = project / "04_review" / "v001"
    review.mkdir()
    (review / "cloud_smoke_v001_qa.json").write_text(
        json.dumps(qa.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    manifest = review / "render-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "model": "cloud_smoke",
                "version": "v001",
                "short_id": identity.short_id,
                "bodies": [
                    {
                        "name": name,
                        "path": str(path),
                        "color": roundtrip.colors[name],
                    }
                    for name, path in roundtrip.reopened_bodies.items()
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    raw = review / "raw"
    (renderer or _blender_renderer)(manifest, raw)
    label_and_compose(raw, review / "previews", identity, qa)
    advance_state(project, Status.READY_FOR_REVIEW, "smoke candidate reopened, QA passed, previews generated")
    if (project / "05_release" / "v001").exists():
        raise RuntimeError("smoke must stop before release")
    return project


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    project = run_smoke(args.output)
    print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
