"""Render proof views only from the mesh reopened from candidate 3MF."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

import bpy
from mathutils import Vector


VIEWS = {
    "front": ((0.0, -100.0, 25.0), (0.0, 0.0, 25.0), 61.0),
    "back": ((0.0, 100.0, 25.0), (0.0, 0.0, 25.0), 61.0),
    "side": ((100.0, 0.0, 25.0), (0.0, 0.0, 25.0), 61.0),
    "top": ((0.0, 0.0, 110.0), (0.0, 0.0, 24.0), 34.0),
    "isometric": ((72.0, -82.0, 66.0), (0.0, 0.0, 25.0), 66.0),
    "detail": ((55.0, -12.0, 48.0), (0.0, 0.0, 44.2), 19.0),
}


def parse_args():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--qa", type=pathlib.Path, required=True)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    return parser.parse_args(raw)


def version_from_qa(path: pathlib.Path) -> str:
    match = re.search(r"_(v\d{3})_qa$", path.stem)
    if match is None:
        raise ValueError(f"QA filename is not versioned: {path.name}")
    return match.group(1)


def point_camera(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def main():
    args = parse_args()
    qa = json.loads(args.qa.read_text(encoding="utf-8"))
    version = version_from_qa(args.qa)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.wm.stl_import(filepath=str(args.mesh.resolve()))
    meshes = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"expected one reopened mesh, got {len(meshes)}")
    body = meshes[0]
    body.name = "reopened_candidate_body"
    body.color = (0.008, 0.010, 0.014, 1.0)
    for polygon in body.data.polygons:
        polygon.use_smooth = True

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.curvature_ridge_factor = 1.45
    scene.display.shading.curvature_valley_factor = 1.25
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.72, 0.75, 0.79)
    scene.display.shading.show_specular_highlight = True
    scene.render.resolution_x = 720
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"

    camera_data = bpy.data.cameras.new("proof_camera")
    camera = bpy.data.objects.new("proof_camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    scene.camera = camera

    for name, (location, target, ortho_scale) in VIEWS.items():
        camera.location = location
        point_camera(camera, target)
        camera.data.ortho_scale = ortho_scale
        scene.render.filepath = str(
            output_dir / f"staunton_queen_keychain_{version}_{name}_raw.png"
        )
        bpy.ops.render.render(write_still=True)

    print(f"RENDERED_REOPENED={qa['short_id']} views={','.join(VIEWS)}")


if __name__ == "__main__":
    main()

