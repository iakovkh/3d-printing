"""Procedural Blender geometry for the Staunton queen keychain."""

from __future__ import annotations

import math

import bmesh
import bpy
from mathutils import Vector

from model_config import ModelConfig


RADIAL_SEGMENTS = 192


def _mesh_object(name: str, vertices, faces) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def _lathe(name: str, profile, segments: int = RADIAL_SEGMENTS) -> bpy.types.Object:
    vertices = []
    for z, radius in profile:
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            vertices.append((radius * math.cos(angle), radius * math.sin(angle), z))

    faces = []
    ring_count = len(profile)
    for ring in range(ring_count - 1):
        start = ring * segments
        next_start = (ring + 1) * segments
        for index in range(segments):
            nxt = (index + 1) % segments
            faces.append((start + index, start + nxt, next_start + nxt, next_start + index))

    bottom_center = len(vertices)
    vertices.append((0.0, 0.0, profile[0][0]))
    top_center = len(vertices)
    vertices.append((0.0, 0.0, profile[-1][0]))
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append((bottom_center, index, nxt))
        top_start = (ring_count - 1) * segments
        faces.append((top_center, top_start + nxt, top_start + index))
    return _mesh_object(name, vertices, faces)


def create_lathed_body(cfg: ModelConfig) -> bpy.types.Object:
    return _lathe("queen_lathed_body", cfg.lathe_profile)


def _create_crown_ring(cfg: ModelConfig) -> bpy.types.Object:
    segments = RADIAL_SEGMENTS
    rings = []
    for index in range(segments):
        angle = 2.0 * math.pi * index / segments
        peak = ((1.0 + math.cos(cfg.crown_teeth * angle)) * 0.5) ** 3
        rings.append(
            (
                (5.15, 35.10),
                (6.35, 37.70),
                (6.00 + 0.55 * peak, 39.85 + 3.25 * peak),
                (3.80 + 0.20 * peak, 39.25 + 2.10 * peak),
                (3.45, 35.70),
            )
        )

    vertices = []
    ring_total = 5
    for ring_index in range(ring_total):
        for index in range(segments):
            radius, z = rings[index][ring_index]
            angle = 2.0 * math.pi * index / segments
            vertices.append((radius * math.cos(angle), radius * math.sin(angle), z))

    faces = []
    for ring_index in range(ring_total - 1):
        current = ring_index * segments
        following = (ring_index + 1) * segments
        for index in range(segments):
            nxt = (index + 1) % segments
            faces.append((current + index, current + nxt, following + nxt, following + index))

    outer_bottom = 0
    inner_bottom = (ring_total - 1) * segments
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append((outer_bottom + nxt, outer_bottom + index, inner_bottom + index, inner_bottom + nxt))
    return _mesh_object("queen_crown_ring", vertices, faces)


def create_crown(cfg: ModelConfig) -> list[bpy.types.Object]:
    ring = _create_crown_ring(cfg)
    dome_profile = (
        (34.90, 4.55),
        (36.40, 4.90),
        (38.30, 4.55),
        (40.20, 3.35),
        (41.70, 2.25),
        (42.45, 1.65),
    )
    dome = _lathe("queen_crown_dome", dome_profile)
    return [ring, dome]


def create_finial(cfg: ModelConfig) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=96,
        ring_count=48,
        radius=cfg.finial_diameter_mm / 2.0,
        location=(0.0, 0.0, cfg.finial_center_z_mm),
    )
    sphere = bpy.context.active_object
    sphere.name = "queen_finial"
    return sphere


def _construction_collection() -> bpy.types.Collection:
    collection = bpy.data.collections.get("construction")
    if collection is None:
        collection = bpy.data.collections.new("construction")
        bpy.context.scene.collection.children.link(collection)
    return collection


def _archive_copy(obj: bpy.types.Object, suffix: str) -> None:
    archived = obj.copy()
    archived.data = obj.data.copy()
    archived.name = f"{obj.name}_{suffix}"
    _construction_collection().objects.link(archived)
    archived["no_export"] = True
    archived.hide_set(True)
    archived.hide_render = True


def join_and_remesh(parts: list[bpy.types.Object], cfg: ModelConfig) -> bpy.types.Object:
    for part in parts:
        _archive_copy(part, "construction")
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.hide_set(False)
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    body = bpy.context.active_object
    body.name = "queen_outer_union"
    modifier = body.modifiers.new("outer_voxel_union", "REMESH")
    modifier.mode = "VOXEL"
    modifier.voxel_size = cfg.remesh_voxel_mm
    modifier.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return body


def _world_bounds(obj: bpy.types.Object):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maximum = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return minimum, maximum


def normalize_outer_dimensions(body: bpy.types.Object, cfg: ModelConfig) -> bpy.types.Object:
    minimum, maximum = _world_bounds(body)
    size = maximum - minimum
    xy_scale = cfg.base_diameter_mm / max(size.x, size.y)
    z_scale = cfg.height_mm / size.z
    body.scale.x *= xy_scale
    body.scale.y *= xy_scale
    body.scale.z *= z_scale
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    minimum, _ = _world_bounds(body)
    body.location.z -= minimum.z
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    return body


def _make_hole_cutter(cfg: ModelConfig) -> bpy.types.Object:
    segments = 128
    bore_radius = cfg.hole_diameter_mm / 2.0 + 0.02
    outer_radius = bore_radius + cfg.hole_chamfer_mm
    profile = (
        (-6.0, outer_radius),
        (-4.20, outer_radius),
        (-3.45, bore_radius),
        (3.45, bore_radius),
        (4.20, outer_radius),
        (6.0, outer_radius),
    )
    vertices = []
    for x_value, radius in profile:
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            vertices.append(
                (
                    x_value,
                    radius * math.cos(angle),
                    cfg.finial_center_z_mm + radius * math.sin(angle),
                )
            )
    faces = []
    for ring in range(len(profile) - 1):
        start = ring * segments
        following = (ring + 1) * segments
        for index in range(segments):
            nxt = (index + 1) % segments
            faces.append((start + index, start + nxt, following + nxt, following + index))
    left_center = len(vertices)
    vertices.append((profile[0][0], 0.0, cfg.finial_center_z_mm))
    right_center = len(vertices)
    vertices.append((profile[-1][0], 0.0, cfg.finial_center_z_mm))
    right_start = (len(profile) - 1) * segments
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append((left_center, nxt, index))
        faces.append((right_center, right_start + index, right_start + nxt))
    return _mesh_object("ring_hole_cutter", vertices, faces)


def cut_ring_hole(body: bpy.types.Object, cfg: ModelConfig) -> bpy.types.Object:
    cutter = _make_hole_cutter(cfg)
    modifier = body.modifiers.new("ring_hole_difference", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)

    repair = body.modifiers.new("ring_hole_manifold_repair", "REMESH")
    repair.mode = "VOXEL"
    repair.voxel_size = cfg.repair_voxel_mm
    repair.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=repair.name)
    cutter["no_export"] = True
    for collection in list(cutter.users_collection):
        collection.objects.unlink(cutter)
    _construction_collection().objects.link(cutter)
    cutter.hide_set(True)
    cutter.hide_render = True
    return body


def flatten_base(body: bpy.types.Object, cfg: ModelConfig) -> bpy.types.Object:
    mesh = body.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    minimum_z = min(vertex.co.z for vertex in bm.verts)
    for vertex in bm.verts:
        if vertex.co.z <= minimum_z + cfg.remesh_voxel_mm * 1.25:
            vertex.co.z = cfg.base_z_mm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return body


def finalize_body(body: bpy.types.Object, cfg: ModelConfig) -> bpy.types.Object:
    body.name = cfg.body_name
    body.data.name = f"{cfg.body_name}_mesh"
    body["crown_teeth"] = cfg.crown_teeth
    body["hole_diameter_mm"] = cfg.hole_diameter_mm
    body["hole_axis"] = cfg.hole_axis
    body["finial_diameter_mm"] = cfg.finial_diameter_mm
    body["model_version"] = cfg.version

    material = bpy.data.materials.get("matte_black_pla") or bpy.data.materials.new("matte_black_pla")
    material.diffuse_color = (0.008, 0.008, 0.010, 1.0)
    material.roughness = 0.58
    body.data.materials.clear()
    body.data.materials.append(material)

    bpy.context.view_layer.objects.active = body
    bpy.ops.object.select_all(action="DESELECT")
    body.hide_set(False)
    body.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mesh = body.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return body
