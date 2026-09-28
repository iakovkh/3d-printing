"""Generic geometric checks performed only on reopened candidate bodies."""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import pathlib
from collections.abc import Callable
from typing import Any

import numpy as np
import trimesh

from .roundtrip import RoundTripReport


class Severity(str, enum.Enum):
    BLOCKER = "BLOCKER"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclasses.dataclass(frozen=True)
class Finding:
    severity: Severity
    code: str
    message: str


@dataclasses.dataclass(frozen=True)
class QaReport:
    candidate: pathlib.Path
    sha256: str
    short_id: str
    unit: str
    bounds_mm: tuple[float, float, float]
    body_names: tuple[str, ...]
    colors: dict[str, str]
    watertight: dict[str, bool]
    connected_components: dict[str, int]
    findings: tuple[Finding, ...]
    checks: dict[str, str]
    measurements: dict[str, Any]

    @property
    def has_blocker(self) -> bool:
        return any(item.severity == Severity.BLOCKER for item in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate": str(self.candidate),
            "sha256": self.sha256,
            "short_id": self.short_id,
            "unit": self.unit,
            "bounds_mm": list(self.bounds_mm),
            "body_names": list(self.body_names),
            "colors": self.colors,
            "watertight": self.watertight,
            "connected_components": self.connected_components,
            "findings": [
                {
                    "severity": finding.severity.value,
                    "code": finding.code,
                    "message": finding.message,
                }
                for finding in self.findings
            ],
            "checks": self.checks,
            "measurements": self.measurements,
        }


MeasurementCallback = Callable[[RoundTripReport], dict[str, Any]]


def run_generic_qa(
    candidate: pathlib.Path,
    roundtrip: RoundTripReport,
    expectations: dict[str, Any],
    measurement_callback: MeasurementCallback | None = None,
) -> QaReport:
    candidate = candidate.resolve()
    if roundtrip.candidate != candidate:
        raise ValueError("round-trip report belongs to a different candidate")
    payload = candidate.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    findings: list[Finding] = []
    watertight: dict[str, bool] = {}
    components: dict[str, int] = {}
    for name in roundtrip.body_names:
        mesh = trimesh.load_mesh(roundtrip.reopened_bodies[name], process=False)
        if not isinstance(mesh, trimesh.Trimesh):
            findings.append(
                Finding(Severity.BLOCKER, "INVALID_REOPENED_BODY", f"{name} is not a mesh")
            )
            continue
        # Binary STL repeats vertices per triangle. Re-index identical positions
        # before topology checks; this changes connectivity representation, not geometry.
        mesh.merge_vertices(merge_tex=True, merge_norm=True)
        mesh.remove_unreferenced_vertices()
        watertight[name] = bool(mesh.is_watertight)
        components[name] = len(mesh.split(only_watertight=False))
        if not mesh.is_watertight:
            findings.append(
                Finding(Severity.BLOCKER, "NOT_WATERTIGHT", f"{name} is not watertight")
            )
        if components[name] != 1:
            findings.append(
                Finding(
                    Severity.BLOCKER,
                    "CONNECTED_COMPONENTS",
                    f"{name} has {components[name]} connected components",
                )
            )
        if not mesh.is_winding_consistent:
            findings.append(
                Finding(Severity.BLOCKER, "INCONSISTENT_NORMALS", f"{name} winding is inconsistent")
            )
        if bool(np.any(mesh.area_faces <= 1e-12)):
            findings.append(
                Finding(Severity.BLOCKER, "DEGENERATE_FACES", f"{name} has degenerate faces")
            )

    expected_names = expectations.get("body_names")
    if expected_names is not None and tuple(expected_names) != roundtrip.body_names:
        findings.append(
            Finding(
                Severity.BLOCKER,
                "BODY_SET_MISMATCH",
                f"expected bodies {tuple(expected_names)}, got {roundtrip.body_names}",
            )
        )
    expected_bounds = expectations.get("bounds_mm")
    if expected_bounds is not None:
        tolerance = float(expectations.get("bounds_tolerance_mm", 0.0))
        if not np.allclose(roundtrip.extents_mm, expected_bounds, atol=tolerance, rtol=0.0):
            findings.append(
                Finding(
                    Severity.BLOCKER,
                    "BOUNDS_MISMATCH",
                    f"expected {expected_bounds} ±{tolerance} mm, got {roundtrip.extents_mm}",
                )
            )
    support_risk = expectations.get("support_risk")
    if support_risk:
        findings.append(Finding(Severity.WARNING, "SUPPORT_RISK", str(support_risk)))
    measurements = measurement_callback(roundtrip) if measurement_callback else {}
    return QaReport(
        candidate=candidate,
        sha256=digest,
        short_id=digest[:8].upper(),
        unit=roundtrip.unit,
        bounds_mm=roundtrip.extents_mm,
        body_names=roundtrip.body_names,
        colors=roundtrip.colors,
        watertight=watertight,
        connected_components=components,
        findings=tuple(findings),
        checks={
            "package_roundtrip": "VERIFIED",
            "self_intersections": "NOT_VERIFIED",
            "minimum_wall_thickness": "NOT_VERIFIED",
        },
        measurements=measurements,
    )
