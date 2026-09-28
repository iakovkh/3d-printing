from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import sys
from typing import TypedDict

import numpy
import trimesh


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from inspect_3mf import inspect_package  # noqa: E402


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
    opening_diameter_mm: float
    cavity_depth_mm: float
    minimum_wall_mm: float
    base_plane_error_mm: float
    blockers: list[str]
    warnings: list[str]


def reopened_mesh(candidate: pathlib.Path):
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


def centered_section_loops(mesh: trimesh.Trimesh, z_value: float):
    section = mesh.section(plane_origin=[0.0, 0.0, z_value], plane_normal=[0.0, 0.0, 1.0])
    if section is None:
        return []
    loops = []
    for path in section.discrete:
        points = numpy.asarray(path)[:, :2]
        if len(points) < 8:
            continue
        centroid = points.mean(axis=0)
        radii = numpy.linalg.norm(points - centroid, axis=1)
        mean_radius = float(numpy.median(radii))
        if numpy.linalg.norm(centroid) <= 2.5 and 2.0 <= mean_radius <= 40.0:
            loops.append(
                {
                    "centroid": centroid,
                    "mean_radius": mean_radius,
                    "radial_std": float(radii.std()),
                    "closed_error": float(numpy.linalg.norm(points[0] - points[-1])),
                }
            )
    return sorted(loops, key=lambda item: item["mean_radius"])


def measure_opening(mesh: trimesh.Trimesh):
    top = float(mesh.bounds[1, 2])
    loops = centered_section_loops(mesh, top - 0.35)
    candidates = [loop for loop in loops if 17.0 <= loop["mean_radius"] <= 23.0]
    if not candidates:
        raise ValueError(f"could not identify opening loop at z={top - 0.35:.3f}: {loops}")
    opening = min(candidates, key=lambda loop: abs(loop["mean_radius"] - 21.0))
    return 2.0 * opening["mean_radius"]


def measure_cavity_depth(mesh: trimesh.Trimesh):
    top = float(mesh.bounds[1, 2])
    vertices = numpy.asarray(mesh.vertices)
    radius = numpy.linalg.norm(vertices[:, :2], axis=1)
    candidates = vertices[(radius <= 0.55) & (vertices[:, 2] >= top - 35.0) & (vertices[:, 2] <= top - 1.0)]
    if not len(candidates):
        raise ValueError("could not identify the cavity bottom near the central axis")
    bottom = float(candidates[:, 2].max())
    # The central bowl vertex is the highest central-axis surface below the opening.
    return top - bottom


def measure_functional_wall(mesh: trimesh.Trimesh):
    top = float(mesh.bounds[1, 2])
    gaps = []
    details = []
    for offset in (0.6, 2.0, 4.0, 7.0, 10.0):
        z_value = top - offset
        loops = centered_section_loops(mesh, z_value)
        if len(loops) < 2:
            continue
        for inner, outer in zip(loops, loops[1:]):
            if inner["mean_radius"] <= 23.0 and outer["mean_radius"] > inner["mean_radius"] + 1.0:
                gap = outer["mean_radius"] - inner["mean_radius"]
                gaps.append(gap)
                details.append((z_value, gap))
                break
    if not gaps:
        raise ValueError("could not derive functional wall from horizontal sections")
    return min(gaps), details


def format_markdown(result: QaResult, package: dict, wall_sections: list[tuple[float, float]]):
    lines = [
        "# Skull egg cup v001 — reopened candidate QA",
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
        f"- Opening: `{result['opening_diameter_mm']:.3f} mm`",
        f"- Bowl depth: `{result['cavity_depth_mm']:.3f} mm`",
        f"- Minimum measured functional wall: `{result['minimum_wall_mm']:.3f} mm`",
        f"- Base-plane error: `{result['base_plane_error_mm']:.4f} mm`",
        f"- 3MF XML: `{package['vertex_count']}` vertices / `{package['triangle_count']}` triangles",
        "",
        "## Section wall samples",
        "",
    ]
    lines.extend(f"- Z `{z_value:.3f}` mm: `{gap:.3f}` mm" for z_value, gap in wall_sections)
    lines.extend(["", "## Blockers", ""])
    lines.extend([f"- {item}" for item in result["blockers"]] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in result["warnings"]] or ["- None"])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--review-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()

    package = inspect_package(args.candidate)
    payload = args.candidate.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    scene, mesh = reopened_mesh(args.candidate)
    bounds = numpy.asarray(mesh.extents, dtype=float)
    face_vertices = numpy.asarray(mesh.vertices)[numpy.asarray(mesh.faces)]
    double_area = numpy.linalg.norm(
        numpy.cross(face_vertices[:, 1] - face_vertices[:, 0], face_vertices[:, 2] - face_vertices[:, 0]), axis=1
    )
    degenerate = int(numpy.count_nonzero(double_area <= 1e-10))
    opening = measure_opening(mesh)
    depth = measure_cavity_depth(mesh)
    wall, wall_sections = measure_functional_wall(mesh)
    base_error = abs(float(mesh.bounds[0, 2]))
    connected = int(mesh.body_count)
    euler = int(mesh.euler_number)

    blockers = []
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
    if abs(opening - 42.0) > 0.2:
        blockers.append(f"opening {opening:.3f} mm is outside 42.0 ± 0.2 mm")
    if abs(depth - 22.0) > 0.2:
        blockers.append(f"cavity depth {depth:.3f} mm is outside 22.0 ± 0.2 mm")
    if wall < 2.4:
        blockers.append(f"functional wall {wall:.3f} mm is below 2.4 mm")
    if base_error > 0.05:
        blockers.append(f"base-plane error {base_error:.4f} mm exceeds 0.05 mm")

    warnings = [
        "PLA temperature risk accepted by user",
        "Anatomical undercuts and dental detail may require slicer supports",
        "Hand wash only; geometry file contains no validated food-contact or dishwasher certification",
    ]
    if euler != 2:
        genus = int((2 - euler) / 2)
        warnings.append(
            f"Intentional anatomical passages yield Euler number {euler} (genus {genus}); accepted because the mesh is one connected watertight manifold"
        )

    result: QaResult = {
        "sha256": digest,
        "short_id": digest[:8].upper(),
        "bounds_mm": [round(float(value), 4) for value in bounds],
        "body_count": len(scene.geometry),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "euler_number": euler,
        "degenerate_face_count": degenerate,
        "connected_component_count": connected,
        "opening_diameter_mm": round(opening, 4),
        "cavity_depth_mm": round(depth, 4),
        "minimum_wall_mm": round(wall, 4),
        "base_plane_error_mm": round(base_error, 6),
        "blockers": blockers,
        "warnings": warnings,
    }

    args.review_dir.mkdir(parents=True, exist_ok=True)
    reopened_path = args.review_dir / "reopened_body.stl"
    reopened_path.write_bytes(mesh.export(file_type="stl"))
    json_path = args.review_dir / "skull_egg_cup_v001_qa.json"
    markdown_path = args.review_dir / "skull_egg_cup_v001_qa.md"
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(format_markdown(result, package, wall_sections), encoding="utf-8")
    print("QA_RESULT=" + json.dumps(result, sort_keys=True))
    if blockers:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
