"""Render proof views from the mesh reopened from candidate 3MF."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import bpy
from mathutils import Vector


VIEWS = {
    "front": (0.0, -185.0, 38.0),
    "back": (0.0, 185.0, 38.0),
    "side": (185.0, 0.0, 38.0),
    "top": (0.0, 0.0, 205.0),
    "isometric": (125.0, -150.0, 118.0),
}


def parse_args():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--qa", type=pathlib.Path, required=True)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    return parser.parse_args(raw)


def point_camera(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def area_light(name, location, energy, size, color):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    point_camera(obj, (0.0, 0.0, 35.0))
    return obj


def main():
    args = parse_args()
    qa = json.loads(args.qa.read_text(encoding="utf-8"))
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
    body.color = (0.58, 0.37, 0.19, 1.0)
    for polygon in body.data.polygons:
        polygon.use_smooth = True

    bone = bpy.data.materials.new("warm_printed_bone")
    bone.use_nodes = True
    principled = bone.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.54, 0.34, 0.17, 1.0)
    principled.inputs["Roughness"].default_value = 0.72
    if "Specular IOR Level" in principled.inputs:
        principled.inputs["Specular IOR Level"].default_value = 0.26
    body.data.materials.append(bone)

    bpy.ops.mesh.primitive_plane_add(size=420.0, location=(0.0, 0.0, -0.18))
    floor = bpy.context.object
    floor.name = "studio_floor"
    floor.color = (0.035, 0.043, 0.052, 1.0)
    floor_material = bpy.data.materials.new("studio_floor_material")
    floor_material.use_nodes = True
    floor_bsdf = floor_material.node_tree.nodes.get("Principled BSDF")
    floor_bsdf.inputs["Base Color"].default_value = (0.035, 0.043, 0.052, 1.0)
    floor_bsdf.inputs["Roughness"].default_value = 0.88
    floor.data.materials.append(floor_material)

    area_light("key", (-95.0, -120.0, 145.0), 1050.0, 85.0, (1.0, 0.82, 0.62))
    area_light("fill", (105.0, -65.0, 92.0), 720.0, 75.0, (0.68, 0.80, 1.0))
    area_light("rim", (0.0, 115.0, 135.0), 900.0, 65.0, (1.0, 0.58, 0.32))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "rim.sl"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.curvature_ridge_factor = 1.7
    scene.display.shading.curvature_valley_factor = 1.3
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.025, 0.032, 0.040)
    scene.render.resolution_x = 720
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.color = (0.012, 0.016, 0.022)

    camera_data = bpy.data.cameras.new("proof_camera")
    camera = bpy.data.objects.new("proof_camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    scene.camera = camera

    for name, location in VIEWS.items():
        camera.location = location
        target = (0.0, 0.0, 37.0)
        point_camera(camera, target)
        camera.data.ortho_scale = 104.0 if name != "isometric" else 112.0
        if name == "top":
            camera.data.ortho_scale = 102.0
        scene.render.filepath = str(output_dir / f"skull_egg_cup_v001_{name}_raw.png")
        bpy.ops.render.render(write_still=True)

    print(f"RENDERED_REOPENED={qa['short_id']} views={','.join(VIEWS)}")


if __name__ == "__main__":
    main()
