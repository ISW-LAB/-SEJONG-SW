# -*- coding: utf-8 -*-
"""
Carbon2 (국내·국외 통합 모듈) 수종 데이터.

원본: Carbon2_251013_1.mlapp / Carbon2_matlab_code.txt
- DomesticDataMap, DomesticRangeMap → DOMESTIC_SPECIES
- ForeignDataMap,  ForeignRangeMap  → FOREIGN_SPECIES

각 항목은 (equation 문자열, range) 보유.
원본 MATLAB 의 동적 평가 방식을 그대로 유지하기 위해 equation 은
문자열로 저장하고 `equation_eval.evaluate` 에서 평가한다.

라벨/식/범위 출처: 「기초 DB 자료」 시트 순번 25~39, 42~60, 68, 44 등.

원본 MATLAB 의 mojibake 한글 키는 `상대생장식 자료_최종본.xlsx` 의 동일 식·범위
항목과 매칭하여 정상 한글로 복원하였다 (Ver. 1.0 - Carbon2 Python).
"""
from __future__ import annotations

from dataclasses import dataclass


# 탄소전환계수 (Carbon2 원본 코드에서는 0.5로 하드코딩됨)
CARBON_FACTOR = 0.5


@dataclass(frozen=True)
class EquationSpecies:
    equation: str               # 식 문자열. 첫 변수=X, 두 번째 변수(다변수 식)=H
                                # 예) "Y=0.063*X^2.578", "ln(Y)=2.43*ln(X)-2.28",
                                #     "Y=exp(-4.7483+1.7395*ln(X*H))" (다변수)
    diameter_min: float | None  # None 이면 범위 검사 안 함
    diameter_max: float | None
    var1_label: str = "DBH (cm)"     # 첫 번째 입력 변수(X) 라벨
    var2_label: str | None = None    # 두 번째 입력 변수(H) 라벨. None 이면 단일변수
    var2_min: float = 0.0            # 두 번째 변수 입력 범위/기본값
    var2_max: float = 100.0
    var2_default: float = 10.0

    @property
    def has_range(self) -> bool:
        return self.diameter_min is not None and self.diameter_max is not None

    @property
    def is_multivar(self) -> bool:
        """두 번째 변수(H) 입력이 필요한 다변수 식인지."""
        return self.var2_label is not None


# ─────────────────────────── 국내 수종 (30종) ───────────────────────────────
# 출처: 「기초 DB 자료」 순번 44~60, 68 (기존 18) + 61,62,63,64,65,66,67,69,70,71,75,76 (추가 12)
DOMESTIC_SPECIES: dict[str, EquationSpecies] = {
    # 1. 후박나무 (Machilus thunbergii) - 국내, 지상부 - 서은경 등 (2017)
    "후박나무(지상부)":   EquationSpecies("ln(Y)=ln(2.20)+2.32*ln(X)", None, None),
    # 2. 백합나무 (Liriodendron tulipifera) - 국내, 전체 - 강민선 등 (2016)
    "백합나무(전체)":     EquationSpecies("Y=0.063*X^2.578", None, None),
    # 3. 종가시나무 (Quercus glauca) - 국립산림과학원 (2014)
    "종가시나무(전체)":   EquationSpecies(
        "Y=(0.021*X^2.763)+(0.072*X^2.368)+(0.071*X^1.776)+(0.128*X^2.014)", 6, 30),
    # 4. 리기다소나무 (Pinus rigida)
    "리기다소나무(전체)": EquationSpecies(
        "Y=(0.220*X^2.116)+(0.004*X^2.814)+(0.035*X^1.743)+(0.063*X^2.285)", 6, 40),
    # 5. 잣나무 (Pinus koraiensis)
    "잣나무(전체)":       EquationSpecies(
        "Y=(0.064*X^2.377)+(0.621*X^1.395)+(0.025*X^2.237)+(0.056*X^2.175)", 6, 40),
    # 6. 일본잎갈나무 (Larix kaempferi) - CSV: X^2.888 (MATLAB 원본 X^2.88 - 마지막 자리 누락 추정)
    "일본잎갈나무(전체)": EquationSpecies(
        "Y=(0.016*X^2.888)+(0.005*X^2.774)+(0.215*X^1.864)+(0.009*X^2.806)", 6, 50),
    # 7. 삼나무 (Cryptomeria japonica)
    "삼나무(전체)":       EquationSpecies(
        "Y=(0.042*X^2.533)+(0.621*X^2.774)+(0.330*X^1.257)+(0.080*X^1.949)", 6, 50),
    # 8. 상수리나무 (Quercus acutissima)
    "상수리나무(전체)":   EquationSpecies(
        "Y=(0.051*X^2.724)+(0.012*X^2.854)+(0.006*X^2.478)+(0.460*X^1.669)", 6, 30),
    # 9. 굴참나무 (Quercus variabilis)
    "굴참나무(전체)":     EquationSpecies(
        "Y=(0.186*X^2.184)+(0.035*X^2.293)+(0.061*X^1.454)+(0.077*X^2.199)", 6, 50),
    # 10. 자작나무 (Betula pendula)
    "자작나무(전체)":     EquationSpecies(
        "Y=(0.076*X^2.503)+(0.023*X^2.387)+(0.039*X^1.688)+(0.009*X^2.916)", 6, 40),
    # 11. 서어나무 (Carpinus laxiflora)
    "서어나무(전체)":     EquationSpecies(
        "Y=(0.255*X^2.001)+(0.005*X^3.167)+(0.000007*X^4.413)+(0.008*X^2.847)", 6, 30),
    # 12. 밤나무 (Castanea crenata)
    "밤나무(전체)":       EquationSpecies(
        "Y=(0.0003*X^4.217)+(0.010*X^3.006)+(0.261*X^1.199)+(0.130*X^2.159)", 6, 30),
    # 13. 현사시나무 (Populus alba x glandulosa)
    "현사시나무(전체)":   EquationSpecies(
        "Y=(0.078*X^2.409)+(0.00004*X^4.237)+(0.0008*X^2.647)+(0.006*X^2.707)", 6, 40),
    # 14. 구실잣밤나무 (Castanopsis cuspidata)
    "구실잣밤나무(전체)": EquationSpecies(
        "Y=(0.223*X^2.092)+(0.004*X^3.050)+(0.009*X^2.317)+(0.017*X^2.883)", 6, 30),
    # 15. 동백나무 (Camellia japonica)
    "동백나무(전체)":     EquationSpecies(
        "Y=(0.034*X^2.475)+(0.002*X^3.738)+(0.036*X^1.995)+(0.004*X^3.331)", 6, 25),
    # 16. 메타세쿼이아 (Metasequoia glyptostroboides) - 정준영 등 (2023)
    "메타세쿼이아(전체)": EquationSpecies("Y=0.787*X^0.551", 15, 30),
    # 17. 양버즘나무 (Platanus occidentalis) - 정준영 등 (2023)
    "양버즘나무(전체)":   EquationSpecies("Y=0.215*X^0.756", 16, 35),
    # 18. 단풍나무 (Acer palmatum) - (석사) 김호진 (2023)
    # 원본 MATLAB 범위 [13,26] (CSV의 6~19와 다름 — MATLAB 원본 값 유지)
    "단풍나무(전체)":     EquationSpecies("ln(Y)=2.3864+2.0950*ln(X)", 13, 26),

    # ───── 추가 (Excel 순번 61,62,64,65,66,69,70,71 — 단일변수) ─────
    # 19. 잣나무 (국내, 지상부) - 김성용 등 (2015) - 순번 61
    "잣나무(지상부)":           EquationSpecies("ln(Y)=-4.6774+2.8073*ln(X)", 6, 39),
    # 20. 종가시나무 (국내, 전체, 경남) - 정현모 등 (2014) - 순번 62
    #     Excel: Y=e(2.4042ln(X)-1.3045)+e(...)+... → e(z)=exp(z)
    "종가시나무(전체, 경남)":   EquationSpecies(
        "Y=exp(2.4042*ln(X)-1.3045)+exp(2.6434*ln(X)-1.6232)"
        "+exp(1.5428*ln(X)-1.3692)+exp(2.3324*ln(X)-0.9181)", 1, 25),
    # 21. 곰솔 (국내, 전체, 해안방재림) - 김성용 등 (2014) - 순번 64
    "곰솔(전체, 해안방재림)":   EquationSpecies("ln(Y)=-1.4631+2.1687*ln(X)", 11, 30),
    # 22. 곰솔 (국내, 지상부, 경남) - 김춘식 등 (2013) - 순번 65
    "곰솔(지상부, 경남)":       EquationSpecies("ln(Y)=-0.8555+2.3386*ln(X)", 0, 50),
    # 23. 곰솔 (국내, 전체, 여수) - 박인협 & 김소담 (2018) - 순번 66
    "곰솔(전체, 여수)":         EquationSpecies("Y=67.863*X^2.577", 7, 29),
    # 24. 붉가시나무 (국내, 전체, 전남) - (석사)김현준 (2011) - 순번 69
    "붉가시나무(전체, 전남)":   EquationSpecies("Y=0.0827*X^2.4689", 4, 24),
    # 25. 삼나무 (국내, 지상부, 경남) - (석사)권정화 (2015) - 순번 70
    "삼나무(지상부, 경남)":     EquationSpecies("ln(Y)=-0.3972+1.9041*ln(X)", 23, 36),
    # 26. 밤나무 (국내, 전체, 전남) - (석사)박종원 (2015) - 순번 71 (변수: RCD cm)
    "밤나무(전체, 전남)":       EquationSpecies("Y=327.9*X^2.159", 7, 27, var1_label="RCD (cm)"),
    # 27. 신갈나무 (국내, 전체) - 권기철 & 이돈구 (2006) - 순번 67
    #     Excel 식 자체는 X(=DBH) 단일 변수: Y=e(0.992ln(X)+1.469)+e(0.808ln(X)+1.527)
    #     (변수 라벨 'DBH2H' 는 출처 표기일 뿐, 식에는 X 만 등장 → 단일변수로 처리)
    "신갈나무(전체)":           EquationSpecies(
        "Y=exp(0.992*ln(X)+1.469)+exp(0.808*ln(X)+1.527)", 11, 22),

    # ───── 추가 (다변수 — 2개 입력 필요) ─────
    # 28. 잣나무 (국내, 지상부, 밀도, 경기도) - 류다운 등 (2014) - 순번 63
    #     Excel: ln(Y)=0.903ln(density)+2.0973ln(X)-3.323  (X=DBH, H=임분밀도)
    "잣나무(지상부, 밀도)":     EquationSpecies(
        "ln(Y)=0.903*ln(H)+2.0973*ln(X)-3.323", 15, 46,
        var2_label="임분밀도 (본/ha)", var2_min=1, var2_max=100000, var2_default=1000),
    # 29. 선버들 (국내, 지상부) - 조형진 등 (2017) - 순번 75  (변수: DBH², H)
    "선버들(지상부)":           EquationSpecies(
        "Y=exp(-0.3945+0.4348*ln(X**2*H))+exp(-0.5642+0.4344*ln(X**2*H))"
        "+exp(-1.2941+0.4537*ln(X**2*H))", None, None,
        var2_label="수고 H (m)", var2_min=0, var2_max=60, var2_default=10),
    # 30. 왕버들 (국내, 지상부) - 조형진 등 (2017) - 순번 76  (변수: DBH², H)
    "왕버들(지상부)":           EquationSpecies(
        "Y=exp(-1.153+0.9583*ln(X**2*H))+exp(-1.054+0.9689*ln(X**2*H))"
        "+exp(-0.9722+0.3737*ln(X**2*H))", None, None,
        var2_label="수고 H (m)", var2_min=0, var2_max=60, var2_default=10),
}


# ─────────────────────────── 국외 수종 (26종) ───────────────────────────────
# 출처: 「기초 DB 자료」 순번 25~39, 42, 43 + Position 8 (기존 18)
#       + 40,41 (단일변수 추가) + 73,74,77,78,80,81 (다변수 추가)
FOREIGN_SPECIES: dict[str, EquationSpecies] = {
    # 1. 사할린전나무 Abies sachalinensis (Takagi et al. 2010) - 순번 25
    "사할린전나무(지상부)":   EquationSpecies("ln(Y)=2.43*ln(X)-2.28", None, None),
    # 2. 아프리카향나무 Juniperus procera (Worku et al. 2015) - 순번 26
    # [수정] 원본 MATLAB/Excel 의 "Y=ln(-2.31)+2.32*ln(X)" 는 ln(음수) → math domain error.
    #        올바른 로그-로그 상대생장식 "ln(Y)=-2.31+2.32*ln(X)" 로 정정
    #        (절편 -2.31, 기울기 2.32; 독일가문비/가문비 등과 동일한 ln(Y)=a+b*ln(X) 형식).
    "아프리카향나무(전체)":   EquationSpecies("ln(Y)=-2.31+2.32*ln(X)", 30, 100),
    # 3. 까치박달 Carpinus cordata (Vahei et al. 2014) - 순번 27
    "까치박달(전체)":         EquationSpecies("ln(Y)=2.302*ln(X)-2.235", None, None),
    # 4. 미국너도밤나무 Fagus grandifolia (Zianis & Mencuccini 2003) - 순번 28
    "미국너도밤나무(지상부)": EquationSpecies("Y=0.20*X^2.30", 3, 66),
    # 5. 인도월계수 Cinnamomum tamala (Poudel et al. 2013) - 순번 29
    "인도월계수(지상부)":     EquationSpecies("Y=1.623*exp(0.478*X)", None, None),
    # 6. 차나무 Camellia sinensis (Rathnayaka et al. 2024) - 순번 30
    "차나무(전체)":           EquationSpecies("Y=164.5*X", None, None),
    # 7. 사스레피나무 Eurya japonica (Chen et al. 2017) - 순번 31
    "사스레피나무(지상부)":   EquationSpecies("ln(Y)=1.266*ln(X^2)-1.852", None, None),
    # 8. (CSV 미발견 - 원본 MATLAB 식 유지) - 팥배나무류 추정
    "팥배나무(지상부)":       EquationSpecies("Y=0.168*X^2.47", None, None),
    # 9. 마가목 Sorbus aucuparia (Pol et al. 2018) - 순번 32
    "마가목(지상부)":         EquationSpecies("Y=0.164*X^2.041", 0, 50),
    # 10. 국수나무 Stephanandra incisa (Seo et al. 2017) - 순번 33
    "국수나무(지상부)":       EquationSpecies("ln(Y)=ln(2.27)+2.26*ln(X)", None, None),
    # 11. 산동백나무 Mallotus paniculatus (Feng et al. 2005) - 순번 34
    "산동백나무(지상부)":     EquationSpecies("Y=26.475*X^0.055", None, None),
    # 12. 박달목서 Daphniphyllum himalense (Poudel et al. 2020) - 순번 35
    "박달목서(지상부)":       EquationSpecies("Y=0.08234*X^1.59396", None, None),
    # 13. 피나무 Tilia amurensis (He et al. 2020) - 순번 36
    "피나무(전체)":           EquationSpecies("ln(Y)=2.459*ln(X)-2.535", None, None),
    # 14. 산수유 Cornus officinalis (Kim et al. 2025) - 순번 37
    "산수유(전체)":           EquationSpecies("Y=0.04*X^2.41", None, None),
    # 15. 노린재나무 Symplocos paniculata (Xie et al. 2017) - 순번 38
    "노린재나무(전체)":       EquationSpecies("Y=0.05*X^0.94", None, None),
    # 16. 구주소나무 Pinus sylvestris (Ovington et al. 1959) - 순번 39
    "구주소나무(전체)":       EquationSpecies("ln(Y)=2.6*ln(X)-1.61", None, None),
    # 17. 독일가문비나무 Picea abies (Zianis et al. 2005) - 순번 42
    "독일가문비나무(전체)":   EquationSpecies("ln(Y)=-3.084+2.814*ln(X)", None, None),
    # 18. 가문비나무 Picea mariana (Ouellet et al. 1983) - 순번 43
    "가문비나무(전체)":       EquationSpecies("ln(Y)=-1.784+3.3271*ln(X)", None, None),

    # ───── 추가 (Excel 순번 40,41 — 단일변수) ─────
    # 19. 포플러 (국외, 전체) - Rock (2007) - 순번 40
    "포플러(전체)":           EquationSpecies("Y=0.0519*X^2.545", 13, 33),
    # 20. 비술나무 (국외, 지상부) - Alesso et al. (2021) - 순번 41
    "비술나무(지상부)":       EquationSpecies("Y=0.065*X^2.612", 1, 14),
    # 21. 모밀잣밤나무 Castanopsis indica (Phandari & Neupane 2014) - 순번 78
    #     Excel 식 자체는 X 단일 변수: Y=52.28*X^0.89
    #     (변수 라벨 'RCD2H' 는 출처 표기. 식에 X 만 등장 → 단일변수로 처리)
    "모밀잣밤나무(전체)":     EquationSpecies("Y=52.28*X^0.89", 0.8, 2.7, var1_label="RCD (cm)"),

    # ───── 추가 (다변수 — 2개 입력 필요) ─────
    # 22. 멕시코수양소나무 Pinus patula (Martinez-Domninguez 2020) - 순번 73 (DBH, H)
    #     Excel: Y=e^(-4.7483+1.7395ln(X1·X2))  (X1=DBH, X2=H)
    "멕시코수양소나무(전체)":  EquationSpecies(
        "Y=exp(-4.7483+1.7395*ln(X*H))", 5, 25,
        var2_label="수고 H (m)", var2_min=0, var2_max=60, var2_default=10),
    # 23. 굴피나무 Platycarya strobilacea (Liu et al. 2016) - 순번 74 (DBH, H; X1²·X2)
    "굴피나무(지상부)":       EquationSpecies(
        "Y=1.9611*(X**2*H)**0.8921", None, None,
        var2_label="수고 H (m)", var2_min=0, var2_max=60, var2_default=10),
    # 24. 서양개암나무 Corylus avellana (Pajtik et al. 2025) - 순번 77 (h, LAI)
    #     Excel: Y=e^(-0.858+0.604·X1+0.850·X2)  (X1=수고 h, X2=LAI)
    "서양개암나무(지상부)":   EquationSpecies(
        "Y=exp(-0.858+0.604*X+0.850*H)", None, None,
        var1_label="수고 h (m)", var2_label="엽면적지수 LAI",
        var2_min=0, var2_max=15, var2_default=2),
    # 25. 개옻나무 Toxicodendron trichocarpum (Osada et al. 2006) - 순번 80 (DBH, L; X1²·X2)
    "개옻나무(지상부)":       EquationSpecies(
        "Y=0.336*(X**2*H)**0.928", 0.18, 1.73,
        var2_label="길이 L (m)", var2_min=0, var2_max=10, var2_default=1),
    # 26. 모감주나무 Koelreuteria paniculata (He et al. 2025) - 순번 81 (DBH²H)
    "모감주나무(지상부)":     EquationSpecies(
        "Y=0.0545*(X**2*H)**0.8630+0.0155*(X**2*H)**0.8737"
        "+0.0145*(X**2*H)**0.7444+0.0307*(X**2*H)**0.8270", 28, 41,
        var2_label="수고 H (m)", var2_min=0, var2_max=60, var2_default=10),
}


DOMESTIC_NAMES = list(DOMESTIC_SPECIES.keys())
FOREIGN_NAMES = list(FOREIGN_SPECIES.keys())


def _load_from_bundled_json() -> None:
    """통합 species_data.json(또는 구 carbon2_species_data.json)으로
    DOMESTIC_SPECIES·FOREIGN_SPECIES 를 덮어쓴다.

    파일 탐색 우선순위 (처음 발견된 파일을 사용):
      exe 실행 시 — ① exe 옆 디렉터리 (사용자 업데이트) → ② sys._MEIPASS (번들 기본값)
      개발 모드   — ③ 프로젝트 루트
    각 디렉터리 안에서는 통합본(species_data.json) 을 우선하고,
    없으면 구버전(carbon2_species_data.json) 을 사용한다.
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
         for _fn in ('species_data.json', 'carbon2_species_data.json')
         if (_b / _fn).exists()),
        None,
    )
    if _json_path is None:
        return

    try:
        _raw = _json.loads(_json_path.read_text(encoding='utf-8'))
    except Exception:
        return

    global DOMESTIC_SPECIES, FOREIGN_SPECIES, DOMESTIC_NAMES, FOREIGN_NAMES

    def _parse(entry: dict) -> EquationSpecies:
        _rng = entry.get('range') or [None, None]
        _v2 = entry.get('var2')
        return EquationSpecies(
            equation=entry['equation'],
            diameter_min=_rng[0],
            diameter_max=_rng[1],
            var1_label=entry.get('var1', 'DBH (cm)'),
            var2_label=_v2['label'] if _v2 else None,
            var2_min=float(_v2['min']) if _v2 else 0.0,
            var2_max=float(_v2['max']) if _v2 else 100.0,
            var2_default=float(_v2['default']) if _v2 else 10.0,
        )

    _new_dom = {_n: _parse(_e) for _n, _e in _raw.get('DOMESTIC_SPECIES', {}).items()}
    _new_for = {_n: _parse(_e) for _n, _e in _raw.get('FOREIGN_SPECIES', {}).items()}

    if _new_dom:
        DOMESTIC_SPECIES = _new_dom
        DOMESTIC_NAMES = list(_new_dom.keys())
    if _new_for:
        FOREIGN_SPECIES = _new_for
        FOREIGN_NAMES = list(_new_for.keys())


_load_from_bundled_json()


def species_map(origin: str) -> dict[str, EquationSpecies]:
    """origin: 'domestic' 또는 'foreign'."""
    if origin == "domestic":
        return DOMESTIC_SPECIES
    if origin == "foreign":
        return FOREIGN_SPECIES
    raise ValueError(f"origin must be 'domestic' or 'foreign', got {origin!r}")


def species_names(origin: str) -> list[str]:
    return DOMESTIC_NAMES if origin == "domestic" else FOREIGN_NAMES
