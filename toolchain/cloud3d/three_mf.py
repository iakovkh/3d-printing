"""Build and inspect immutable, traceable 3MF candidate packages."""

from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import pathlib
import re
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Sequence

import numpy as np
import trimesh


CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
MATERIAL_NS = "http://schemas.microsoft.com/3dmanufacturing/material/2015/02"
PRODUCTION_NS = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
REQUIRED_MEMBERS = {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}
_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


Transform = tuple[tuple[float, float, float, float], ...]


@dataclasses.dataclass(frozen=True)
class BodyInput:
    path: pathlib.Path
    name: str
    color: str
    transform: Transform


@dataclasses.dataclass(frozen=True)
class CandidateIdentity:
    path: pathlib.Path
    sha256: str
    short_id: str
    size_bytes: int
    body_names: tuple[str, ...]
    bounds_mm: tuple[float, float, float]


@dataclasses.dataclass(frozen=True)
class PackageReport:
    path: pathlib.Path
    unit: str
    object_count: int
    build_item_count: int
    vertex_count: int
    triangle_count: int
    body_names: tuple[str, ...]
    transforms: dict[str, Transform]
    colors: dict[str, str]


def _matrix(value: Transform) -> np.ndarray:
    matrix = np.asarray(value, dtype=float)
    if matrix.shape != (4, 4) or not np.allclose(matrix[3], (0.0, 0.0, 0.0, 1.0)):
        raise ValueError("body transform must be an affine 4x4 matrix")
    return matrix


def _normalize_bodies(bodies: Sequence[BodyInput]) -> tuple[BodyInput, ...]:
    result = tuple(bodies)
    if not result:
        raise ValueError("candidate requires at least one body")
    names: set[str] = set()
    for body in result:
        if not body.name or body.name in names:
            raise ValueError(f"body names must be non-empty and unique: {body.name!r}")
        names.add(body.name)
        if not _COLOR.fullmatch(body.color):
            raise ValueError(f"body color must be #RRGGBB: {body.color!r}")
        _matrix(body.transform)
    return result


def _flatten_transform(transform: Transform) -> list[float]:
    return [float(value) for row in transform for value in row]


def _validate_source_manifest(
    bodies: tuple[BodyInput, ...], source_manifest: pathlib.Path
) -> None:
    raw = json.loads(source_manifest.read_text(encoding="utf-8"))
    declared = raw.get("bodies")
    if not isinstance(declared, list) or len(declared) != len(bodies):
        raise ValueError("source manifest body count does not match candidate")
    by_name = {body.name: body for body in bodies}
    for item in declared:
        if not isinstance(item, dict) or item.get("name") not in by_name:
            raise ValueError("source manifest body names do not match candidate")
        body = by_name[item["name"]]
        if str(item.get("color", "")).upper() != body.color.upper():
            raise ValueError(f"source manifest color mismatch for {body.name}")
        values = item.get("transform")
        if not isinstance(values, list) or len(values) != 16:
            raise ValueError(f"source manifest transform is invalid for {body.name}")
        if not np.allclose(values, _flatten_transform(body.transform), atol=1e-9):
            raise ValueError(f"source manifest transform mismatch for {body.name}")


def _add_material_colors(payload: bytes, bodies: tuple[BodyInput, ...]) -> bytes:
    source = io.BytesIO(payload)
    members: dict[str, bytes] = {}
    with zipfile.ZipFile(source, "r") as archive:
        for name in archive.namelist():
            members[name] = archive.read(name)

    ET.register_namespace("", CORE_NS)
    ET.register_namespace("m", MATERIAL_NS)
    ET.register_namespace("p", PRODUCTION_NS)
    root = ET.fromstring(members["3D/3dmodel.model"])
    resources = root.find(f"{{{CORE_NS}}}resources")
    if resources is None:
        raise ValueError("3MF model has no resources")
    objects = resources.findall(f"{{{CORE_NS}}}object")
    mesh_objects = [item for item in objects if item.find(f"{{{CORE_NS}}}mesh") is not None]
    by_name = {item.attrib.get("name"): item for item in mesh_objects}
    if set(by_name) != {body.name for body in bodies}:
        raise ValueError("exported 3MF body names do not match inputs")
    object_ids = [int(item.attrib["id"]) for item in objects]
    group_id = str(max(object_ids, default=0) + 1)
    group = ET.Element(f"{{{MATERIAL_NS}}}colorgroup", {"id": group_id})
    resources.insert(0, group)
    for index, body in enumerate(bodies):
        ET.SubElement(group, f"{{{MATERIAL_NS}}}color", {"color": body.color.upper()})
        by_name[body.name].set("pid", group_id)
        by_name[body.name].set("pindex", str(index))
    root.set("requiredextensions", "m")
    members["3D/3dmodel.model"] = ET.tostring(
        root, encoding="utf-8", xml_declaration=True
    )

    destination = io.BytesIO()
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=5
    ) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return destination.getvalue()


def build_candidate(
    bodies: Sequence[BodyInput],
    candidate_path: pathlib.Path,
    *,
    source_manifest: pathlib.Path | None = None,
) -> CandidateIdentity:
    if candidate_path.exists():
        raise FileExistsError(f"refusing to overwrite candidate: {candidate_path}")
    normalized = _normalize_bodies(bodies)
    if source_manifest is not None:
        _validate_source_manifest(normalized, source_manifest)
    scene = trimesh.Scene()
    for body in normalized:
        mesh = trimesh.load_mesh(body.path, file_type=body.path.suffix.lstrip("."), process=False)
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError(f"expected one mesh for {body.name}, got {type(mesh).__name__}")
        mesh.units = "mm"
        mesh.merge_vertices(merge_tex=True, merge_norm=True)
        mesh.remove_unreferenced_vertices()
        mesh.metadata["name"] = body.name
        scene.add_geometry(
            mesh,
            node_name=body.name,
            geom_name=body.name,
            transform=_matrix(body.transform),
        )
    payload = scene.export(file_type="3mf")
    payload = _add_material_colors(payload, normalized)
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    return CandidateIdentity(
        path=candidate_path.resolve(),
        sha256=digest,
        short_id=digest[:8].upper(),
        size_bytes=len(payload),
        body_names=tuple(body.name for body in normalized),
        bounds_mm=tuple(round(float(value), 6) for value in scene.extents),
    )


def _parse_transform(raw: str | None) -> Transform:
    if raw is None:
        return (
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
    values = np.asarray([float(value) for value in raw.split()], dtype=float)
    if values.size != 12:
        raise ValueError("3MF transform must contain 12 values")
    matrix = np.eye(4)
    matrix[:3, :4] = values.reshape((4, 3)).T
    return tuple(tuple(float(value) for value in row) for row in matrix)


def inspect_package(path: pathlib.Path) -> PackageReport:
    with zipfile.ZipFile(path, "r") as archive:
        members = set(archive.namelist())
        missing = REQUIRED_MEMBERS - members
        if missing:
            raise ValueError(f"3MF package is missing {sorted(missing)}")
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
    unit = root.attrib.get("unit", "millimeter")
    if unit != "millimeter":
        raise ValueError(f"3MF unit is {unit!r}, expected 'millimeter'")
    resources = root.find(f"{{{CORE_NS}}}resources")
    build = root.find(f"{{{CORE_NS}}}build")
    if resources is None or build is None:
        raise ValueError("3MF is missing resources or build")
    objects = resources.findall(f"{{{CORE_NS}}}object")
    mesh_objects = [item for item in objects if item.find(f"{{{CORE_NS}}}mesh") is not None]
    object_by_id = {item.attrib["id"]: item for item in objects}
    color_groups: dict[str, list[str]] = {}
    for group in resources.findall(f"{{{MATERIAL_NS}}}colorgroup"):
        color_groups[group.attrib["id"]] = [
            color.attrib["color"].upper()
            for color in group.findall(f"{{{MATERIAL_NS}}}color")
        ]
    items = build.findall(f"{{{CORE_NS}}}item")
    names: list[str] = []
    transforms: dict[str, Transform] = {}
    colors: dict[str, str] = {}
    for item in items:
        obj = object_by_id.get(item.attrib.get("objectid", ""))
        if obj is None:
            raise ValueError("3MF build references an unknown object")
        name = item.attrib.get("partnumber") or obj.attrib.get("name")
        if not name:
            raise ValueError("3MF build item has no stable name")
        names.append(name)
        transforms[name] = _parse_transform(item.attrib.get("transform"))
        pid = obj.attrib.get("pid")
        pindex = int(obj.attrib.get("pindex", "0"))
        if pid in color_groups and pindex < len(color_groups[pid]):
            colors[name] = color_groups[pid][pindex]
    vertices = root.findall(f".//{{{CORE_NS}}}vertex")
    triangles = root.findall(f".//{{{CORE_NS}}}triangle")
    return PackageReport(
        path=path.resolve(),
        unit=unit,
        object_count=len(mesh_objects),
        build_item_count=len(items),
        vertex_count=len(vertices),
        triangle_count=len(triangles),
        body_names=tuple(names),
        transforms=transforms,
        colors=colors,
    )

