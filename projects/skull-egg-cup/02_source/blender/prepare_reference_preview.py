"""Import and normalize the CC BY anatomical skull for visual assessment."""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import bpy
from mathutils import Vector


def parse_args():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args(raw)


def world_bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maximum = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return minimum, maximum


def main():
    args = parse_args()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.wm.stl_import(filepath=str(args.input.resolve()))
    meshes = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("reference STL imported no meshes")
    bpy.context.view_layer.objects.active = meshes[0]
    for obj in meshes:
        obj.select_set(True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    body = bpy.context.object
    body.name = "skull_egg_cup_body"

    # Medical scan axes: X left/right, Y superior/inferior, Z anterior/posterior.
    # Project axes: X left/right, Y back/front, Z up. Positive old Z becomes
    # negative project Y so the face is seen from the standard front camera.
    body.rotation_euler.x = math.radians(90.0)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    minimum, maximum = world_bounds(body)
    extents = maximum - minimum
    body.scale.x *= 78.0 / extents.x
    body.scale.y *= 88.0 / extents.y
    body.scale.z *= 74.0 / extents.z
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    minimum, maximum = world_bounds(body)
    body.location -= Vector(((minimum.x + maximum.x) / 2.0, (minimum.y + maximum.y) / 2.0, minimum.z))
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    for polygon in body.data.polygons:
        polygon.use_smooth = True
    body.color = (0.72, 0.62, 0.47, 1.0)
    body["reference_only"] = True
    body["source_license"] = "CC BY 4.0"
    body["source_sha256"] = "d44fe197ce4724d6fdf9729701c723efb79ccf14a1ccb3ad37475fbfe1b5066d"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print(
        "REFERENCE_PREVIEW="
        + json.dumps(
            {
                "objects": len(meshes),
                "vertices": len(body.data.vertices),
                "faces": len(body.data.polygons),
                "bounds_mm": [round(float(value), 4) for value in body.dimensions],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
