import json

import bmesh
import bpy


body = bpy.data.objects.get("skull_egg_cup_body")
assert body is not None, "missing skull_egg_cup_body"
assert body.type == "MESH"

bm = bmesh.new()
bm.from_mesh(body.data)
boundary = [edge for edge in bm.edges if edge.is_boundary]
non_manifold = [edge for edge in bm.edges if not edge.is_manifold]
components = 0
unseen = set(bm.verts)
while unseen:
    components += 1
    stack = [unseen.pop()]
    while stack:
        vertex = stack.pop()
        neighbours = {edge.other_vert(vertex) for edge in vertex.link_edges}
        found = neighbours & unseen
        unseen.difference_update(found)
        stack.extend(found)

report = {
    "vertices": len(bm.verts),
    "faces": len(bm.faces),
    "boundary_edges": len(boundary),
    "non_manifold_edges": len(non_manifold),
    "connected_components": components,
    "bounds_mm": [round(float(value), 4) for value in body.dimensions],
}
bm.free()

assert report["boundary_edges"] == 0, report
assert report["non_manifold_edges"] == 0, report
assert report["connected_components"] == 1, report
assert report["faces"] >= 8000, report

for feature in (
    "brow_ridge",
    "left_eye_socket",
    "right_eye_socket",
    "nasal_cavity",
    "cheekbones",
    "teeth_relief",
    "cranial_sutures",
    "bone_microrelief",
):
    assert bool(body.get(feature)), f"missing feature marker {feature}"

assert abs(float(body.get("opening_diameter_mm", 0.0)) - 42.0) <= 0.2
assert abs(float(body.get("cavity_depth_mm", 0.0)) - 22.0) <= 0.2
assert len([obj for obj in bpy.data.objects if obj.type == "MESH" and not bool(obj.get("no_export"))]) == 1
print("SOURCE_VALIDATION=" + json.dumps(report, sort_keys=True))
