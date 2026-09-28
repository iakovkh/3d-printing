"""Build an immutable one-object 3MF candidate from the exported STL."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import trimesh


BODY_NAME = "staunton_queen_keychain_body"


def build_candidate(stl_path: pathlib.Path, candidate_path: pathlib.Path):
    if candidate_path.exists():
        raise FileExistsError(f"refusing to overwrite candidate: {candidate_path}")
    mesh = trimesh.load_mesh(stl_path, file_type="stl", process=False)
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError(f"expected one STL mesh, got {type(mesh).__name__}")
    mesh.units = "mm"
    mesh.merge_vertices(merge_tex=True, merge_norm=True)
    mesh.remove_unreferenced_vertices()
    mesh.metadata["name"] = BODY_NAME
    scene = trimesh.Scene({BODY_NAME: mesh})
    payload = scene.export(file_type="3mf")
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    return {
        "candidate": str(candidate_path.resolve()),
        "sha256": digest,
        "short_id": digest[:8].upper(),
        "bytes": len(payload),
        "geometry_count": len(scene.geometry),
        "vertex_count": int(len(mesh.vertices)),
        "triangle_count": int(len(mesh.faces)),
        "bounds_mm": [round(float(value), 4) for value in scene.extents],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stl", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if not args.stl.is_file():
        raise FileNotFoundError(args.stl)
    report = build_candidate(args.stl, args.output)
    print("CANDIDATE_BUILD=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

