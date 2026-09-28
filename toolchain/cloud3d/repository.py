"""Repository-wide contract validation for structured and migrated projects."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import re
import subprocess

from .state import Status, load_state


@dataclasses.dataclass(frozen=True)
class ValidationFinding:
    severity: str
    code: str
    message: str
    path: str | None = None


@dataclasses.dataclass(frozen=True)
class ValidationReport:
    findings: tuple[ValidationFinding, ...]

    @property
    def ok(self) -> bool:
        return not any(item.severity == "BLOCKER" for item in self.findings)


def _block(findings: list[ValidationFinding], code: str, message: str, path=None):
    findings.append(
        ValidationFinding("BLOCKER", code, message, str(path) if path is not None else None)
    )


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_lifecycle(project: pathlib.Path, findings: list[ValidationFinding]) -> None:
    state = load_state(project)
    candidates = sorted(project.glob("03_build/v[0-9][0-9][0-9]/*_candidate.3mf"))
    if candidates and (
        state.requirements_approval is None
        or not any(entry.get("to") == Status.READY_TO_MODEL.value for entry in state.history)
    ):
        _block(
            findings,
            "GEOMETRY_BEFORE_REQUIREMENTS_APPROVAL",
            "candidate geometry exists without recorded requirements approval",
            project,
        )

    by_digest: dict[str, list[pathlib.Path]] = {}
    versions = set()
    for candidate in candidates:
        versions.add(candidate.parent.name)
        by_digest.setdefault(_digest(candidate), []).append(candidate)
        match = re.fullmatch(r"(.+)_(v\d{3})_candidate\.3mf", candidate.name)
        if match is None or match.group(2) != candidate.parent.name:
            _block(findings, "MIXED_ACTIVE_VERSIONS", "candidate path and filename versions differ", candidate)
    for digest, paths in by_digest.items():
        if len(paths) > 1:
            _block(
                findings,
                "DUPLICATE_CANDIDATE_IDENTITY",
                f"candidate SHA-256 {digest} is reused across versions",
                project,
            )
    if state.current_version is not None:
        foreign = [path for path in candidates if path.parent.name > state.current_version]
        if foreign:
            _block(
                findings,
                "MIXED_ACTIVE_VERSIONS",
                f"candidate newer than state current_version {state.current_version}",
                foreign[0],
            )
    elif len(versions) > 1:
        _block(findings, "MIXED_ACTIVE_VERSIONS", "multiple versions exist without current_version", project)

    for release in sorted(project.glob("05_release/v[0-9][0-9][0-9]")):
        version = release.name
        geometry = list(release.glob(f"*_{version}_geometry.3mf"))
        manifests = list(release.glob(f"*_{version}_manifest.json"))
        approvals = list((project / "04_review" / version).glob(f"*_{version}_approval.json"))
        if len(approvals) != 1:
            _block(findings, "RELEASE_WITHOUT_APPROVAL", "release lacks exact approval evidence", release)
        if len(geometry) != 1 or len(manifests) != 1:
            _block(findings, "INCOMPLETE_RELEASE", "release geometry or manifest is missing", release)
            continue
        manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
        release_digest = _digest(geometry[0])
        build_candidates = list((project / "03_build" / version).glob(f"*_{version}_candidate.3mf"))
        candidate_digest = _digest(build_candidates[0]) if len(build_candidates) == 1 else None
        if (
            manifest.get("release_sha256") != release_digest
            or manifest.get("candidate_sha256") != candidate_digest
            or release_digest != candidate_digest
        ):
            _block(
                findings,
                "RELEASE_HASH_MISMATCH",
                "release bytes, candidate bytes, or manifest hashes differ",
                release,
            )


def _immutable_diff(repo_root: pathlib.Path, base_ref: str, findings: list[ValidationFinding]):
    completed = subprocess.run(
        ["git", "diff", "--name-status", f"{base_ref}...HEAD", "--", "projects"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        _block(findings, "BASE_REF_UNAVAILABLE", completed.stderr.strip() or "git diff failed")
        return
    immutable = re.compile(
        r"^projects/[^/]+/(?:03_build/v\d{3}/[^/]+_candidate\.3mf|05_release/v\d{3}/)"
    )
    for line in completed.stdout.splitlines():
        fields = line.split("\t")
        status = fields[0]
        paths = fields[1:]
        if status[0] in {"M", "D", "R"} and any(immutable.match(path) for path in paths):
            _block(
                findings,
                "IMMUTABLE_ARTIFACT_CHANGED",
                f"committed candidate/release changed relative to {base_ref}: {line}",
            )


def validate_repository(
    repo_root: pathlib.Path, base_ref: str | None = None
) -> ValidationReport:
    repo_root = repo_root.resolve()
    findings: list[ValidationFinding] = []
    projects = repo_root / "projects"
    if projects.is_dir():
        for project in sorted(path for path in projects.iterdir() if path.is_dir()):
            if (project / "project-state.json").is_file():
                try:
                    _validate_lifecycle(project, findings)
                except Exception as error:
                    _block(findings, "PROJECT_VALIDATION_ERROR", str(error), project)
    if base_ref:
        _immutable_diff(repo_root, base_ref, findings)
    return ValidationReport(tuple(findings))
