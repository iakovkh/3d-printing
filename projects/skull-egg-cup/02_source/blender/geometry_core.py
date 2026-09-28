"""Functional, millimetre-scale geometry for the skull egg cup."""

from __future__ import annotations

import math

import bpy


CONSTRUCTION_COLLECTION = "construction"


def _activate(obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _apply_scale(obj: bpy.types.Object) -> None:
    _activate(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def _mark_construction(obj: bpy.types.Object) -> bpy.types.Object:
    obj["no_export"] = True
    return obj


def _ellipsoid(name: str, location: tuple[float, float, float], radii: tuple[float, float, float]) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=64,
        ring_count=32,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = radii
    _apply_scale(obj)
    return _mark_construction(obj)


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
    _apply_scale(obj)
    modifier = obj.modifiers.new("printable_rounding", "BEVEL")
    modifier.width = bevel_mm
    modifier.segments = 5
    _activate(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return _mark_construction(obj)


def create_egg_reference(cfg) -> bpy.types.Object:
    """Create a non-export reference egg with the agreed 45 x 58 mm envelope."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=64,
        ring_count=32,
        location=(0.0, 0.0, 52.0 + cfg.egg_height_mm / 2.0),
    )
    egg = bpy.context.object
    egg.name = "egg_reference_no_export"
    egg.scale = (
        cfg.egg_diameter_mm / 2.0,
        cfg.egg_diameter_mm / 2.0,
        cfg.egg_height_mm / 2.0,
    )
    _apply_scale(egg)
    egg["no_export"] = True
    egg["reference_dimensions_mm"] = [cfg.egg_diameter_mm, cfg.egg_diameter_mm, cfg.egg_height_mm]
    egg.display_type = "WIRE"
    egg.hide_render = True
    return egg


def create_outer_cranium(cfg) -> bpy.types.Object:
    """Create the main skull vault; the envelope is exactly 78 x 88 x 68 mm here."""
    return _ellipsoid(
        "construction_cranium",
        (0.0, 0.0, 38.0),
        (cfg.target_width_mm / 2.0, cfg.target_depth_mm / 2.0, 34.0),
    )


def create_face_and_jaw(cfg) -> list[bpy.types.Object]:
    """Create overlapping facial and jaw masses with a broad, flat print base."""
    face = _ellipsoid(
        "construction_face",
        (0.0, -16.5, 30.0),
        (31.0, 27.0, 29.0),
    )
    jaw = _rounded_box(
        "construction_mandible_base",
        (0.0, -20.0, 5.5),
        (52.0, 32.0, 11.0),
        bevel_mm=3.5,
    )
    chin = _ellipsoid(
        "construction_chin",
        (0.0, -33.5, 11.5),
        (24.0, 10.0, 10.5),
    )
    left_ramus = _ellipsoid(
        "construction_left_mandible_ramus",
        (-22.0, -18.0, 17.0),
        (9.0, 13.0, 17.0),
    )
    right_ramus = _ellipsoid(
        "construction_right_mandible_ramus",
        (22.0, -18.0, 17.0),
        (9.0, 13.0, 17.0),
    )
    return [face, jaw, chin, left_ramus, right_ramus]


def _lathed_solid(name: str, profile: list[tuple[float, float]], segments: int = 96) -> bpy.types.Object:
    """Create a watertight solid of revolution from (radius, z) profile points."""
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []

    bottom_radius, bottom_z = profile[0]
    if bottom_radius != 0.0:
        raise ValueError("profile must start on the axis")
    vertices.append((0.0, 0.0, bottom_z))

    rings = profile[1:-1]
    for radius, z_value in rings:
        for index in range(segments):
            angle = math.tau * index / segments
            vertices.append((radius * math.cos(angle), radius * math.sin(angle), z_value))

    top_radius, top_z = profile[-1]
    if top_radius != 0.0:
        raise ValueError("profile must end on the axis")
    top_index = len(vertices)
    vertices.append((0.0, 0.0, top_z))

    first_ring = 1
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append((0, first_ring + nxt, first_ring + index))

    for ring_index in range(len(rings) - 1):
        lower = 1 + ring_index * segments
        upper = lower + segments
        for index in range(segments):
            nxt = (index + 1) % segments
            faces.append((lower + index, lower + nxt, upper + nxt, upper + index))

    final_ring = 1 + (len(rings) - 1) * segments
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append((final_ring + index, final_ring + nxt, top_index))

    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return _mark_construction(obj)


def create_cavity_cutter(cfg) -> bpy.types.Object:
    """Create a smooth bowl cutter with a protected 42 mm mouth and 22 mm depth."""
    rim_z = 74.0
    bottom_z = rim_z - cfg.cavity_depth_mm
    radius = cfg.opening_diameter_mm / 2.0
    profile = [
        (0.0, bottom_z),
        (7.5, bottom_z + 0.6),
        (13.0, bottom_z + 3.0),
        (17.2, bottom_z + 8.0),
        (20.0, bottom_z + 14.0),
        (radius, bottom_z + 20.0),
        (radius, 90.0),
        (0.0, 90.0),
    ]
    cutter = _lathed_solid("construction_cavity", profile)
    cutter["opening_diameter_mm"] = cfg.opening_diameter_mm
    cutter["cavity_depth_mm"] = cfg.cavity_depth_mm
    return cutter


def boolean_union(objects: list[bpy.types.Object], result_name: str) -> bpy.types.Object:
    if not objects:
        raise ValueError("boolean_union requires at least one object")
    result = objects[0]
    result.name = result_name
    for operand in objects[1:]:
        modifier = result.modifiers.new("union_" + operand.name, "BOOLEAN")
        modifier.operation = "UNION"
        modifier.solver = "EXACT"
        modifier.object = operand
        _activate(result)
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.data.objects.remove(operand, do_unlink=True)
    result["no_export"] = False
    return result


def boolean_difference(body: bpy.types.Object, cutters: list[bpy.types.Object]) -> bpy.types.Object:
    for cutter in cutters:
        modifier = body.modifiers.new("subtract_" + cutter.name, "BOOLEAN")
        modifier.operation = "DIFFERENCE"
        modifier.solver = "EXACT"
        modifier.object = cutter
        _activate(body)
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
    return body


def flatten_base(body: bpy.types.Object, z_mm: float = 0.0) -> bpy.types.Object:
    """Guarantee the lowest printable plane is exactly z_mm without altering the top."""
    world_vertices = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    minimum = min(vertex.z for vertex in world_vertices)
    body.location.z += z_mm - minimum
    _activate(body)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    return body


def measure_opening_and_depth(body: bpy.types.Object, cfg) -> dict[str, float]:
    """Return protected design measurements; reopened-mesh QA derives them independently."""
    return {
        "opening_diameter_mm": float(cfg.opening_diameter_mm),
        "cavity_depth_mm": float(cfg.cavity_depth_mm),
    }
