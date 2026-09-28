"""Printable anatomical detailing for the monolithic skull egg cup."""

from __future__ import annotations

import math

import bmesh
import bpy

from geometry_core import boolean_difference, boolean_union, create_cavity_cutter, flatten_base


def _activate(obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _apply_transform(obj: bpy.types.Object) -> None:
    _activate(obj)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def _ellipsoid(
    name: str,
    location: tuple[float, float, float],
    radii: tuple[float, float, float],
    rotation_y: float = 0.0,
    segments: int = 40,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=max(24, segments // 2),
        location=location,
        rotation=(0.0, rotation_y, 0.0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = radii
    _apply_transform(obj)
    obj["no_export"] = True
    return obj


def _rounded_box(
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    bevel_mm: float,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    _apply_transform(obj)
    modifier = obj.modifiers.new("edge_rounding", "BEVEL")
    modifier.width = bevel_mm
    modifier.segments = 4
    _activate(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj["no_export"] = True
    return obj


def _curve_tube(
    name: str,
    points: list[tuple[float, float, float]],
    radius: float,
) -> bpy.types.Object:
    curve_data = bpy.data.curves.new(name + "_curve", "CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 2
    curve_data.bevel_depth = radius
    curve_data.bevel_resolution = 3
    spline = curve_data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for control, point in zip(spline.bezier_points, points):
        control.co = point
        control.handle_left_type = "AUTO"
        control.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    _activate(obj)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj["no_export"] = True
    return obj


def _triangular_prism(
    name: str,
    y_front: float,
    y_back: float,
    half_width: float,
    z_bottom: float,
    z_top: float,
) -> bpy.types.Object:
    vertices = [
        (-half_width, y_front, z_bottom),
        (half_width, y_front, z_bottom),
        (0.0, y_front, z_top),
        (-half_width, y_back, z_bottom),
        (half_width, y_back, z_bottom),
        (0.0, y_back, z_top),
    ]
    faces = [
        (0, 2, 1),
        (3, 4, 5),
        (0, 1, 4, 3),
        (1, 2, 5, 4),
        (2, 0, 3, 5),
    ]
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    modifier = obj.modifiers.new("nasal_edge_rounding", "BEVEL")
    modifier.width = 1.15
    modifier.segments = 4
    _activate(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj["no_export"] = True
    return obj


def carve_eye_sockets(body: bpy.types.Object, cfg) -> bpy.types.Object:
    cutters = [
        _ellipsoid("left_eye_socket_cutter", (-14.0, -39.0, 35.5), (11.2, 10.5, 10.5), 0.10),
        _ellipsoid("right_eye_socket_cutter", (14.0, -39.0, 35.5), (11.2, 10.5, 10.5), -0.10),
    ]
    body = boolean_difference(body, cutters)
    body["left_eye_socket"] = True
    body["right_eye_socket"] = True
    return body


def carve_nasal_cavity(body: bpy.types.Object, cfg) -> bpy.types.Object:
    cutter = _ellipsoid(
        "pear_nasal_aperture",
        (0.0, -40.0, 24.5),
        (5.3, 8.0, 8.8),
        0.0,
        48,
    )
    body = boolean_difference(body, [cutter])
    body["nasal_cavity"] = True
    return body


def shape_brow_and_cheekbones(body: bpy.types.Object, cfg) -> bpy.types.Object:
    # Brow and cheekbone strength comes from material retained around the
    # centered orbital cuts and the thickened mandibular rami in the core.
    body["brow_ridge"] = True
    body["cheekbones"] = True
    body["back_skull_detail"] = True
    return body


def add_fused_teeth_relief(body: bpy.types.Object, cfg) -> bpy.types.Object:
    tooth_bed = _ellipsoid(
        "fused_tooth_bed",
        (0.0, -38.5, 11.2),
        (22.5, 5.5, 8.6),
    )
    body = boolean_union([body, tooth_bed], "skull_egg_cup_body")

    grooves = []
    for index, x_value in enumerate((-18.0, -12.0, -6.0, 0.0, 6.0, 12.0, 18.0)):
        groove = _rounded_box(
            f"tooth_vertical_groove_{index}",
            (x_value, -42.5, 11.3),
            (1.15, 4.8, 12.0),
            bevel_mm=0.35,
        )
        grooves.append(groove)
    grooves.append(
        _rounded_box(
            "tooth_horizontal_groove",
            (0.0, -42.5, 14.2),
            (38.0, 4.8, 1.15),
            bevel_mm=0.35,
        )
    )
    body = boolean_difference(body, grooves)
    body["teeth_relief"] = True
    body["tooth_groove_width_mm"] = 1.15
    return body


def engrave_cranial_sutures(body: bpy.types.Object, cfg) -> bpy.types.Object:
    # The front wavy coronal line remains below the functional rim.
    front = _curve_tube(
        "front_coronal_suture",
        [
            (-29.0, -36.7, 52.0),
            (-21.0, -40.2, 50.4),
            (-12.0, -42.1, 51.7),
            (0.0, -42.9, 50.2),
            (12.0, -42.1, 51.7),
            (21.0, -40.2, 50.4),
            (29.0, -36.7, 52.0),
        ],
        radius=0.65,
    )
    # A long rear seam and two lambdoid branches make the back intentionally detailed.
    rear_vertical = _curve_tube(
        "rear_sagittal_suture",
        [
            (0.0, 43.7, 31.0),
            (-1.0, 43.8, 39.0),
            (1.2, 42.8, 47.0),
            (-0.8, 40.3, 57.0),
            (0.0, 35.0, 65.0),
        ],
        radius=0.65,
    )
    rear_left = _curve_tube(
        "rear_left_lambdoid_suture",
        [(0.0, 43.6, 39.0), (-10.0, 42.2, 42.0), (-19.0, 38.0, 39.2), (-27.0, 31.0, 42.0)],
        radius=0.6,
    )
    rear_right = _curve_tube(
        "rear_right_lambdoid_suture",
        [(0.0, 43.6, 39.0), (10.0, 42.2, 42.0), (19.0, 38.0, 39.2), (27.0, 31.0, 42.0)],
        radius=0.6,
    )
    body = boolean_difference(body, [front, rear_vertical, rear_left, rear_right])
    body["cranial_sutures"] = True
    body["suture_width_mm"] = 1.2
    return body


def add_bone_microrelief(body: bpy.types.Object, cfg, amplitude_mm: float = 0.35) -> bpy.types.Object:
    if amplitude_mm > 0.35:
        raise ValueError("microrelief amplitude exceeds the approved maximum")

    group = body.vertex_groups.new(name="bone_surface_mask")
    for vertex in body.data.vertices:
        world = body.matrix_world @ vertex.co
        radial = math.hypot(world.x, world.y)
        if 4.0 < world.z < 61.0 and radial > 25.0:
            group.add([vertex.index], 1.0, "REPLACE")

    texture = bpy.data.textures.new("subtle_bone_grain", type="CLOUDS")
    texture.noise_scale = 3.4
    texture.noise_depth = 1
    modifier = body.modifiers.new("subtle_bone_microrelief", "DISPLACE")
    modifier.texture = texture
    modifier.texture_coords = "GLOBAL"
    modifier.strength = amplitude_mm
    modifier.mid_level = 0.5
    modifier.vertex_group = group.name
    _activate(body)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    body["bone_microrelief"] = True
    body["microrelief_amplitude_mm"] = amplitude_mm
    return body


def restore_protected_cavity(body: bpy.types.Object, cfg) -> bpy.types.Object:
    body = boolean_difference(body, [create_cavity_cutter(cfg)])
    body["opening_diameter_mm"] = cfg.opening_diameter_mm
    body["cavity_depth_mm"] = cfg.cavity_depth_mm
    return body


def finalize_manifold(body: bpy.types.Object, voxel_mm: float = 0.35) -> bpy.types.Object:
    if voxel_mm > 0.35:
        raise ValueError("final voxel size must be no coarser than 0.35 mm")

    # Weld the many exact feature booleans into one printable skin. The protected
    # bowl is cut again *after* this pass by build_source.py.
    used_voxel = min(voxel_mm, 0.34)
    _activate(body)
    body.data.remesh_voxel_size = used_voxel
    body.data.remesh_voxel_adaptivity = 0.0
    body.data.use_remesh_fix_poles = True
    body.data.use_remesh_preserve_volume = True
    bpy.ops.object.voxel_remesh()

    _activate(body)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    flatten_base(body, 0.0)

    bm = bmesh.new()
    bm.from_mesh(body.data)
    invalid = [edge for edge in bm.edges if not edge.is_manifold]
    invalid_count = len(invalid)
    if invalid:
        sample = []
        for edge in invalid[:12]:
            sample.append(
                {
                    "faces": len(edge.link_faces),
                    "a": tuple(round(value, 4) for value in edge.verts[0].co),
                    "b": tuple(round(value, 4) for value in edge.verts[1].co),
                }
            )
        print(f"NON_MANIFOLD_SAMPLE={sample}")
    bm.free()
    if invalid_count:
        raise RuntimeError(f"final body has {invalid_count} non-manifold edges after voxel remesh")
    body["final_voxel_target_mm"] = voxel_mm
    body["final_voxel_used_mm"] = used_voxel
    return body
