"""Create a release by byte-copying an exactly approved candidate."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import shutil
import tempfile
import uuid

from .approval import _validate_review
from .roundtrip import reopen_candidate
from .state import Status, advance_state, load_state


@dataclasses.dataclass(frozen=True)
class ReleaseInputs:
    project_dir: pathlib.Path
    model: str
    version: str
    candidate: pathlib.Path
    qa_path: pathlib.Path
    approval_path: pathlib.Path
    sha256: str
    short_id: str
    preview_paths: tuple[pathlib.Path, ...]


def validate_release_gate(project_dir: pathlib.Path, version: str) -> ReleaseInputs:
    state = load_state(project_dir)
    if state.status != Status.APPROVED:
        raise ValueError(f"release requires approval; current status is {state.status.value}")
    model, candidate, review, qa_path, _, identity, previews = _validate_review(
        project_dir, version
    )
    approval_path = review / f"{model}_{version}_approval.json"
    if not approval_path.is_file():
        raise ValueError("approval evidence is missing")
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    expected = {
        "model": model,
        "version": version,
        "short_id": identity.short_id,
        "sha256": identity.sha256,
    }
    for key, value in expected.items():
        if approval.get(key) != value:
            label = "full SHA-256" if key == "sha256" else key.replace("_", " ")
            raise ValueError(f"approval {label} does not match candidate")
    exact_text = f"Утверждаю {model} {version}, ID {identity.short_id}."
    if approval.get("user_text") != exact_text:
        raise ValueError("approval text does not name the exact model, version, and ID")
    return ReleaseInputs(
        project_dir=project_dir.resolve(),
        model=model,
        version=version,
        candidate=candidate,
        qa_path=qa_path,
        approval_path=approval_path,
        sha256=identity.sha256,
        short_id=identity.short_id,
        preview_paths=tuple(previews),
    )


def _copy_supporting_evidence(inputs: ReleaseInputs, staging: pathlib.Path) -> None:
    requirements = inputs.project_dir / "00_brief" / "requirements.md"
    shutil.copyfile(requirements, staging / f"{inputs.model}_{inputs.version}_requirements.md")
    shutil.copyfile(inputs.qa_path, staging / inputs.qa_path.name)
    shutil.copyfile(inputs.approval_path, staging / inputs.approval_path.name)
    preview_destination = staging / "previews"
    preview_destination.mkdir()
    for path in inputs.preview_paths:
        shutil.copyfile(path, preview_destination / path.name)
    source = inputs.project_dir / "02_source"
    if source.is_dir() and any(source.iterdir()):
        shutil.copytree(source, staging / "source")


def release_candidate(project_dir: pathlib.Path, version: str) -> pathlib.Path:
    inputs = validate_release_gate(project_dir, version)
    release_root = project_dir / "05_release"
    destination = release_root / version
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite release: {destination}")
    release_root.mkdir(parents=True, exist_ok=True)
    staging = release_root / f".{version}.tmp-{uuid.uuid4().hex}"
    staging.mkdir()
    try:
        geometry = staging / f"{inputs.model}_{version}_geometry.3mf"
        shutil.copyfile(inputs.candidate, geometry)
        release_digest = hashlib.sha256(geometry.read_bytes()).hexdigest()
        if release_digest != inputs.sha256:
            raise ValueError("release full SHA-256 differs from approved candidate")
        with tempfile.TemporaryDirectory(prefix="cloud3d-release-reopen-") as temporary:
            roundtrip = reopen_candidate(geometry, pathlib.Path(temporary) / "reopened")
        _copy_supporting_evidence(inputs, staging)
        approval = json.loads(inputs.approval_path.read_text(encoding="utf-8"))
        manifest = {
            "schema_version": 1,
            "model": inputs.model,
            "version": version,
            "short_id": inputs.short_id,
            "candidate_sha256": inputs.sha256,
            "release_sha256": release_digest,
            "approval": approval,
            "roundtrip": {
                "unit": roundtrip.unit,
                "body_names": list(roundtrip.body_names),
                "bounds_mm": list(roundtrip.extents_mm),
                "colors": roundtrip.colors,
            },
        }
        (staging / f"{inputs.model}_{version}_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        staging.replace(destination)
        advance_state(project_dir, Status.RELEASED, f"released {version} {inputs.short_id}")
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return destination
