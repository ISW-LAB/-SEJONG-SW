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


@dataclass(frozen=True)
class SpeciesData:
    a: float            # allometric 회귀계수 a
    b: float            # allometric 회귀계수 b
    cf: float           # 탄소전환계수 (biomass kg → C kg)
    diameter_min: float
    diameter_max: float
    growth_y10: float   # 1~10년 성장률 (cm/yr)
    growth_y20: float   # 11~20년 성장률 (cm/yr)
    growth_y21: float   # 21년 이후 성장률 (cm/yr)

    def growth_at_year(self, year: int) -> float:
        if year <= 10:
            return self.growth_y10
        if year <= 20:
            return self.growth_y20
        return self.growth_y21


# 복원 환경(유형) — 지역 추가 시 선택. 교목 계수/성장차를 이 환경에 따라 매핑한다.
RESTORATION_ENVIRONMENTS = (
    "산불피해지 자연복원",
    "산불피해지 인공복원",
    "채석장 인공복원",
)
DEFAULT_ENVIRONMENT = RESTORATION_ENVIRONMENTS[0]


def _env_species(default: SpeciesData, by_env: dict | None = None) -> dict:
    """기본 계수 + 환경별 오버라이드를 담는 항목. by_env 에 없는 환경은 default 사용."""
    return {"default": default, "by_env": by_env or {}}


# 교목 (Tree) — **수종(기본명)** → 환경별 계수 매핑.
# 현재 환경별(복원 유형) 계수는 소나무(3개 환경)·신갈나무(자연복원)만 보유하며,
# 나머지 교목은 환경 무관 단일 계수(default)를 모든 환경에서 사용한다.
# 추후 다른 교목에 환경별 계수/성장차가 확정되면 해당 수종의 by_env 에 항목만 추가하면 된다.
# 라벨/계수/범위 출처: 「기초 DB 자료」 시트 순번 1, 2, 3, 4, 5, 6, 7, 8, 9
TREE_BASE: dict[str, dict] = {
    "소나무": _env_species(
        # 환경 미지정 시 기본값 = 산불피해지 자연복원
        default=SpeciesData(0.0737, 2.5735, 0.5, 1, 15, 0.11, 0.20, 0.70),
        by_env={
            "산불피해지 자연복원": SpeciesData(0.0737, 2.5735, 0.5, 1, 15, 0.11, 0.20, 0.70),
            "산불피해지 인공복원": SpeciesData(0.0722, 2.6044, 0.5, 1, 22, 0.11, 0.20, 1.00),
            # 순번 3 (Excel) — 성장차는 Excel/MATLAB 미수록 → 인공복원 값 차용(그래프용)
            "채석장 인공복원":     SpeciesData(0.1323, 2.2619, 0.5, 1, 25, 0.11, 0.20, 1.00),
        },
    ),
    "곰솔":       _env_species(SpeciesData(0.0679, 2.5770, 0.5, 1, 29, 0.24, 0.32, 0.32)),
    "편백":       _env_species(SpeciesData(0.3617, 2.0450, 0.5, 1, 50, 0.11, 0.23, 0.23)),
    "졸참나무":   _env_species(SpeciesData(0.2002, 2.3767, 0.5, 1, 30, 0.13, 0.30, 0.30)),
    "아까시나무": _env_species(SpeciesData(0.1391, 2.5016, 0.5, 1, 30, 0.14, 0.20, 0.20)),
    "붉가시나무": _env_species(SpeciesData(0.1926, 2.4300, 0.5, 1, 40, 0.12, 0.16, 0.16)),
    # 신갈나무: 현재 '산불피해지 자연복원'만 환경별 계수를 보유. 나머지 환경(인공복원/채석장)은
    # default(현재 자연복원과 동일)로 폴백한다. 추후 default 를 자연복원과 다르게 바꾸면
    # 인공/채석장 환경의 신갈나무 값이 바뀌므로 주의(필요 시 by_env 에 해당 환경을 추가).
    "신갈나무": _env_species(
        default=SpeciesData(0.0147, 3.1075, 0.5, 6, 30, 0.40, 0.40, 0.40),
        by_env={
            "산불피해지 자연복원": SpeciesData(0.0147, 3.1075, 0.5, 6, 30, 0.40, 0.40, 0.40),
        },
    ),
}

# 관목 (Shrub, 15종) - 직경 단위 mm (RCD)
# 라벨/계수/범위 출처: 「기초 DB 자료」 시트 순번 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 23, 21, 22, 24
SHRUB_SPECIES: dict[str, SpeciesData] = {
    "사철나무":     SpeciesData(0.0002,    2.50, 0.50,  6, 53, 0.30, 0.22, 0.22),
    "산철쭉":       SpeciesData(0.0003,    2.40, 0.50,  1, 22, 0.31, 0.17, 0.17),
    "조팝나무":     SpeciesData(0.00025,   2.60, 0.50,  5, 44, 0.20, 0.14, 0.14),
    # 순번 13 (Excel a=0.000022; MATLAB 원본 0.00022 의 1/10 — 회양목과 동일 패턴, Excel 채택)
    # 성장률은 MATLAB 원본 위치매칭값(0.38/0.25/0.25) 사용
    "화살나무":     SpeciesData(0.000022,  2.55, 0.50, 11, 67, 0.38, 0.25, 0.25),
    "회양목":       SpeciesData(0.000018,  2.70, 0.50,  8, 30, 0.24, 0.17, 0.17),
    "개나리":       SpeciesData(0.00028,   2.45, 0.50,  4, 26, 0.16, 0.16, 0.16),
    "남천":         SpeciesData(0.00031,   2.30, 0.50,  4, 35, 0.24, 0.22, 0.22),
    "덜꿩나무":     SpeciesData(0.00026,   2.50, 0.50,  7, 39, 0.35, 0.00, 0.00),
    "말발도리":     SpeciesData(0.00023,   2.60, 0.50,  4, 25, 0.30, 0.00, 0.00),
    "병꽃나무":     SpeciesData(0.00029,   2.40, 0.50,  6, 39, 0.30, 0.24, 0.24),
    "싸리":         SpeciesData(0.00015,   2.80, 0.50,  2, 17, 0.10, 0.06, 0.06),
    "수수꽃다리":   SpeciesData(0.00005,   2.64, 0.45,  5, 29, 0.25, 0.23, 0.23),
    "좀작살나무":   SpeciesData(0.0021,    2.65, 0.50,  7, 25, 0.24, 0.16, 0.16),
    "쥐똥나무":     SpeciesData(0.00019,   2.75, 0.50,  4, 35, 0.18, 0.21, 0.21),
    "흰말채나무":   SpeciesData(0.00027,   2.52, 0.50,  7, 52, 0.29, 0.26, 0.26),
}


# ----- 환경(복원 유형) 기반 조회 함수 -----

def tree_species_for_env(environment: str) -> dict[str, SpeciesData]:
    """주어진 환경에 맞는 {수종명: SpeciesData} 반환. 환경별 데이터가 없으면 default."""
    return {
        name: spec["by_env"].get(environment, spec["default"])
        for name, spec in TREE_BASE.items()
    }


def shrub_species_for_env(environment: str) -> dict[str, SpeciesData]:
    """관목은 현재 환경 무관(단일 계수). 추후 환경별 추가 시 이 함수만 확장하면 된다."""
    return dict(SHRUB_SPECIES)


def tree_names() -> list[str]:
    """교목 수종(기본명) 목록 — 환경과 무관(계수만 환경별로 달라짐)."""
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
    # 수종데이터업데이터로 새 수종을 넣으면 학명도 함께 갱신되도록.
    from .i18n import load_json_overrides as _load_i18n_overrides
    _load_i18n_overrides(_raw)

    global TREE_BASE, SHRUB_SPECIES, TREE_SPECIES, TREE_NAMES, SHRUB_NAMES

    _new_tree: dict = {}
    for _name, _entry in _raw.get('TREE_BASE', {}).items():
        if isinstance(_entry, dict) and 'default' in _entry:
            _sd = SpeciesData(*_entry['default'])
            _by_env = {_env: SpeciesData(*_arr) for _env, _arr in _entry.get('by_env', {}).items()}
            _new_tree[_name] = _env_species(_sd, _by_env)
        elif isinstance(_entry, list):
            _new_tree[_name] = _env_species(SpeciesData(*_entry))

    _new_shrub: dict = {}
    for _name, _arr in _raw.get('SHRUB_SPECIES', {}).items():
        _new_shrub[_name] = SpeciesData(*_arr)

    if _new_tree:
        TREE_BASE = _new_tree
    if _new_shrub:
        SHRUB_SPECIES = _new_shrub

    TREE_SPECIES = tree_species_for_env(DEFAULT_ENVIRONMENT)
    TREE_NAMES = list(TREE_SPECIES.keys())
    SHRUB_NAMES = list(_new_shrub.keys()) if _new_shrub else SHRUB_NAMES


_load_from_bundled_json()
