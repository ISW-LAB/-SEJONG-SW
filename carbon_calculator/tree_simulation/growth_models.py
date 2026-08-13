"""기존 직경 성장자료를 렌더 상태로 변환하는 함수.

탄소량은 이 모듈에서 계산하지 않는다. 수고와 수관 fallback은 오직 geometry용이다.
"""
from __future__ import annotations

import math

import numpy as np

from .models import ModelValue, RenderState, RegionVisualizationSnapshot
from .species_profiles import SpeciesRenderProfile, profile_by_key


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
    """실제 수령이 아닌 현재 상태 이후 경과 연도의 시각적 발달도(0..1)."""
    return max(0.0, min(1.0, elapsed_year / 50.0))


def _fallback_height(diameter_m: float, profile: SpeciesRenderProfile, kind: str,
                     elapsed_year: int) -> float:
    # 포화형 함수: 작은 직경에서도 보이며 큰 직경에서 profile limit에 점근한다.
    base = 0.58 if kind == "shrub" else 1.3
    # 관목은 mm→m 변환 뒤에도 RCD 변화가 화면에서 드러나되 조기 포화되지 않게 한다.
    rate = 8.0 if kind == "shrub" else 3.8
    scaled = 1.0 - math.exp(-rate * max(0.0, diameter_m) * profile.height_scale)
    development = visual_development(elapsed_year)
    # 직경과 경과 시간을 별도 시각 성분으로 합쳐 조기 포화를 피한다. 최대값보다
    # 여유를 남겨 전 구간에서 성장 변화가 보이도록 한 렌더링 전용 mapping이다.
    if kind == "shrub":
        progress = 0.68 * scaled + 0.22 * development * profile.visual_growth_scale
    else:
        progress = 0.78 * scaled + 0.14 * development * profile.visual_growth_scale
    return base + (profile.height_limit_m - base) * min(0.96, progress)


def rendered_height(species: str, diameter_value: float, diameter_unit: str,
                    profile: SpeciesRenderProfile, kind: str,
                    elapsed_year: int = 0) -> ModelValue:
    diameter_m = diameter_value / (100.0 if diameter_unit == "cm" else 1000.0)
    return ModelValue(
        _fallback_height(diameter_m, profile, kind, elapsed_year), "m", "visual_fallback",
        VISUAL_FALLBACK_SOURCE,
    )


def rendered_trunk_diameter(diameter_m: float, profile: SpeciesRenderProfile) -> ModelValue:
    """실제 DBH/RCD와 분리된 단순 geometry용 줄기 표시 직경."""
    boost = 1.0 + profile.trunk_visual_boost * math.exp(
        -diameter_m / profile.trunk_boost_decay_m
    )
    value = max(profile.trunk_min_visible_m, diameter_m * boost)
    return ModelValue(value, "m", "visual_fallback", "3D visibility adjustment")


def rendered_crown(profile: SpeciesRenderProfile, diameter_m: float,
                   height_m: float, elapsed_year: int, kind: str) -> tuple[ModelValue, ModelValue]:
    development = visual_development(elapsed_year)
    min_width = 0.65 if kind == "shrub" else 0.55
    width_limit = height_m * (1.65 if kind == "shrub" else 0.78)
    raw_width = min_width + profile.crown_width_scale * math.sqrt(max(diameter_m, 0.001)) * 4.0
    growth = profile.visual_growth_scale * development
    width_factor = (0.62 + 0.38 * growth) if kind == "shrub" else (0.76 + 0.24 * growth)
    length_factor = (0.68 + 0.32 * growth) if kind == "shrub" else (0.80 + 0.20 * growth)
    width = min(width_limit, raw_width) * width_factor
    length = max(0.25, height_m * profile.crown_length_ratio * length_factor)
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
        height = rendered_height(
            group.species, diameter, group.diameter_unit, profile, group.kind, year,
        )
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
            rendered_trunk_diameter_m=rendered_trunk_diameter(diameter_m, profile),
            rendered_height_m=height,
            rendered_crown_width_m=crown_width,
            rendered_crown_length_m=crown_length,
            visual_development=visual_development(year),
        ))
    return tuple(states)
