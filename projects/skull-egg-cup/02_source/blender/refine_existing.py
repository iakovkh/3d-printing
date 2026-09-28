"""Apply controlled local sculpt corrections to a validated checkpoint mesh."""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import bmesh
import bpy


def parse_args():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args(raw)


def soften_applied_pads(body):
    moved = 0
    for vertex in body.data.vertices:
        point = vertex.co

        # Flatten only the foremost part of each former brow pad. Socket rims
        # and all inner surfaces remain untouched.
        for x_center in (-14.0, 14.0):
            metric = ((point.x - x_center) / 14.0) ** 2 + ((point.z - 47.0) / 5.0) ** 2
            if metric < 1.0 and point.y < -39.2:
                weight = (1.0 - metric) ** 2
                point.y += min((-39.2 - point.y) * weight, 3.0 * weight)
                moved += 1

        # Sink the visually separate cheek ovals into the zygomatic bridge.
        for x_center in (-27.0, 27.0):
            metric = ((point.x - x_center) / 9.0) ** 2 + ((point.z - 28.5) / 11.0) ** 2
            if metric < 1.0 and point.y < -32.0:
                weight = (1.0 - metric) ** 2
                point.y += min((-32.0 - point.y) * weight, 5.5 * weight)
                moved += 1

        # Reduce the two rear oval ridges while retaining shallow occipital relief.
        for x_center in (-13.0, 13.0):
            metric = ((point.x - x_center) / 15.0) ** 2 + ((point.z - 35.0) / 5.5) ** 2
            if metric < 1.0 and point.y > 42.0:
                weight = (1.0 - metric) ** 2
                point.y -= min((point.y - 42.0) * weight, 2.2 * weight)
                moved += 1

    body.data.update()
    return moved


def add_nasal_aperture(body):
    moved = 0
    for vertex in body.data.vertices:
        point = vertex.co
        metric = (point.x / 6.2) ** 2 + ((point.z - 25.0) / 9.2) ** 2
        if metric < 1.0 and point.y < -32.0:
            weight = (1.0 - metric) ** 2
            point.y += 5.5 * weight
            moved += 1
    body.data.update()
    body["nasal_cavity"] = True
    body["nasal_recess_depth_mm"] = 5.5
    return moved


def validate_topology(body):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    boundary = len([edge for edge in bm.edges if edge.is_boundary])
    non_manifold = len([edge for edge in bm.edges if not edge.is_manifold])
    vertices = len(bm.verts)
    faces = len(bm.faces)
    bm.free()
    if boundary or non_manifold:
        raise RuntimeError(
            f"refinement damaged topology: boundary={boundary}, non_manifold={non_manifold}"
        )
    return {"vertices": vertices, "faces": faces, "boundary_edges": boundary, "non_manifold_edges": non_manifold}


def main():
    args = parse_args()
    body = bpy.data.objects["skull_egg_cup_body"]
    moved = soften_applied_pads(body)
    nasal_vertices = add_nasal_aperture(body)
    for polygon in body.data.polygons:
        polygon.use_smooth = True
    body["local_sculpt_refinement"] = True
    report = validate_topology(body)
    report["moved_vertices"] = moved
    report["nasal_vertices"] = nasal_vertices
    report["bounds_mm"] = [round(float(value), 4) for value in body.dimensions]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print("REFINEMENT=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
