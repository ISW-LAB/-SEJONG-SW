"""기존 직경 성장자료를 렌더 상태로 변환하는 함수.

탄소량은 이 모듈에서 계산하지 않는다. 수고와 수관 fallback은 오직 geometry용이다.
"""
from __future__ import annotations

import math

import numpy as np

from .models import ModelValue, RenderState, RegionVisualizationSnapshot
from .species_profiles import SpeciesRenderProfile, profile_by_key


BLACK_LOCUST_DBH_RANGE = (3.66, 28.81)
BLACK_LOCUST_SOURCE = "Manolopoulos et al. 2022, DOI:10.3390/land11040471"
VISUAL_FALLBACK_SOURCE = "Carbon1 3D visual fallback (not a scientific height/crown model)"


def diameter_timeline(species_data, starting_diameter: float, *, years: int = 50,
                      mm_scale: bool = False) -> np.ndarray:
    """Carbon1 project_future_carbon과 같은 규칙으로 직경 timeline을 만든다."""
    scale = 10.0 if mm_scale else 1.0
    values = np.zeros(years + 1, dtype=float)
    values[0] = starting_diameter
    for year in range(1, years + 1):
        values[year] = values[year - 1] + species_data.growth_at_year(year) * scale
    return values


def visual_development(elapsed_year: int) -> float:
    """실제 수령이 아닌 elapsed year 기반 렌더링 전용 성숙도(0..1)."""
    return max(0.0, min(1.0, 1.0 - math.exp(-max(0, elapsed_year) / 18.0)))


def _fallback_height(diameter_m: float, profile: SpeciesRenderProfile, kind: str) -> float:
    # 포화형 함수: 작은 직경에서도 보이며 큰 직경에서 profile limit에 점근한다.
    base = 0.58 if kind == "shrub" else 1.3
    rate = 20.0 if kind == "shrub" else 5.4
    scaled = 1.0 - math.exp(-rate * max(0.0, diameter_m) * profile.height_scale)
    return base + (profile.height_limit_m - base) * scaled


def rendered_height(species: str, diameter_value: float, diameter_unit: str,
                    profile: SpeciesRenderProfile, kind: str) -> ModelValue:
    diameter_m = diameter_value / (100.0 if diameter_unit == "cm" else 1000.0)
    if species == "아까시나무" and diameter_unit == "cm":
        lo, hi = BLACK_LOCUST_DBH_RANGE
        if lo <= diameter_value <= hi:
            d = diameter_value
            height = -1.989 + 2.036 * d - 0.078 * d**2 + 0.001 * d**3
            return ModelValue(max(1.3, height), "m", "validated", BLACK_LOCUST_SOURCE)
        status = "out_of_range_fallback"
    else:
        status = "visual_fallback"
    return ModelValue(
        _fallback_height(diameter_m, profile, kind), "m", status,
        VISUAL_FALLBACK_SOURCE,
    )


def rendered_crown(profile: SpeciesRenderProfile, diameter_m: float,
                   height_m: float, elapsed_year: int, kind: str) -> tuple[ModelValue, ModelValue]:
    development = visual_development(elapsed_year)
    min_width = 0.65 if kind == "shrub" else 0.55
    width_limit = height_m * (1.65 if kind == "shrub" else 0.78)
    raw_width = min_width + profile.crown_width_scale * math.sqrt(max(diameter_m, 0.001)) * 4.0
    width = min(width_limit, raw_width) * (0.72 + 0.28 * development)
    length = max(0.25, height_m * profile.crown_length_ratio * (0.82 + 0.18 * development))
    source = "Carbon1 3D visual crown fallback (not a scientific crown model)"
    return (
        ModelValue(width, "m", "visual_fallback", source),
        ModelValue(length, "m", "visual_fallback", source),
    )


def render_states(snapshot: RegionVisualizationSnapshot, year: int) -> tuple[RenderState, ...]:
    year = max(0, min(50, int(year)))
    groups = {g.group_id: g for g in snapshot.groups}
    states: list[RenderState] = []
    for instance in snapshot.instances:
        group = groups[instance.group_id]
        profile = profile_by_key(group.profile_key)
        diameter = float(group.diameter_by_year[year])
        diameter_m = diameter / (100.0 if group.diameter_unit == "cm" else 1000.0)
        height = rendered_height(group.species, diameter, group.diameter_unit, profile, group.kind)
        crown_width, crown_length = rendered_crown(
            profile, diameter_m, height.value, year, group.kind,
        )
        states.append(RenderState(
            instance_id=instance.instance_id,
            profile_key=group.profile_key,
            kind=group.kind,
            x_m=instance.x_m,
            y_m=instance.y_m,
            diameter_m=diameter_m,
            rendered_height_m=height,
            rendered_crown_width_m=crown_width,
            rendered_crown_length_m=crown_length,
            visual_development=visual_development(year),
        ))
    return tuple(states)
