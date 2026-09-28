"""Render technical proof views exclusively from meshes reopened from candidate 3MF."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import bpy
from mathutils import Vector


REQUIRED_VIEWS = {
    "front": Vector((0.0, -1.0, 0.0)),
    "back": Vector((0.0, 1.0, 0.0)),
    "side": Vector((1.0, 0.0, 0.0)),
    "top": Vector((0.0, 0.0, 1.0)),
    "isometric": Vector((1.0, -1.0, 0.8)),
}


def parse_args():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    return parser.parse_args(raw)


def rgba(hex_color: str):
    value = hex_color.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"invalid RGB color: {hex_color}")
    return tuple(int(value[index : index + 2], 16) / 255.0 for index in (0, 2, 4)) + (1.0,)


def point_camera(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def scene_bounds(objects):
    corners = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    minimum = Vector(tuple(min(point[axis] for point in corners) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in corners) for axis in range(3)))
    return minimum, maximum


def main():
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    model = manifest["model"]
    version = manifest["version"]
    bodies = manifest["bodies"]
    if not bodies:
        raise ValueError("render manifest contains no reopened bodies")

    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite raw previews: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    imported = []
    for body in bodies:
        path = pathlib.Path(body["path"]).resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        bpy.ops.wm.stl_import(filepath=str(path))
        selected = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
        if len(selected) != 1:
            raise RuntimeError(f"expected one mesh in {path.name}, got {len(selected)}")
        obj = selected[0]
        obj.name = body["name"]
        obj.color = rgba(body["color"])
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        imported.append(obj)

    minimum, maximum = scene_bounds(imported)
    center = (minimum + maximum) * 0.5
    extents = maximum - minimum
    span = max(max(extents), 1.0)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.72, 0.75, 0.79)
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
    camera.data.clip_start = 0.01
    camera.data.clip_end = span * 20.0 + 100.0
    scene.camera = camera

    for name, direction in REQUIRED_VIEWS.items():
        unit_direction = direction.normalized()
        camera.location = center + unit_direction * (span * 4.0 + 10.0)
        point_camera(camera, center)
        camera.data.ortho_scale = span * (1.55 if name == "isometric" else 1.35)
        scene.render.filepath = str(output_dir / f"{model}_{version}_{name}_raw.png")
        bpy.ops.render.render(write_still=True)

    print(
        f"RENDERED_REOPENED={manifest.get('short_id', 'unknown')} "
        f"views={','.join(REQUIRED_VIEWS)}"
    )


if __name__ == "__main__":
    main()
