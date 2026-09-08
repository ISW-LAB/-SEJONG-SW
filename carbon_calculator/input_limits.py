# SPDX-License-Identifier: MIT
"""Site-area safeguards for combined tree and shrub inventories.

The default per-individual planting areas are transparent, configurable input
guards.  They prevent accidental over-entry; they are not species-specific
ecological planting recommendations or estimates of biological carrying
capacity.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


TREE_PLANTING_AREA_M2_PER_INDIVIDUAL = 1.0
SHRUB_PLANTING_AREA_M2_PER_INDIVIDUAL = 0.25


@dataclass(frozen=True)
class PlantingAreaBudget:
    """Resolved site and inventory areas for one calculation request."""

    site_area_m2: float
    tree_quantity: int
    shrub_quantity: int
    tree_area_m2: float
    shrub_area_m2: float
    required_area_m2: float

    @property
    def excess_area_m2(self) -> float:
        return max(0.0, self.required_area_m2 - self.site_area_m2)

    @property
    def is_exceeded(self) -> bool:
        return self.required_area_m2 > self.site_area_m2 + 1e-9


def planting_area_budget(
    *,
    area_w: float,
    area_h: float,
    tree_quantity: int,
    shrub_quantity: int,
    tree_unit_area_m2: float = TREE_PLANTING_AREA_M2_PER_INDIVIDUAL,
    shrub_unit_area_m2: float = SHRUB_PLANTING_AREA_M2_PER_INDIVIDUAL,
) -> PlantingAreaBudget | None:
    """Return the combined planting-area budget, or ``None`` for an invalid site."""

    values = (area_w, area_h, tree_unit_area_m2, shrub_unit_area_m2)
    if not all(math.isfinite(float(value)) for value in values):
        return None
    if area_w <= 0 or area_h <= 0 or tree_unit_area_m2 < 0 or shrub_unit_area_m2 < 0:
        return None

    tree_quantity = max(0, int(tree_quantity))
    shrub_quantity = max(0, int(shrub_quantity))
    site_area_m2 = float(area_w) * float(area_h)
    tree_area_m2 = tree_quantity * float(tree_unit_area_m2)
    shrub_area_m2 = shrub_quantity * float(shrub_unit_area_m2)
    return PlantingAreaBudget(
        site_area_m2=site_area_m2,
        tree_quantity=tree_quantity,
        shrub_quantity=shrub_quantity,
        tree_area_m2=tree_area_m2,
        shrub_area_m2=shrub_area_m2,
        required_area_m2=tree_area_m2 + shrub_area_m2,
    )
