"""Build the functional or final Blender source for the skull egg cup."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import bpy


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from geometry_core import (  # noqa: E402
    boolean_difference,
    boolean_union,
    create_cavity_cutter,
    create_egg_reference,
    create_face_and_jaw,
    create_outer_cranium,
    flatten_base,
    measure_opening_and_depth,
)
from model_config import CONFIG  # noqa: E402


def add_final_features(body):
    from skull_features import (
        add_bone_microrelief,
        add_fused_teeth_relief,
        carve_eye_sockets,
        carve_nasal_cavity,
        engrave_cranial_sutures,
        finalize_manifold,
        restore_protected_cavity,
        shape_brow_and_cheekbones,
    )

    body = carve_eye_sockets(body, CONFIG)
    body = carve_nasal_cavity(body, CONFIG)
    body = shape_brow_and_cheekbones(body, CONFIG)
    body = add_fused_teeth_relief(body, CONFIG)
    body = engrave_cranial_sutures(body, CONFIG)
    body = add_bone_microrelief(body, CONFIG, amplitude_mm=0.30)
    body = finalize_manifold(body, voxel_mm=0.35)
    body = restore_protected_cavity(body, CONFIG)
    return body


def parse_args() -> argparse.Namespace:
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("core", "final"), default="core")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args(arguments)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)


def build_core():
    cfg = CONFIG
    cranium = create_outer_cranium(cfg)
    face_parts = create_face_and_jaw(cfg)

    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=26.0, depth=7.0, location=(0.0, 0.0, 70.5))
    rim = bpy.context.object
    rim.name = "construction_rim"
    rim["no_export"] = True
    rim_bevel = rim.modifiers.new("organic_rim_rounding", "BEVEL")
    rim_bevel.width = 1.4
    rim_bevel.segments = 5
    bpy.context.view_layer.objects.active = rim
    rim.select_set(True)
    bpy.ops.object.modifier_apply(modifier=rim_bevel.name)

    body = boolean_union([cranium, *face_parts, rim], "skull_egg_cup_body")
    body = boolean_difference(body, [create_cavity_cutter(cfg)])
    body = flatten_base(body, 0.0)
    body.name = "skull_egg_cup_body"
    body["no_export"] = False
    body["opening_diameter_mm"] = cfg.opening_diameter_mm
    body["cavity_depth_mm"] = cfg.cavity_depth_mm
    body["minimum_wall_mm"] = cfg.min_wall_mm

    for polygon in body.data.polygons:
        polygon.use_smooth = True

    egg = create_egg_reference(cfg)
    egg.hide_set(True)
    return body


def main() -> None:
    args = parse_args()
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 0.001

    body = build_core()
    if args.stage == "final":
        body = add_final_features(body)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))

    measurements = measure_opening_and_depth(body, CONFIG)
    report = {
        "bounds_mm": [round(float(value), 4) for value in body.dimensions],
        **measurements,
        "body_count": len(
            [obj for obj in bpy.data.objects if obj.type == "MESH" and not bool(obj.get("no_export"))]
        ),
    }
    print("CORE_BUILD=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
