"""Validate the saved canonical Blender source."""

import math

import bmesh
import bpy


def count_circular_clusters(angles, gap_degrees=20.0):
    if not angles:
        return 0
    values = sorted(angle % (2.0 * math.pi) for angle in angles)
    gaps = [
        (values[(index + 1) % len(values)] - values[index]) % (2.0 * math.pi)
        for index in range(len(values))
    ]
    threshold = math.radians(gap_degrees)
    return max(1, sum(gap > threshold for gap in gaps))


assert count_circular_clusters([2.0 * math.pi * i / 7.0 for i in range(7)]) == 7
assert count_circular_clusters([2.0 * math.pi * i / 8.0 for i in range(8)]) == 8
assert count_circular_clusters([2.0 * math.pi * i / 9.0 for i in range(9)]) == 9

body = bpy.data.objects.get("staunton_queen_keychain_body")
assert body is not None, "missing staunton_queen_keychain_body"
assert body.type == "MESH"
assert abs(body.dimensions.x - 22.5) <= 0.10, body.dimensions.x
assert abs(body.dimensions.y - 22.5) <= 0.10, body.dimensions.y
assert abs(body.dimensions.z - 50.0) <= 0.10, body.dimensions.z
assert body.get("crown_teeth") == 8
assert abs(float(body.get("hole_diameter_mm")) - 3.2) <= 0.001
assert body.get("hole_axis") == "X"

world_vertices = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
base_z = min(vertex.z for vertex in world_vertices)
assert abs(base_z) <= 0.05, base_z

tip_angles = [
    math.atan2(vertex.y, vertex.x)
    for vertex in world_vertices
    if 42.45 <= vertex.z <= 43.60 and math.hypot(vertex.x, vertex.y) >= 5.2
]
peak_count = count_circular_clusters(tip_angles)
assert peak_count == 8, f"expected 8 crown peaks, found {peak_count}"

exportable = [
    obj
    for obj in bpy.context.scene.objects
    if obj.type == "MESH" and not bool(obj.get("no_export")) and not obj.hide_get()
]
assert exportable == [body], [obj.name for obj in exportable]

bm = bmesh.new()
bm.from_mesh(body.data)
boundary = [edge for edge in bm.edges if edge.is_boundary]
non_manifold = [edge for edge in bm.edges if not edge.is_manifold]
euler_number = len(bm.verts) - len(bm.edges) + len(bm.faces)
assert not boundary, f"boundary edges: {len(boundary)}"
assert not non_manifold, f"non-manifold edges: {len(non_manifold)}"
assert euler_number == 0, f"expected Euler 0 for one through-hole, found {euler_number}"
bm.free()

print(
    "SOURCE_VALIDATION="
    + str(
        {
            "bounds_mm": [round(float(value), 4) for value in body.dimensions],
            "base_z_mm": round(float(base_z), 4),
            "crown_peaks": peak_count,
            "euler_number": euler_number,
            "exportable_bodies": 1,
        }
    )
)
