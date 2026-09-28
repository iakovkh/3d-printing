"""Independent geometric QA for the reopened Staunton queen candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import re
import sys
from typing import TypedDict

import numpy
import trimesh


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from inspect_3mf import inspect_package


class QaResult(TypedDict):
    sha256: str
    short_id: str
    bounds_mm: list[float]
    body_count: int
    watertight: bool
    winding_consistent: bool
    euler_number: int
    degenerate_face_count: int
    connected_component_count: int
    base_diameter_mm: float
    hole_diameter_mm: float
    finial_outer_diameter_mm: float
    minimum_hole_ligament_mm: float
    crown_peak_count: int
    base_plane_error_mm: float
    blockers: list[str]
    warnings: list[str]


def candidate_version(candidate: pathlib.Path) -> str:
    match = re.search(r"_(v\d{3})_candidate$", candidate.stem)
    if match is None:
        raise ValueError(f"candidate filename is not versioned: {candidate.name}")
    return match.group(1)


def load_candidate_mesh(candidate: pathlib.Path):
    scene = trimesh.load(candidate, force="scene", process=False)
    if not isinstance(scene, trimesh.Scene):
        scene = trimesh.Scene(scene)
    instances = []
    for node_name in scene.graph.nodes_geometry:
        transform, geometry_name = scene.graph[node_name]
        geometry = scene.geometry[geometry_name].copy()
        geometry.apply_transform(transform)
        instances.append(geometry)
    if not instances:
        raise ValueError("candidate contains no mesh instances")
    return scene, trimesh.util.concatenate(instances)


def measure_concentric_rings(points_yz, center_y: float, center_z: float):
    points = numpy.asarray(points_yz, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("ring points must have shape N×2")
    radii = numpy.linalg.norm(points - numpy.array([center_y, center_z]), axis=1)
    values = numpy.sort(radii)
    split_indices = numpy.flatnonzero(numpy.diff(values) > 0.30) + 1
    clusters = [cluster for cluster in numpy.split(values, split_indices) if len(cluster) >= 4]
    if len(clusters) < 2:
        raise ValueError(f"expected inner and outer section rings, got medians {[float(numpy.median(c)) for c in clusters]}")
    medians = sorted(float(numpy.median(cluster)) for cluster in clusters)
    inner_radius = medians[0]
    outer_radius = medians[-1]
    return {
        "diameter_mm": 2.0 * inner_radius,
        "finial_outer_diameter_mm": 2.0 * outer_radius,
        "minimum_ligament_mm": outer_radius - inner_radius,
        "ring_radii_mm": medians,
    }


def measure_cross_section_loops(mesh: trimesh.Trimesh, center_z: float):
    section = mesh.section(
        plane_origin=[0.0, 0.0, center_z],
        plane_normal=[1.0, 0.0, 0.0],
    )
    if section is None:
        raise ValueError("X-normal section through finial is empty")
    points = []
    for entity in section.entities:
        array = numpy.asarray(entity.discrete(section.vertices), dtype=float)
        if len(array) >= 8:
            yz = array[:, 1:3]
            radii = numpy.linalg.norm(yz - numpy.array([0.0, center_z]), axis=1)
            region = yz[radii <= 4.60]
            if len(region) >= 4:
                points.append(region)
    if not points:
        raise ValueError("finial section contains no closed sampled paths")
    return numpy.vstack(points)


def measure_hole(mesh: trimesh.Trimesh, center_z: float = 46.0):
    points = measure_cross_section_loops(mesh, center_z)
    return measure_concentric_rings(points, center_y=0.0, center_z=center_z)


def measure_hole_or_blocker(mesh: trimesh.Trimesh, center_z: float = 46.0):
    try:
        return measure_hole(mesh, center_z), []
    except ValueError as error:
        return (
            {
                "diameter_mm": 0.0,
                "finial_outer_diameter_mm": 0.0,
                "minimum_ligament_mm": 0.0,
                "ring_radii_mm": [],
            },
            [f"could not identify the ring hole in reopened geometry: {error}"],
        )


def evaluate_hole(measurement, expected: float, tolerance: float):
    blockers = []
    diameter = float(measurement["diameter_mm"])
    if abs(diameter - expected) > tolerance:
        blockers.append(
            f"hole diameter {diameter:.3f} mm is outside {expected:.1f} ± {tolerance:.1f} mm"
        )
    if float(measurement["minimum_ligament_mm"]) < 2.2:
        blockers.append(
            f"minimum hole ligament {measurement['minimum_ligament_mm']:.3f} mm is below 2.2 mm"
        )
    return {"blockers": blockers}


def measure_base(mesh: trimesh.Trimesh):
    vertices = numpy.asarray(mesh.vertices, dtype=float)
    minimum_z = float(vertices[:, 2].min())
    bottom = vertices[vertices[:, 2] <= minimum_z + 0.02]
    flatness = float(numpy.ptp(bottom[:, 2])) if len(bottom) else math.inf
    diameter = float(max(mesh.extents[0], mesh.extents[1]))
    return {
        "diameter_mm": diameter,
        "plane_error_mm": max(abs(minimum_z), flatness),
    }


def count_peaks_from_polar_samples(theta, heights):
    theta = numpy.asarray(theta, dtype=float)
    heights = numpy.asarray(heights, dtype=float)
    if len(theta) != len(heights) or len(theta) < 8:
        raise ValueError("polar samples must contain matching arrays of at least eight values")
    span = float(heights.max() - heights.min())
    if span <= 0.05:
        return 0
    mask = heights >= float(heights.min()) + span * 0.72
    return int(numpy.count_nonzero(mask & ~numpy.roll(mask, 1)))


def count_crown_peaks(mesh: trimesh.Trimesh):
    vertices = numpy.asarray(mesh.vertices, dtype=float)
    radii = numpy.linalg.norm(vertices[:, :2], axis=1)
    crown = vertices[(vertices[:, 2] >= 39.0) & (vertices[:, 2] <= 43.7) & (radii >= 5.0)]
    if len(crown) < 32:
        raise ValueError("insufficient crown vertices for peak measurement")
    angles = numpy.mod(numpy.arctan2(crown[:, 1], crown[:, 0]), 2.0 * numpy.pi)
    bins = 192
    indices = numpy.floor(angles / (2.0 * numpy.pi) * bins).astype(int) % bins
    envelope = numpy.full(bins, numpy.nan)
    for index, z_value in zip(indices, crown[:, 2]):
        if numpy.isnan(envelope[index]) or z_value > envelope[index]:
            envelope[index] = z_value
    known = numpy.flatnonzero(~numpy.isnan(envelope))
    if len(known) < 16:
        raise ValueError("crown angular envelope is undersampled")
    extended_x = numpy.concatenate((known - bins, known, known + bins))
    extended_y = numpy.concatenate((envelope[known], envelope[known], envelope[known]))
    envelope = numpy.interp(numpy.arange(bins), extended_x, extended_y)
    theta = numpy.linspace(0.0, 2.0 * numpy.pi, bins, endpoint=False)
    return count_peaks_from_polar_samples(theta, envelope)


def format_markdown(result: QaResult, package: dict, version: str):
    lines = [
        f"# Staunton queen keychain {version} — reopened candidate QA",
        "",
        f"- Candidate ID: `{result['short_id']}`",
        f"- SHA-256: `{result['sha256']}`",
        f"- Bounds: `{result['bounds_mm'][0]:.3f} × {result['bounds_mm'][1]:.3f} × {result['bounds_mm'][2]:.3f} mm`",
        f"- Body count: `{result['body_count']}`",
        f"- Connected components: `{result['connected_component_count']}`",
        f"- Watertight: `{result['watertight']}`",
        f"- Winding consistent: `{result['winding_consistent']}`",
        f"- Euler number: `{result['euler_number']}`",
        f"- Degenerate faces: `{result['degenerate_face_count']}`",
        f"- Base diameter: `{result['base_diameter_mm']:.3f} mm`",
        f"- Ring hole: `{result['hole_diameter_mm']:.3f} mm`",
        f"- Finial outer diameter: `{result['finial_outer_diameter_mm']:.3f} mm`",
        f"- Minimum hole ligament: `{result['minimum_hole_ligament_mm']:.3f} mm`",
        f"- Crown peaks: `{result['crown_peak_count']}`",
        f"- Base-plane error: `{result['base_plane_error_mm']:.4f} mm`",
        f"- 3MF XML: `{package['vertex_count']}` vertices / `{package['triangle_count']}` triangles",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- {item}" for item in result["blockers"]] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in result["warnings"]] or ["- None"])
    return "\n".join(lines) + "\n"


def run_qa(candidate: pathlib.Path, review_dir: pathlib.Path) -> QaResult:
    version = candidate_version(candidate)
    package = inspect_package(candidate)
    payload = candidate.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    scene, mesh = load_candidate_mesh(candidate)
    bounds = numpy.asarray(mesh.extents, dtype=float)
    face_vertices = numpy.asarray(mesh.vertices)[numpy.asarray(mesh.faces)]
    double_area = numpy.linalg.norm(
        numpy.cross(
            face_vertices[:, 1] - face_vertices[:, 0],
            face_vertices[:, 2] - face_vertices[:, 0],
        ),
        axis=1,
    )
    degenerate = int(numpy.count_nonzero(double_area <= 1e-10))
    connected = len(mesh.split(only_watertight=False))
    hole, hole_blockers = measure_hole_or_blocker(mesh)
    base = measure_base(mesh)
    peaks = count_crown_peaks(mesh)

    blockers = list(hole_blockers)
    if len(scene.geometry) != 1:
        blockers.append(f"expected one 3MF geometry, found {len(scene.geometry)}")
    if connected != 1:
        blockers.append(f"expected one connected component, found {connected}")
    if not mesh.is_watertight:
        blockers.append("reopened mesh is not watertight")
    if not mesh.is_winding_consistent:
        blockers.append("reopened mesh winding is inconsistent")
    if degenerate:
        blockers.append(f"found {degenerate} degenerate faces")
    expected_bounds = numpy.array([22.5, 22.5, 50.0])
    if numpy.any(numpy.abs(bounds - expected_bounds) > 0.10):
        blockers.append(f"bounds {bounds.tolist()} are outside [22.5, 22.5, 50.0] ± 0.10 mm")
    if abs(base["diameter_mm"] - 22.5) > 0.10:
        blockers.append(f"base diameter {base['diameter_mm']:.3f} mm is outside 22.5 ± 0.10 mm")
    if not hole_blockers:
        blockers.extend(evaluate_hole(hole, expected=3.2, tolerance=0.10)["blockers"])
    if peaks != 8:
        blockers.append(f"expected 8 crown peaks, measured {peaks}")
    if base["plane_error_mm"] > 0.05:
        blockers.append(f"base-plane error {base['plane_error_mm']:.4f} mm exceeds 0.05 mm")

    warnings = [
        "Horizontal 3.2 mm bore creates a short bridge; inspect the sliced roof and add local support only if needed",
        "Crown valleys and tooth undersides may create local overhangs; inspect layers in Anycubic Slicer Next",
        "Slicer profile, seam, material flow, print time, and support placement are not validated by geometry QA",
    ]

    result: QaResult = {
        "sha256": digest,
        "short_id": digest[:8].upper(),
        "bounds_mm": [round(float(value), 4) for value in bounds],
        "body_count": len(scene.geometry),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "euler_number": int(mesh.euler_number),
        "degenerate_face_count": degenerate,
        "connected_component_count": connected,
        "base_diameter_mm": round(float(base["diameter_mm"]), 4),
        "hole_diameter_mm": round(float(hole["diameter_mm"]), 4),
        "finial_outer_diameter_mm": round(float(hole["finial_outer_diameter_mm"]), 4),
        "minimum_hole_ligament_mm": round(float(hole["minimum_ligament_mm"]), 4),
        "crown_peak_count": peaks,
        "base_plane_error_mm": round(float(base["plane_error_mm"]), 6),
        "blockers": blockers,
        "warnings": warnings,
    }

    review_dir.mkdir(parents=True, exist_ok=True)
    (review_dir / "reopened_body.stl").write_bytes(mesh.export(file_type="stl"))
    json_path = review_dir / f"staunton_queen_keychain_{version}_qa.json"
    markdown_path = review_dir / f"staunton_queen_keychain_{version}_qa.md"
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(format_markdown(result, package, version), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--review-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    result = run_qa(args.candidate, args.review_dir)
    print("QA_RESULT=" + json.dumps(result, sort_keys=True))
    if result["blockers"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
