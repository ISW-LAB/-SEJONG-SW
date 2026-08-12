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

SHRUB_PROFILE = SpeciesRenderProfile(
    "shrub", "", "shrub", "#78A95A",
    0.42, 4.5, 1.55, 0.72, 0.15, 3, 0.18, 0.90,
)

DEFAULT_TREE_PROFILE = SpeciesRenderProfile(
    "default_tree", "", "rounded", "#5F934A",
    0.90, 24.0, 1.10, 0.50, 0.48, 2, 0.10,
)


def profile_for(species: str, kind: str) -> SpeciesRenderProfile:
    if kind == "shrub":
        return SHRUB_PROFILE
    return TREE_PROFILES.get(species, DEFAULT_TREE_PROFILE)


def profile_by_key(key: str) -> SpeciesRenderProfile:
    for profile in (*TREE_PROFILES.values(), SHRUB_PROFILE, DEFAULT_TREE_PROFILE):
        if profile.key == key:
            return profile
    return DEFAULT_TREE_PROFILE
