"""Carbon1 입력 DTO를 불변 지역 시각화 snapshot으로 변환한다."""
from __future__ import annotations

import hashlib
import json

import numpy as np

from ..calculations import project_future_carbon
from .growth_models import diameter_timeline
from .models import (
    RegionVisualizationSnapshot, VegetationGroup, VisualizationInputGroup,
)
from .placement import place_instances, stable_seed
from .species_profiles import profile_for


def input_fingerprint(region_name: str, environment: str, area_w: float, area_h: float,
                      inputs: tuple[VisualizationInputGroup, ...]) -> str:
    payload = {
        "region": region_name,
        "environment": environment,
        "area": [area_w, area_h],
        "inputs": [
            [
                item.species, item.kind, item.diameter, item.quantity,
                item.diameter_unit,
                item.species_data.a, item.species_data.b, item.species_data.cf,
                item.species_data.diameter_min, item.species_data.diameter_max,
                item.species_data.growth_y10, item.species_data.growth_y20,
                item.species_data.growth_y21,
            ]
            for item in inputs
        ],
    }
    serial = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serial.encode("utf-8")).hexdigest()


def build_snapshot(*, region_name: str, environment: str, area_w: float, area_h: float,
                   inputs: tuple[VisualizationInputGroup, ...],
                   warnings: tuple[str, ...] = ()) -> RegionVisualizationSnapshot:
    groups: list[VegetationGroup] = []
    for group_id, item in enumerate(inputs):
        mm_scale = item.kind == "shrub"
        years, carbon = project_future_carbon(
            item.species_data, item.diameter, item.quantity, years=50,
            mm_scale=mm_scale,
        )
        diameters = diameter_timeline(
            item.species_data, item.diameter, years=50, mm_scale=mm_scale,
        )
        groups.append(VegetationGroup(
            group_id=group_id,
            species=item.species,
            kind=item.kind,
            quantity=item.quantity,
            initial_diameter=item.diameter,
            diameter_unit=item.diameter_unit,
            diameter_by_year=diameters,
            carbon_by_year_kgc=carbon,
            profile_key=profile_for(item.species, item.kind).key,
        ))

    group_tuple = tuple(groups)
    seed, placement_fingerprint = stable_seed(
        region_name, environment, area_w, area_h, group_tuple,
    )
    instances = place_instances(group_tuple, area_w, area_h, seed)
    total = np.zeros(51, dtype=float)
    for group in group_tuple:
        total += group.carbon_by_year_kgc
    fingerprint = input_fingerprint(region_name, environment, area_w, area_h, inputs)
    # placement_fingerprint는 현재 fingerprint 구성의 일부와 동일하지만 seed 재현성 검증에 활용.
    assert placement_fingerprint
    return RegionVisualizationSnapshot(
        region_name=region_name,
        environment=environment,
        area_w=float(area_w),
        area_h=float(area_h),
        years=np.arange(51, dtype=int),
        groups=group_tuple,
        instances=instances,
        total_carbon_by_year_kgc=total,
        placement_seed=seed,
        input_fingerprint=fingerprint,
        warnings=warnings,
    )
