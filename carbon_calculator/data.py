# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
수종별 탄소량 계산 데이터.

원본 MATLAB (Carbon_251002_5.mlapp) 의 TreeDataMap/TreeGrowthMap/TreeDiameterRangeMap +
ShrubDataMap/ShrubGrowthMap/ShrubDiameterRangeMap 을 단일 dict 구조로 통합.

수종 라벨·상대생장식(a, b)·변수·범위는 **`상대생장식 자료_최종본.xlsx` 의
「기초 DB 자료」 시트** 와 일치하도록 정합 (Ver. 1.2).

성장률(growth_y10/y20/y21)은 CSV에 없으므로 MATLAB 원본의 TreeGrowthMap / ShrubGrowthMap
에서 위치 매칭으로 가져옴.

CSV vs MATLAB 차이 (CSV를 출처상의 진실로 채택):
- 회양목      : CSV a=0.000018  (MATLAB 0.00018 - 10배 차이)
- 좀작살나무 : CSV a=0.0021     (MATLAB 0.00021 - 10배 차이)
- 수수꽃다리 : CF=0.45 (CSV에 CF 정보 없음; MATLAB 원본 값 유지)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SpeciesData:
    a: float            # allometric 회귀계수 a
    b: float            # allometric 회귀계수 b
    cf: float           # 탄소전환계수 (biomass kg → C kg)
    diameter_min_native: float
    diameter_max_native: float
    growth_y10: float   # 1~10년 성장률 (cm/yr)
    growth_y20: float   # 11~20년 성장률 (cm/yr)
    growth_y21: float   # 21년 이후 성장률 (cm/yr)
    equation_diameter_unit: Literal["cm", "mm"] = "cm"

    @property
    def equation_diameter_scale(self) -> float:
        """Centimetre input을 원 상대생장식의 직경 단위로 변환하는 배율."""
        return 10.0 if self.equation_diameter_unit == "mm" else 1.0

    @property
    def diameter_min(self) -> float:
        """Assessment Application에 노출되는 최소 직경(cm)."""
        return self.diameter_min_native / self.equation_diameter_scale

    @property
    def diameter_max(self) -> float:
        """Assessment Application에 노출되는 최대 직경(cm)."""
        return self.diameter_max_native / self.equation_diameter_scale

    def to_equation_diameter(self, diameter_cm: float | object):
        """공개 입력(cm)을 계수 적합 시 사용된 원 직경 단위로 변환한다."""
        return diameter_cm * self.equation_diameter_scale

    def growth_at_year(self, year: int) -> float:
        if year <= 10:
            return self.growth_y10
        if year <= 20:
            return self.growth_y20
        return self.growth_y21


# 대상지 유형 — 프로젝트 설명과 결과 구분을 위한 메타데이터.
RESTORATION_ENVIRONMENTS = (
    "산불피해지 자연복원",
    "산불피해지 인공복원",
    "채석장 인공복원",
)
DEFAULT_ENVIRONMENT = RESTORATION_ENVIRONMENTS[0]


def _env_species(default: SpeciesData) -> dict:
    """수종별 기본 계수 레코드를 내부 형식으로 감싼다."""
    return {"default": default}


# 교목 (Tree) — 수종별 검증된 기본 계수 레코드.
# 라벨/계수/범위 출처: 「기초 DB 자료」 시트 순번 1, 2, 3, 4, 5, 6, 7, 8, 9
TREE_BASE: dict[str, dict] = {
    "소나무":     _env_species(SpeciesData(0.0737, 2.5735, 0.5, 1, 15, 0.11, 0.20, 0.70)),
    "곰솔":       _env_species(SpeciesData(0.0679, 2.5770, 0.5, 1, 29, 0.24, 0.32, 0.32)),
    "편백":       _env_species(SpeciesData(0.3617, 2.0450, 0.5, 1, 50, 0.11, 0.23, 0.23)),
    "졸참나무":   _env_species(SpeciesData(0.2002, 2.3767, 0.5, 1, 30, 0.13, 0.30, 0.30)),
    "아까시나무": _env_species(SpeciesData(0.1391, 2.5016, 0.5, 1, 30, 0.14, 0.20, 0.20)),
    "붉가시나무": _env_species(SpeciesData(0.1926, 2.4300, 0.5, 1, 40, 0.12, 0.16, 0.16)),
    "신갈나무":   _env_species(SpeciesData(0.0147, 3.1075, 0.5, 6, 30, 0.40, 0.40, 0.40)),
}

# 관목 (Shrub, 15종).
# 공개 입력과 범위 표시는 RCD cm로 통일한다. 다만 기존 15개 상대생장식의
# 계수는 RCD mm로 적합되었으므로 식 평가 직전에만 cm×10 변환을 적용한다.
# 라벨/계수/범위 출처: 「기초 DB 자료」 시트 순번 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 23, 21, 22, 24
def _legacy_shrub_species(*values: float) -> SpeciesData:
    return SpeciesData(*values, equation_diameter_unit="mm")


SHRUB_SPECIES: dict[str, SpeciesData] = {
    "사철나무":     _legacy_shrub_species(0.0002,    2.50, 0.50,  6, 53, 0.30, 0.22, 0.22),
    "산철쭉":       _legacy_shrub_species(0.0003,    2.40, 0.50,  1, 22, 0.31, 0.17, 0.17),
    "조팝나무":     _legacy_shrub_species(0.00025,   2.60, 0.50,  5, 44, 0.20, 0.14, 0.14),
    # 순번 13 (Excel a=0.000022; MATLAB 원본 0.00022 의 1/10 — 회양목과 동일 패턴, Excel 채택)
    # 성장률은 MATLAB 원본 위치매칭값(0.38/0.25/0.25) 사용
    "화살나무":     _legacy_shrub_species(0.000022,  2.55, 0.50, 11, 67, 0.38, 0.25, 0.25),
    "회양목":       _legacy_shrub_species(0.000018,  2.70, 0.50,  8, 30, 0.24, 0.17, 0.17),
    "개나리":       _legacy_shrub_species(0.00028,   2.45, 0.50,  4, 26, 0.16, 0.16, 0.16),
    "남천":         _legacy_shrub_species(0.00031,   2.30, 0.50,  4, 35, 0.24, 0.22, 0.22),
    "덜꿩나무":     _legacy_shrub_species(0.00026,   2.50, 0.50,  7, 39, 0.35, 0.00, 0.00),
    "말발도리":     _legacy_shrub_species(0.00023,   2.60, 0.50,  4, 25, 0.30, 0.00, 0.00),
    "병꽃나무":     _legacy_shrub_species(0.00029,   2.40, 0.50,  6, 39, 0.30, 0.24, 0.24),
    "싸리":         _legacy_shrub_species(0.00015,   2.80, 0.50,  2, 17, 0.10, 0.06, 0.06),
    "수수꽃다리":   _legacy_shrub_species(0.00005,   2.64, 0.45,  5, 29, 0.25, 0.23, 0.23),
    "좀작살나무":   _legacy_shrub_species(0.0021,    2.65, 0.50,  7, 25, 0.24, 0.16, 0.16),
    "쥐똥나무":     _legacy_shrub_species(0.00019,   2.75, 0.50,  4, 35, 0.18, 0.21, 0.21),
    "흰말채나무":   _legacy_shrub_species(0.00027,   2.52, 0.50,  7, 52, 0.29, 0.26, 0.26),
}


# ----- 대상지 메타데이터와 호환되는 조회 함수 -----

def tree_species_for_env(environment: str) -> dict[str, SpeciesData]:
    """모든 대상지 유형에 동일한 검증 기본 레코드를 반환한다.

    ``environment`` 인수는 저장 파일과 호출 API의 호환성을 위해 유지된다.
    """
    del environment
    return {name: spec["default"] for name, spec in TREE_BASE.items()}


def shrub_species_for_env(environment: str) -> dict[str, SpeciesData]:
    """모든 대상지 유형에 동일한 관목 레코드를 반환한다."""
    del environment
    return dict(SHRUB_SPECIES)


def tree_names() -> list[str]:
    """교목 수종(기본명) 목록."""
    return list(TREE_BASE.keys())


def shrub_names() -> list[str]:
    return list(SHRUB_SPECIES.keys())


# 하위 호환 기본 export (환경 미지정 = 기본 환경). 기존 코드/검증 스크립트가 참조.
TREE_SPECIES = tree_species_for_env(DEFAULT_ENVIRONMENT)
TREE_NAMES = list(TREE_SPECIES.keys())
SHRUB_NAMES = list(SHRUB_SPECIES.keys())


def _load_from_bundled_json() -> None:
    """통합 species_data.json(또는 구 carbon1_species_data.json)으로
    TREE_BASE·SHRUB_SPECIES 를 덮어쓴다.

    파일 탐색 우선순위 (처음 발견된 파일을 사용):
      exe 실행 시 — ① exe 옆 디렉터리 (사용자 업데이트) → ② sys._MEIPASS (번들 기본값)
      개발 모드   — ③ 프로젝트 루트
    각 디렉터리 안에서는 통합본(species_data.json) 을 우선하고,
    없으면 구버전(carbon1_species_data.json) 을 사용한다.
    JSON 파싱 실패 시 기존 Python 상수를 그대로 유지한다.
    """
    import json as _json
    import pathlib as _pl
    import sys as _sys

    _meipass = getattr(_sys, '_MEIPASS', None)
    if _meipass:
        _candidates = [_pl.Path(_sys.executable).parent, _pl.Path(_meipass)]
    else:
        _candidates = [_pl.Path(__file__).resolve().parent.parent]

    _json_path = next(
        (_b / _fn
         for _b in _candidates
         for _fn in ('species_data.json', 'carbon1_species_data.json')
         if (_b / _fn).exists()),
        None,
    )
    if _json_path is None:
        return

    try:
        _raw = _json.loads(_json_path.read_text(encoding='utf-8'))
    except Exception:
        return

    # 영문 표기(SPECIES_EN·ENVIRONMENTS_EN)도 같은 JSON 에서 가져온다 —
    # Equation Library Manager로 새 수종을 넣으면 학명도 함께 갱신되도록.
    from .i18n import load_json_overrides as _load_i18n_overrides
    _load_i18n_overrides(_raw)

    global TREE_BASE, SHRUB_SPECIES, TREE_SPECIES, TREE_NAMES, SHRUB_NAMES

    _new_tree: dict = {}
    for _name, _entry in _raw.get('TREE_BASE', {}).items():
        if isinstance(_entry, dict) and 'default' in _entry:
            _sd = SpeciesData(*_entry['default'])
            _new_tree[_name] = _env_species(_sd)
        elif isinstance(_entry, list):
            _new_tree[_name] = _env_species(SpeciesData(*_entry))

    _schema = _raw.get('_schema') if isinstance(_raw.get('_schema'), dict) else {}
    _shrub_equation_unit = _schema.get('SHRUB_SPECIES_equation_diameter_unit', 'mm')
    if _shrub_equation_unit not in ('cm', 'mm'):
        _shrub_equation_unit = 'mm'

    _new_shrub: dict = {}
    for _name, _arr in _raw.get('SHRUB_SPECIES', {}).items():
        _new_shrub[_name] = SpeciesData(
            *_arr, equation_diameter_unit=_shrub_equation_unit,
        )

    if _new_tree:
        TREE_BASE = _new_tree
    if _new_shrub:
        SHRUB_SPECIES = _new_shrub

    TREE_SPECIES = tree_species_for_env(DEFAULT_ENVIRONMENT)
    TREE_NAMES = list(TREE_SPECIES.keys())
    SHRUB_NAMES = list(_new_shrub.keys()) if _new_shrub else SHRUB_NAMES


_load_from_bundled_json()
