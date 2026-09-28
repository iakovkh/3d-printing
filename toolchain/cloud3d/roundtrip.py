"""Independently reopen a candidate and export only reopened geometry."""

from __future__ import annotations

import dataclasses
import pathlib
import re

import numpy as np
import trimesh

from .three_mf import PackageReport, Transform, inspect_package


@dataclasses.dataclass(frozen=True)
class RoundTripReport:
    candidate: pathlib.Path
    unit: str
    body_names: tuple[str, ...]
    transforms: dict[str, Transform]
    colors: dict[str, str]
    extents_mm: tuple[float, float, float]
    body_volumes_mm3: dict[str, float]
    reopened_bodies: dict[str, pathlib.Path]


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._") or "body"


def _geometry_for_body(
    scene: trimesh.Scene, package: PackageReport, name: str, index: int
) -> trimesh.Trimesh:
    geometries = list(scene.geometry.items())
    if name in scene.geometry:
        mesh = scene.geometry[name].copy()
    elif index < len(geometries):
        mesh = geometries[index][1].copy()
    else:
        raise ValueError(f"reopened 3MF is missing geometry for {name}")
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError(f"reopened body {name} is not a Trimesh")
    mesh.apply_transform(np.asarray(package.transforms[name], dtype=float))
    return mesh


def reopen_candidate(candidate: pathlib.Path, output_dir: pathlib.Path) -> RoundTripReport:
    package = inspect_package(candidate)
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite reopened output: {output_dir}")
    output_dir.mkdir(parents=True)
    loaded = trimesh.load(candidate, force="scene", process=False)
    scene = loaded if isinstance(loaded, trimesh.Scene) else trimesh.Scene(loaded)
    if len(scene.geometry) != package.object_count:
        raise ValueError(
            f"reopened body count {len(scene.geometry)} != package count {package.object_count}"
        )
    reopened: dict[str, pathlib.Path] = {}
    volumes: dict[str, float] = {}
    world_meshes: list[trimesh.Trimesh] = []
    for index, name in enumerate(package.body_names):
        mesh = _geometry_for_body(scene, package, name, index)
        destination = output_dir / f"reopened_{_safe_name(name)}.stl"
        destination.write_bytes(mesh.export(file_type="stl"))
        reopened[name] = destination.resolve()
        volumes[name] = abs(float(mesh.volume))
        world_meshes.append(mesh)
    bounds = np.vstack([mesh.bounds for mesh in world_meshes])
    extents = bounds.max(axis=0) - bounds.min(axis=0)
    return RoundTripReport(
        candidate=candidate.resolve(),
        unit=package.unit,
        body_names=package.body_names,
        transforms=package.transforms,
        colors=package.colors,
        extents_mm=tuple(float(value) for value in extents),
        body_volumes_mm3=volumes,
        reopened_bodies=reopened,
    )

