"""Approved immutable parameters for Staunton Queen Keychain v001."""

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ModelConfig:
    model_name: str = "staunton_queen_keychain"
    version: str = "v002"
    body_name: str = "staunton_queen_keychain_body"
    height_mm: float = 50.0
    base_diameter_mm: float = 22.5
    finial_diameter_mm: float = 8.0
    finial_center_z_mm: float = 46.0
    hole_diameter_mm: float = 3.2
    hole_axis: str = "X"
    hole_chamfer_mm: float = 0.4
    crown_teeth: int = 8
    base_z_mm: float = 0.0
    remesh_voxel_mm: float = 0.12
    repair_voxel_mm: float = 0.06
    dimensional_tolerance_mm: float = 0.10
    base_plane_tolerance_mm: float = 0.05
    minimum_hole_ligament_mm: float = 2.20
    lathe_profile: Sequence[tuple[float, float]] = (
        (0.00, 10.80),
        (0.45, 11.25),
        (2.40, 11.25),
        (3.20, 10.80),
        (4.40, 9.85),
        (5.60, 9.65),
        (7.80, 10.65),
        (9.80, 10.10),
        (12.20, 8.40),
        (14.50, 6.90),
        (18.00, 5.80),
        (23.50, 4.85),
        (28.20, 4.45),
        (30.20, 5.00),
        (31.30, 6.55),
        (32.70, 6.70),
        (34.00, 5.85),
        (35.60, 5.40),
    )
