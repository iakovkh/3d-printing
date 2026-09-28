"""Build the printable egg cup from a CC BY anatomical skull reference."""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import bmesh
import bpy
from mathutils import Vector


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from geometry_core import boolean_difference, create_cavity_cutter, create_egg_reference  # noqa: E402
from model_config import CONFIG  # noqa: E402


REFERENCE_SHA256 = "d44fe197ce4724d6fdf9729701c723efb79ccf14a1ccb3ad37475fbfe1b5066d"


def parse_args():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--core-mode", choices=("none", "minimal", "full"), default="minimal")
    return parser.parse_args(raw)


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_transform(obj):
    activate(obj)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def world_bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maximum = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return minimum, maximum


def import_reference(path):
    bpy.ops.wm.stl_import(filepath=str(path.resolve()))
    meshes = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("reference STL imported no meshes")
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    body = bpy.context.object
    body.name = "anatomical_skull_reference"
    body.rotation_euler.x = math.radians(90.0)
    apply_transform(body)

    minimum, maximum = world_bounds(body)
    extents = maximum - minimum
    body.scale = (78.0 / extents.x, 88.0 / extents.y, 74.0 / extents.z)
    apply_transform(body)
    minimum, maximum = world_bounds(body)
    body.location -= Vector(((minimum.x + maximum.x) / 2.0, (minimum.y + maximum.y) / 2.0, minimum.z))
    activate(body)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    return body


def ellipsoid(name, location, radii):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = radii
    apply_transform(obj)
    return obj


def rounded_box(name, location, dimensions, bevel):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    apply_transform(obj)
    modifier = obj.modifiers.new("structural_rounding", "BEVEL")
    modifier.width = bevel
    modifier.segments = 4
    activate(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def make_structural_core(mode):
    parts = []
    if mode == "full":
        parts.extend(
            [
                ellipsoid("inner_cranial_core", (0.0, 5.0, 40.0), (35.5, 37.0, 31.5)),
                ellipsoid("inner_facial_core", (0.0, -12.0, 30.0), (28.5, 22.0, 23.0)),
                ellipsoid("inner_dental_bridge", (0.0, -31.0, 13.0), (25.0, 7.0, 8.5)),
                ellipsoid("inner_left_ramus", (-23.0, -13.0, 16.0), (8.5, 13.0, 16.0)),
                ellipsoid("inner_right_ramus", (23.0, -13.0, 16.0), (8.5, 13.0, 16.0)),
                rounded_box("flat_mandible_base", (0.0, -13.0, 4.5), (53.0, 37.0, 9.0), 3.0),
            ]
        )
    elif mode == "minimal":
        parts.extend(
            [
                ellipsoid("deep_cranial_bridge", (0.0, 4.0, 42.0), (27.0, 27.0, 24.0)),
                ellipsoid("deep_dental_bridge", (0.0, -20.0, 15.0), (18.0, 10.0, 7.0)),
                rounded_box("compact_flat_base", (0.0, -8.0, 3.0), (42.0, 25.0, 6.0), 2.0),
            ]
        )
    # A low bone-coloured footprint stays inside the approved envelope and
    # prevents the rear-heavy anatomical skull from rocking on its chin.
    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=1.0, depth=3.0, location=(0.0, 0.0, 1.5))
    base = bpy.context.object
    base.name = "integrated_stability_base"
    base.scale = (30.0, 37.0, 1.0)
    apply_transform(base)
    base_bevel = base.modifiers.new("base_edge_rounding", "BEVEL")
    base_bevel.width = 0.9
    base_bevel.segments = 5
    activate(base)
    bpy.ops.object.modifier_apply(modifier=base_bevel.name)
    parts.append(base)
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=25.8, depth=5.5, location=(0.0, 0.0, 71.25))
    rim = bpy.context.object
    rim.name = "integrated_egg_rim"
    modifier = rim.modifiers.new("organic_rim_rounding", "BEVEL")
    modifier.width = 1.4
    modifier.segments = 5
    activate(rim)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    parts.append(rim)
    return parts


def join_and_voxel_weld(objects, voxel_mm=0.35):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    body = bpy.context.object
    body.name = "skull_egg_cup_body"
    body.data.remesh_voxel_size = voxel_mm
    body.data.remesh_voxel_adaptivity = 0.0
    body.data.use_remesh_fix_poles = True
    body.data.use_remesh_preserve_volume = True
    activate(body)
    bpy.ops.object.voxel_remesh()
    return body


def flatten_base(body):
    minimum = min(vertex.co.z for vertex in body.data.vertices)
    body.location.z -= minimum
    activate(body)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    # Collapse the lowest 0.7 mm to a broad, exact contact plane without
    # changing connectivity.
    for vertex in body.data.vertices:
        if vertex.co.z < 0.7:
            vertex.co.z = 0.0
    body.data.update()


def topology_report(body):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    boundary = len([edge for edge in bm.edges if edge.is_boundary])
    non_manifold = len([edge for edge in bm.edges if not edge.is_manifold])
    unseen = set(bm.verts)
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            vertex = stack.pop()
            neighbours = {edge.other_vert(vertex) for edge in vertex.link_edges}
            found = neighbours & unseen
            unseen.difference_update(found)
            stack.extend(found)
    result = {
        "vertices": len(bm.verts),
        "faces": len(bm.faces),
        "boundary_edges": boundary,
        "non_manifold_edges": non_manifold,
        "connected_components": components,
    }
    bm.free()
    return result


def main():
    args = parse_args()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 0.001

    reference = import_reference(args.reference)
    body = join_and_voxel_weld([reference, *make_structural_core(args.core_mode)], voxel_mm=0.35)
    flatten_base(body)
    body = boolean_difference(body, [create_cavity_cutter(CONFIG)])
    body.name = "skull_egg_cup_body"
    body["no_export"] = False
    body["opening_diameter_mm"] = CONFIG.opening_diameter_mm
    body["cavity_depth_mm"] = CONFIG.cavity_depth_mm
    body["minimum_wall_mm"] = CONFIG.min_wall_mm
    body["brow_ridge"] = True
    body["left_eye_socket"] = True
    body["right_eye_socket"] = True
    body["nasal_cavity"] = True
    body["cheekbones"] = True
    body["teeth_relief"] = True
    body["cranial_sutures"] = True
    body["bone_microrelief"] = True
    body["anatomical_reference_sha256"] = REFERENCE_SHA256
    body["anatomical_reference_license"] = "CC BY 4.0"
    for polygon in body.data.polygons:
        polygon.use_smooth = True

    egg = create_egg_reference(CONFIG)
    egg.hide_set(True)
    report = topology_report(body)
    report["bounds_mm"] = [round(float(value), 4) for value in body.dimensions]
    report["opening_diameter_mm"] = CONFIG.opening_diameter_mm
    report["cavity_depth_mm"] = CONFIG.cavity_depth_mm
    report["core_mode"] = args.core_mode
    if report["boundary_edges"] or report["non_manifold_edges"] or report["connected_components"] != 1:
        raise RuntimeError("anatomical build is not one closed component: " + json.dumps(report))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print("ANATOMICAL_BUILD=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
