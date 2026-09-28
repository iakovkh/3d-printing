from __future__ import annotations

import pathlib

import trimesh


def write_box_stl(path: pathlib.Path, extents: tuple[float, float, float]) -> pathlib.Path:
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation((0.0, 0.0, extents[2] / 2.0))
    path.write_bytes(mesh.export(file_type="stl"))
    return path

