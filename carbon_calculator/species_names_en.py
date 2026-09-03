# -*- coding: utf-8 -*-
"""국명 → 학명(binomial) 매핑.

영문 모드에서 수종 라벨을 학명 단독으로 표기하기 위한 표. SCI 논문의 표·그림에
그대로 쓸 수 있도록 통용명 없이 속명+종소명만 둔다.

`species_data.json` 에 `SPECIES_EN` / `ENVIRONMENTS_EN` 섹션이 있으면 그 값이
이 표를 덮어쓴다(수종데이터업데이터로 새 수종을 넣을 때 코드 수정 없이 확장하기 위함).
`(지상부)`·`(전체, 경남)` 같은 꼬리표는 기본명과 분리해 QUALIFIER_EN 으로 번역한다.
"""
from __future__ import annotations

# 기본명(꼬리표를 뗀 수종명) → 학명
SCIENTIFIC_NAMES: dict[str, str] = {
    # ── 교목 (TREE_BASE) ──────────────────────────────────────────────
    "소나무": "Pinus densiflora",
    "곰솔": "Pinus thunbergii",
    "편백": "Chamaecyparis obtusa",
    "졸참나무": "Quercus serrata",
    "아까시나무": "Robinia pseudoacacia",
    "붉가시나무": "Quercus acuta",
    "신갈나무": "Quercus mongolica",

    # ── 관목 (SHRUB_SPECIES) ──────────────────────────────────────────
    "사철나무": "Euonymus japonicus",
    "산철쭉": "Rhododendron yedoense f. poukhanense",
    "조팝나무": "Spiraea prunifolia",
    "화살나무": "Euonymus alatus",
    "회양목": "Buxus sinica var. insularis",
    "개나리": "Forsythia koreana",
    "남천": "Nandina domestica",
    "덜꿩나무": "Viburnum erosum",
    "말발도리": "Deutzia parviflora",
    "병꽃나무": "Weigela subsessilis",
    "싸리": "Lespedeza bicolor",
    "수수꽃다리": "Syringa oblata var. dilatata",
    "좀작살나무": "Callicarpa dichotoma",
    "쥐똥나무": "Ligustrum obtusifolium",
    "흰말채나무": "Cornus alba",

    # ── 국내 수종 (DOMESTIC_SPECIES) ──────────────────────────────────
    "후박나무": "Machilus thunbergii",
    "백합나무": "Liriodendron tulipifera",
    "종가시나무": "Quercus glauca",
    "리기다소나무": "Pinus rigida",
    "잣나무": "Pinus koraiensis",
    "일본잎갈나무": "Larix kaempferi",
    "삼나무": "Cryptomeria japonica",
    "상수리나무": "Quercus acutissima",
    "굴참나무": "Quercus variabilis",
    "자작나무": "Betula pendula",
    "서어나무": "Carpinus laxiflora",
    "밤나무": "Castanea crenata",
    "현사시나무": "Populus tomentiglandulosa",
    "구실잣밤나무": "Castanopsis sieboldii",
    "동백나무": "Camellia japonica",
    "메타세쿼이아": "Metasequoia glyptostroboides",
    "양버즘나무": "Platanus occidentalis",
    "단풍나무": "Acer palmatum",
    "선버들": "Salix subfragilis",
    "왕버들": "Salix chaenomeloides",

    # ── 국외 수종 (FOREIGN_SPECIES) ───────────────────────────────────
    "사할린전나무": "Abies sachalinensis",
    "아프리카향나무": "Juniperus procera",
    "까치박달": "Carpinus cordata",
    "미국너도밤나무": "Fagus grandifolia",
    "인도월계수": "Cinnamomum tamala",
    "차나무": "Camellia sinensis",
    "사스레피나무": "Eurya japonica",
    "마가목": "Sorbus aucuparia",
    "국수나무": "Stephanandra incisa",
    "산동백나무": "Mallotus paniculatus",
    "박달목서": "Daphniphyllum himalense",
    "피나무": "Tilia amurensis",
    "산수유": "Cornus officinalis",
    "노린재나무": "Symplocos paniculata",
    "구주소나무": "Pinus sylvestris",
    "독일가문비나무": "Picea abies",
    "가문비나무": "Picea mariana",
    "포플러": "Populus tremula × P. tremuloides",
    "비술나무": "Ulmus pumila",
    "모밀잣밤나무": "Castanopsis indica",
    "멕시코수양소나무": "Pinus patula",
    "굴피나무": "Platycarya strobilacea",
    "서양개암나무": "Corylus avellana",
    "개옻나무": "Toxicodendron trichocarpum",
    "모감주나무": "Koelreuteria paniculata",
}

# 수종명 괄호 안 꼬리표 — 측정 부위 및 자료 출처 지역
QUALIFIER_EN: dict[str, str] = {
    "지상부": "aboveground",
    "전체": "whole tree",
    "경남": "Gyeongnam",
    "전남": "Jeonnam",
    "여수": "Yeosu",
    "해안방재림": "coastal windbreak forest",
    "밀도": "stand density",
    "경기도": "Gyeonggi-do",
}

# 복원 환경(유형)
ENVIRONMENT_EN: dict[str, str] = {
    "산불피해지 자연복원": "Post-fire site, natural restoration",
    "산불피해지 인공복원": "Post-fire site, artificial restoration",
    "채석장 인공복원": "Quarry site, artificial restoration",
}
