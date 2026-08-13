"""수종별 렌더 프로파일.

shape와 비율은 3D 표현용 설정이며 과학적 생장 계수가 아니다.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpeciesRenderProfile:
    key: str
    scientific_name: str
    shape: str
    color: str
    height_scale: float
    height_limit_m: float
    crown_width_scale: float
    crown_length_ratio: float
    trunk_exposure: float
    crown_layers: int
    crown_irregularity: float
    opacity: float = 0.92
    trunk_visual_boost: float = 1.4
    trunk_boost_decay_m: float = 0.18
    trunk_min_visible_m: float = 0.12


TREE_PROFILES: dict[str, SpeciesRenderProfile] = {
    "소나무": SpeciesRenderProfile(
        "pine", "Pinus densiflora", "layered_conifer", "#3E7D45",
        1.00, 24.0, 1.00, 0.48, 0.52, 3, 0.18,
    ),
    "곰솔": SpeciesRenderProfile(
        "black_pine", "Pinus thunbergii", "layered_conifer", "#285D3C",
        0.92, 22.0, 1.14, 0.52, 0.46, 3, 0.12,
    ),
    "편백": SpeciesRenderProfile(
        "hinoki", "Chamaecyparis obtusa", "pyramid", "#2F6B4F",
        1.10, 28.0, 0.72, 0.68, 0.30, 2, 0.03,
    ),
    "졸참나무": SpeciesRenderProfile(
        "serrata_oak", "Quercus serrata", "rounded", "#72A84B",
        0.92, 25.0, 1.28, 0.48, 0.48, 3, 0.16,
    ),
    "아까시나무": SpeciesRenderProfile(
        "black_locust", "Robinia pseudoacacia", "open_oval", "#83B85A",
        1.00, 22.0, 1.18, 0.43, 0.57, 3, 0.24, 0.82,
    ),
    "붉가시나무": SpeciesRenderProfile(
        "evergreen_oak", "Quercus acuta", "dense_oval", "#356E3C",
        0.88, 23.0, 1.20, 0.54, 0.42, 3, 0.08, 0.96,
    ),
    "신갈나무": SpeciesRenderProfile(
        "mongolian_oak", "Quercus mongolica", "spreading", "#669447",
        0.90, 26.0, 1.42, 0.50, 0.50, 3, 0.18,
    ),
}

SHRUB_PROFILES: dict[str, SpeciesRenderProfile] = {
    # 관목 형태군은 과학적 수형 복원이 아니라 화면 식별을 위한 render profile이다.
    "shrub_rounded": SpeciesRenderProfile(
        "shrub_rounded", "", "shrub_rounded", "#78A95A",
        0.88, 3.2, 1.55, 0.76, 0.12, 3, 0.16, 0.92,
    ),
    "shrub_upright": SpeciesRenderProfile(
        "shrub_upright", "", "shrub_upright", "#5D994F",
        1.12, 4.2, 1.05, 0.88, 0.10, 4, 0.10, 0.91,
    ),
    "shrub_spreading": SpeciesRenderProfile(
        "shrub_spreading", "", "shrub_spreading", "#8CAD57",
        0.66, 2.4, 2.05, 0.62, 0.08, 4, 0.24, 0.90,
    ),
    "shrub_multistem": SpeciesRenderProfile(
        "shrub_multistem", "", "shrub_multistem", "#6FA24D",
        0.96, 3.6, 1.68, 0.82, 0.10, 5, 0.30, 0.88,
    ),
}

SHRUB_PROFILE_BY_SPECIES = {
    "사철나무": "shrub_rounded", "회양목": "shrub_rounded", "남천": "shrub_upright",
    "산철쭉": "shrub_rounded", "조팝나무": "shrub_multistem", "화살나무": "shrub_upright",
    "개나리": "shrub_spreading", "덜꿩나무": "shrub_multistem", "말발도리": "shrub_multistem",
    "병꽃나무": "shrub_multistem", "싸리": "shrub_upright", "수수꽃다리": "shrub_upright",
    "좀작살나무": "shrub_multistem", "쥐똥나무": "shrub_rounded", "흰말채나무": "shrub_spreading",
}

DEFAULT_TREE_PROFILE = SpeciesRenderProfile(
    "default_tree", "", "rounded", "#5F934A",
    0.90, 24.0, 1.10, 0.50, 0.48, 2, 0.10,
)


def profile_for(species: str, kind: str) -> SpeciesRenderProfile:
    if kind == "shrub":
        key = SHRUB_PROFILE_BY_SPECIES.get(species, "shrub_rounded")
        return SHRUB_PROFILES[key]
    return TREE_PROFILES.get(species, DEFAULT_TREE_PROFILE)


def profile_by_key(key: str) -> SpeciesRenderProfile:
    for profile in (*TREE_PROFILES.values(), *SHRUB_PROFILES.values(), DEFAULT_TREE_PROFILE):
        if profile.key == key:
            return profile
    return DEFAULT_TREE_PROFILE
