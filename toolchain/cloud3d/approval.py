"""Record approval only for an exact, blocker-free candidate identity."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re

from .previews import verify_preview_traceability
from .state import Status, advance_state, load_state
from .three_mf import CandidateIdentity, inspect_package


_VERSION = re.compile(r"^v\d{3}$")


def _review_files(project_dir: pathlib.Path, version: str):
    if not _VERSION.fullmatch(version):
        raise ValueError(f"invalid version: {version}")
    build = project_dir / "03_build" / version
    candidates = list(build.glob(f"*_{version}_candidate.3mf"))
    if len(candidates) != 1:
        raise ValueError(f"expected exactly one candidate for {version}, got {len(candidates)}")
    candidate = candidates[0].resolve()
    suffix = f"_{version}_candidate"
    model = candidate.stem[: -len(suffix)]
    review = project_dir / "04_review" / version
    qa_path = review / f"{model}_{version}_qa.json"
    if not qa_path.is_file():
        raise ValueError(f"QA report is missing: {qa_path}")
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    return model, candidate, review, qa_path, qa


def _validate_review(project_dir: pathlib.Path, version: str):
    model, candidate, review, qa_path, qa = _review_files(project_dir, version)
    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    short_id = digest[:8].upper()
    if qa.get("sha256") != digest or qa.get("short_id") != short_id:
        raise ValueError("QA full SHA-256 or short ID does not match candidate")
    blockers = [
        finding for finding in qa.get("findings", []) if finding.get("severity") == "BLOCKER"
    ]
    if blockers:
        raise ValueError(f"QA contains {len(blockers)} BLOCKER finding(s)")
    package = inspect_package(candidate)
    identity = CandidateIdentity(
        path=candidate,
        sha256=digest,
        short_id=short_id,
        size_bytes=candidate.stat().st_size,
        body_names=package.body_names,
        bounds_mm=tuple(float(value) for value in qa["bounds_mm"]),
    )
    previews = sorted((review / "previews").glob(f"{model}_{version}_*.png"))
    if len(previews) != 8:
        raise ValueError(f"expected 8 traceable review previews, got {len(previews)}")
    verify_preview_traceability(previews, identity)
    return model, candidate, review, qa_path, qa, identity, previews


def record_approval(
    project_dir: pathlib.Path,
    version: str,
    short_id: str,
    sha256: str,
    user_text: str,
) -> pathlib.Path:
    """Persist exact approval and move READY_FOR_REVIEW to APPROVED."""
    state = load_state(project_dir)
    if state.status != Status.READY_FOR_REVIEW:
        raise ValueError(f"approval is not allowed in status {state.status.value}")
    model = state.slug.replace("-", "_")
    expected_text = f"Утверждаю {model} {version}, ID {short_id}."
    if user_text != expected_text:
        raise ValueError(f"approval must name the exact model, version, and ID: {expected_text}")
    actual_model, _, review, _, _, identity, _ = _validate_review(project_dir, version)
    if actual_model != model:
        raise ValueError(f"candidate model {actual_model!r} does not match project {model!r}")
    if short_id.upper() != identity.short_id:
        raise ValueError("approval short ID does not match candidate")
    if sha256.lower() != identity.sha256:
        raise ValueError("approval full SHA-256 does not match candidate")
    destination = review / f"{model}_{version}_approval.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite approval: {destination}")
    payload = {
        "schema_version": 1,
        "model": model,
        "version": version,
        "short_id": identity.short_id,
        "sha256": identity.sha256,
        "user_text": user_text,
        "recorded_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    }
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
    try:
        advance_state(project_dir, Status.APPROVED, user_text)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination
