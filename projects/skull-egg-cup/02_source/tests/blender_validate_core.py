import json

import bpy


body = bpy.data.objects.get("skull_egg_cup_body")
assert body is not None, "missing skull_egg_cup_body"
assert body.type == "MESH", f"unexpected body type: {body.type}"

dimensions = [float(value) for value in body.dimensions]
assert abs(dimensions[0] - 78.0) <= 2.0, dimensions
assert abs(dimensions[1] - 88.0) <= 2.0, dimensions
assert 70.0 <= dimensions[2] <= 74.1, dimensions

base_z = min((body.matrix_world @ vertex.co).z for vertex in body.data.vertices)
assert abs(base_z) <= 0.05, f"base plane is {base_z:.4f} mm"

egg = bpy.data.objects.get("egg_reference_no_export")
assert egg is not None, "missing egg reference"
assert bool(egg.get("no_export")), "egg reference must be marked no_export"

report = {
    "bounds_mm": [round(value, 4) for value in dimensions],
    "base_z_mm": round(base_z, 4),
    "body_count": len(
        [
            obj
            for obj in bpy.data.objects
            if obj.type == "MESH" and not bool(obj.get("no_export"))
        ]
    ),
}
assert report["body_count"] == 1, report
print("CORE_VALIDATION=" + json.dumps(report, sort_keys=True))
