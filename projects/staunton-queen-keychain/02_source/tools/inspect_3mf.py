"""Inspect the 3MF package independently of Trimesh."""

from __future__ import annotations

import argparse
import json
import pathlib
import xml.etree.ElementTree as ET
import zipfile


REQUIRED_MEMBERS = {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}
CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


def inspect_package(path: pathlib.Path):
    with zipfile.ZipFile(path, "r") as archive:
        members = set(archive.namelist())
        missing = REQUIRED_MEMBERS - members
        if missing:
            raise ValueError(f"3MF package is missing {sorted(missing)}")
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
    namespace = {"m": CORE_NS}
    objects = root.findall("./m:resources/m:object", namespace)
    build_items = root.findall("./m:build/m:item", namespace)
    vertices = root.findall(".//m:mesh/m:vertices/m:vertex", namespace)
    triangles = root.findall(".//m:mesh/m:triangles/m:triangle", namespace)
    result = {
        "unit": root.attrib.get("unit", "millimeter"),
        "object_count": len(objects),
        "build_item_count": len(build_items),
        "vertex_count": len(vertices),
        "triangle_count": len(triangles),
    }
    if result["unit"] != "millimeter":
        raise ValueError(f"3MF unit is {result['unit']!r}, expected 'millimeter'")
    if result["object_count"] != 1 or result["build_item_count"] != 1:
        raise ValueError(f"3MF must contain one object and one build item: {result}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=pathlib.Path)
    args = parser.parse_args()
    print(json.dumps(inspect_package(args.candidate), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
