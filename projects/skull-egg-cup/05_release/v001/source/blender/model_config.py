from typing import NamedTuple


class ModelConfig(NamedTuple):
    name: str = "skull_egg_cup"
    version: str = "v001"
    egg_diameter_mm: float = 45.0
    egg_height_mm: float = 58.0
    opening_diameter_mm: float = 42.0
    cavity_depth_mm: float = 22.0
    min_wall_mm: float = 2.4
    min_relief_mm: float = 0.8
    target_width_mm: float = 78.0
    target_depth_mm: float = 88.0
    target_height_mm: float = 72.0
    dimension_tolerance_mm: float = 0.2
    envelope_tolerance_mm: float = 2.0
    body_count: int = 1


CONFIG = ModelConfig()

