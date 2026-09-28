"""Build and save the canonical Blender source."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import bpy


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from geometry import (
    create_crown,
    create_finial,
    create_lathed_body,
    cut_ring_hole,
    finalize_body,
    flatten_base,
    join_and_remesh,
    normalize_outer_dimensions,
)
from model_config import ModelConfig


def parse_args():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args(raw)


def main():
    args = parse_args()
    cfg = ModelConfig()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 0.001
    bpy.context.preferences.filepaths.file_preview_type = "NONE"

    parts = [create_lathed_body(cfg), *create_crown(cfg), create_finial(cfg)]
    body = join_and_remesh(parts, cfg)
    body = normalize_outer_dimensions(body, cfg)
    body = cut_ring_hole(body, cfg)
    body = flatten_base(body, cfg)
    body = finalize_body(body, cfg)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print(
        "SOURCE_BUILD="
        + json.dumps(
            {
                "body_name": body.name,
                "bounds_mm": [round(float(value), 4) for value in body.dimensions],
                "crown_teeth": int(body["crown_teeth"]),
                "hole_diameter_mm": float(body["hole_diameter_mm"]),
                "visible_export_bodies": 1,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
