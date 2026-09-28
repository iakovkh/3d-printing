import json

import bmesh
import bpy


body = bpy.data.objects["skull_egg_cup_body"]
bm = bmesh.new()
bm.from_mesh(body.data)
boundary = [edge for edge in bm.edges if edge.is_boundary]
non_manifold = [edge for edge in bm.edges if not edge.is_manifold]
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
report = {
    "vertices": len(bm.verts),
    "faces": len(bm.faces),
    "boundary_edges": len(boundary),
    "non_manifold_edges": len(non_manifold),
    "components": components,
}
bm.free()
print("REFERENCE_TOPOLOGY=" + json.dumps(report, sort_keys=True))
