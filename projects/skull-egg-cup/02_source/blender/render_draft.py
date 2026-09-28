"""Render internal, explicitly non-approval views from the canonical source."""

from __future__ import annotations

import argparse
import math
import pathlib
import sys

import bpy
from mathutils import Vector


VIEWS = {
    "front": (0.0, -180.0, 39.0),
    "back": (0.0, 180.0, 39.0),
    "side": (180.0, 0.0, 39.0),
    "isometric": (125.0, -150.0, 115.0),
}


def args():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    return parser.parse_args(raw)


def point_camera(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def main():
    parsed = args()
    output_dir = parsed.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    body = bpy.data.objects["skull_egg_cup_body"]
    egg = bpy.data.objects.get("egg_reference_no_export")
    if egg:
        egg.hide_render = True
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj != body:
            obj.hide_render = True

    body.color = (0.72, 0.62, 0.47, 1.0)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "rim.sl"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.curvature_ridge_factor = 1.8
    scene.display.shading.curvature_valley_factor = 1.4
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.035, 0.045, 0.055)
    scene.render.resolution_x = 640
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    camera_data = bpy.data.cameras.new("draft_camera")
    camera = bpy.data.objects.new("draft_camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 104.0
    scene.camera = camera

    for name, location in VIEWS.items():
        camera.location = location
        point_camera(camera, (0.0, 0.0, 37.0))
        if name == "isometric":
            camera.data.ortho_scale = 112.0
        else:
            camera.data.ortho_scale = 104.0
        scene.render.filepath = str(output_dir / f"skull_egg_cup_v001_{name}_raw.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
