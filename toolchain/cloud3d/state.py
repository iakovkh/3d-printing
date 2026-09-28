"""Machine-readable lifecycle gates mirroring the approved contract."""

from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import json
import pathlib
from typing import Any


class Status(str, enum.Enum):
    INTAKE = "INTAKE"
    WAITING_FOR_INPUT = "WAITING_FOR_INPUT"
    READY_TO_MODEL = "READY_TO_MODEL"
    GEOMETRY_DRAFT = "GEOMETRY_DRAFT"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    RELEASED = "RELEASED"


@dataclasses.dataclass(frozen=True)
class ApprovalEvidence:
    user_text: str
    recorded_at: str


@dataclasses.dataclass(frozen=True)
class ProjectState:
    schema_version: int
    slug: str
    classification: str | None
    status: Status
    critical_questions_open: bool
    concept_required: bool
    current_version: str | None
    requirements_approval: ApprovalEvidence | None
    concept_approval: ApprovalEvidence | None
    history: tuple[dict[str, str], ...]


_ALLOWED_TRANSITIONS = {
    Status.INTAKE: {Status.WAITING_FOR_INPUT},
    Status.WAITING_FOR_INPUT: {Status.READY_TO_MODEL},
    Status.READY_TO_MODEL: {Status.GEOMETRY_DRAFT},
    Status.GEOMETRY_DRAFT: {Status.READY_FOR_REVIEW},
    Status.READY_FOR_REVIEW: {Status.GEOMETRY_DRAFT, Status.APPROVED},
    Status.APPROVED: {Status.RELEASED},
    Status.RELEASED: set(),
}


def _approval(raw: dict[str, str] | None) -> ApprovalEvidence | None:
    return ApprovalEvidence(**raw) if raw else None


def _from_dict(raw: dict[str, Any]) -> ProjectState:
    return ProjectState(
        schema_version=int(raw["schema_version"]),
        slug=str(raw["slug"]),
        classification=raw["classification"],
        status=Status(raw["status"]),
        critical_questions_open=bool(raw["critical_questions_open"]),
        concept_required=bool(raw["concept_required"]),
        current_version=raw["current_version"],
        requirements_approval=_approval(raw["requirements_approval"]),
        concept_approval=_approval(raw["concept_approval"]),
        history=tuple(raw["history"]),
    )


def _to_dict(state: ProjectState) -> dict[str, Any]:
    data = dataclasses.asdict(state)
    data["status"] = state.status.value
    data["history"] = list(state.history)
    return data


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _write_state(project_dir: pathlib.Path, state: ProjectState) -> None:
    destination = project_dir / "project-state.json"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(_to_dict(state), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def load_state(project_dir: pathlib.Path) -> ProjectState:
    raw = json.loads((project_dir / "project-state.json").read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError("unsupported project-state schema_version")
    return _from_dict(raw)


def configure_requirements(
    project_dir: pathlib.Path,
    *,
    classification: str,
    concept_required: bool,
    critical_questions_open: bool,
) -> ProjectState:
    if classification not in {"FUNCTIONAL", "ORGANIC", "HYBRID"}:
        raise ValueError(f"unsupported classification: {classification}")
    state = load_state(project_dir)
    if state.status not in {Status.INTAKE, Status.WAITING_FOR_INPUT}:
        raise ValueError("requirements can only be configured during intake")
    updated = dataclasses.replace(
        state,
        classification=classification,
        concept_required=concept_required,
        critical_questions_open=critical_questions_open,
    )
    _write_state(project_dir, updated)
    return updated


def record_concept_approval(project_dir: pathlib.Path, evidence: str) -> ProjectState:
    if not evidence.strip():
        raise ValueError("concept approval evidence is required")
    state = load_state(project_dir)
    if not state.concept_required:
        raise ValueError("concept approval is not required for this project")
    if state.status != Status.READY_TO_MODEL:
        raise ValueError("concept can only be approved after requirements")
    updated = dataclasses.replace(
        state,
        concept_approval=ApprovalEvidence(evidence, _now()),
    )
    _write_state(project_dir, updated)
    return updated


def assert_modeling_allowed(project_dir: pathlib.Path) -> None:
    state = load_state(project_dir)
    if state.status not in {Status.READY_TO_MODEL, Status.GEOMETRY_DRAFT}:
        raise ValueError(f"modeling is not allowed in status {state.status.value}")
    if state.requirements_approval is None:
        raise ValueError("requirements approval is required before modeling")
    if state.concept_required and state.concept_approval is None:
        raise ValueError("concept approval is required before modeling")


def advance_state(
    project_dir: pathlib.Path, target: Status, evidence: str
) -> ProjectState:
    if not evidence.strip():
        raise ValueError("transition evidence is required")
    state = load_state(project_dir)
    if target not in _ALLOWED_TRANSITIONS[state.status]:
        raise ValueError(f"invalid transition {state.status.value} -> {target.value}")
    requirements_approval = state.requirements_approval
    if target == Status.READY_TO_MODEL:
        if state.classification is None:
            raise ValueError("classification is required before approval")
        if state.critical_questions_open:
            raise ValueError("critical questions remain open")
        requirements_approval = ApprovalEvidence(evidence, _now())
    if target == Status.GEOMETRY_DRAFT and state.status == Status.READY_TO_MODEL:
        assert_modeling_allowed(project_dir)
    entry = {
        "from": state.status.value,
        "to": target.value,
        "evidence": evidence,
        "recorded_at": _now(),
    }
    updated = dataclasses.replace(
        state,
        status=target,
        requirements_approval=requirements_approval,
        history=(*state.history, entry),
    )
    _write_state(project_dir, updated)
    return updated
