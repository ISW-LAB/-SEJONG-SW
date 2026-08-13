"""Qt/VTK에 의존하지 않는 3D 시각화 데이터 객체."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


@dataclass(frozen=True)
class VisualizationInputGroup:
    """MainWindow 입력을 3D 계층으로 넘기는 plain DTO."""
    species: str
    kind: Literal["tree", "shrub"]
    diameter: float
    quantity: int
    diameter_unit: Literal["cm", "mm"]
    species_data: object


ModelStatus = Literal["existing_project_data", "visual_fallback"]


@dataclass(frozen=True)
class ModelValue:
    value: float
    unit: str
    status: ModelStatus
    source: str


@dataclass(frozen=True)
class VegetationGroup:
    group_id: int
    species: str
    kind: Literal["tree", "shrub"]
    quantity: int
    initial_diameter: float
    diameter_unit: Literal["cm", "mm"]
    diameter_by_year: np.ndarray
    carbon_by_year_kgc: np.ndarray
    profile_key: str
    a: float
    b: float
    cf: float
    growth_y10: float
    growth_y20: float
    growth_y21: float


@dataclass(frozen=True)
class VegetationInstance:
    instance_id: int
    group_id: int
    species: str
    kind: Literal["tree", "shrub"]
    x_m: float
    y_m: float


@dataclass(frozen=True)
class RenderState:
    instance_id: int
    profile_key: str
    kind: Literal["tree", "shrub"]
    x_m: float
    y_m: float
    diameter_m: float
    rendered_trunk_diameter_m: ModelValue
    rendered_height_m: ModelValue
    rendered_crown_width_m: ModelValue
    rendered_crown_length_m: ModelValue
    visual_development: float


@dataclass(frozen=True)
class RegionVisualizationSnapshot:
    region_name: str
    environment: str
    area_w: float
    area_h: float
    years: np.ndarray
    groups: tuple[VegetationGroup, ...]
    instances: tuple[VegetationInstance, ...]
    total_carbon_by_year_kgc: np.ndarray
    placement_seed: int
    input_fingerprint: str
    warnings: tuple[str, ...] = ()

    @property
    def tree_count(self) -> int:
        return sum(g.quantity for g in self.groups if g.kind == "tree")

    @property
    def shrub_count(self) -> int:
        return sum(g.quantity for g in self.groups if g.kind == "shrub")
