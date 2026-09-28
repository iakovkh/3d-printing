"""Export exactly one named body from the canonical Blender source."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import bpy


def parse_args():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args(raw)


def main():
    args = parse_args()
    body = bpy.data.objects.get("skull_egg_cup_body")
    if body is None or body.type != "MESH":
        raise RuntimeError("canonical source is missing skull_egg_cup_body mesh")
    exportable = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and not bool(obj.get("no_export")) and not obj.hide_get()
    ]
    if exportable != [body]:
        raise RuntimeError(f"expected one visible export body, found {[obj.name for obj in exportable]}")

    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    modifier = body.modifiers.new("export_triangulation", "TRIANGULATE")
    bpy.ops.object.modifier_apply(modifier=modifier.name)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.stl_export(
        filepath=str(args.output.resolve()),
        export_selected_objects=True,
        apply_modifiers=True,
        global_scale=1.0,
    )
    print(
        "STL_EXPORT="
        + json.dumps(
            {
                "path": str(args.output.resolve()),
                "bounds_mm": [round(float(value), 4) for value in body.dimensions],
                "triangles": len(body.data.polygons),
                "body_count": 1,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
