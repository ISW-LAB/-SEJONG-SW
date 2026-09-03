# -*- coding: utf-8 -*-
"""한국어/영어 표시 전환 계층.

- 번역 키는 **한글 원문 그대로**다. `tr("계 산")` 처럼 감싸면 영문 모드에서
  `translations.EN` 의 대응 문자열로 바뀌고, 한국어 모드에서는 원문을 그대로 돌려준다.
  대응 항목이 없으면 원문을 반환하므로 누락돼도 화면이 깨지지 않는다.
- 수종명은 `species_name()` 이 학명으로 바꾼다(SCI 논문 표기 기준: 학명 단독).
- 선택한 언어는 QSettings 에 저장되어 다음 실행에 그대로 적용된다.

계산 로직·데이터 키는 항상 한글 원문을 사용한다. 이 모듈은 **표시 계층 전용**이며,
dict 키나 계산 입력을 바꾸지 않는다.
"""
from __future__ import annotations

import re

from .species_names_en import ENVIRONMENT_EN, QUALIFIER_EN, SCIENTIFIC_NAMES
from .translations import EN

LANG_KO = "ko"
LANG_EN = "en"
LANGUAGE_LABELS = {LANG_KO: "한국어", LANG_EN: "English"}

_ORG = "SejongArboretum"
_APP = "CarbonStorageModule"
_KEY = "language"

_current = LANG_KO

# species_data.json 이 제공하는 확장 매핑 (있으면 내장 표보다 우선)
_json_species: dict[str, str] = {}
_json_environments: dict[str, str] = {}


# ─────────────────────────── 언어 상태 ───────────────────────────

def get_language() -> str:
    return _current


def is_english() -> bool:
    return _current == LANG_EN


def set_language(code: str) -> None:
    """현재 언어를 바꾼다(저장하지 않음). 잘못된 값은 무시하고 한국어를 유지한다."""
    global _current
    _current = LANG_EN if code == LANG_EN else LANG_KO


def load_saved_language() -> str | None:
    """이전 실행에서 저장한 언어. 저장된 적이 없으면 None."""
    try:
        from PyQt5.QtCore import QSettings
        value = QSettings(_ORG, _APP).value(_KEY)
    except Exception:
        return None
    if isinstance(value, str) and value in (LANG_KO, LANG_EN):
        return value
    return None


def save_language(code: str) -> None:
    try:
        from PyQt5.QtCore import QSettings
        settings = QSettings(_ORG, _APP)
        settings.setValue(_KEY, LANG_EN if code == LANG_EN else LANG_KO)
        settings.sync()
    except Exception:
        pass


# ─────────────────────────── 문자열 번역 ───────────────────────────

def tr(text: str) -> str:
    """한글 원문을 현재 언어로. 대응 항목이 없으면 원문 그대로."""
    if _current == LANG_KO:
        return text
    return EN.get(text, text)


# ─────────────────────────── 수종·환경 이름 ───────────────────────────

_QUALIFIER_RE = re.compile(r"^\s*(?P<base>[^(]+?)\s*\((?P<qual>.*)\)\s*$")


def _translate_qualifier(qual: str) -> str:
    """'전체, 경남' → 'whole tree, Gyeongnam'. 모르는 항목은 원문 유지."""
    parts = [p.strip() for p in qual.split(",")]
    return ", ".join(QUALIFIER_EN.get(p, p) for p in parts if p)


def scientific_name(base_name: str) -> str | None:
    """꼬리표를 뗀 기본 수종명의 학명. 없으면 None."""
    return _json_species.get(base_name) or SCIENTIFIC_NAMES.get(base_name)


def species_name(name: str) -> str:
    """수종 표시명. 영문 모드에서 '후박나무(지상부)' → 'Machilus thunbergii (aboveground)'.

    학명을 모르는 수종은 국명을 그대로 남긴다(잘못된 학명을 지어내지 않는다).
    """
    if _current == LANG_KO or not name:
        return name

    direct = _json_species.get(name) or SCIENTIFIC_NAMES.get(name)
    if direct:
        return direct

    m = _QUALIFIER_RE.match(name)
    if not m:
        return name
    base = m.group("base")
    latin = scientific_name(base)
    if not latin:
        return name
    qual = _translate_qualifier(m.group("qual"))
    return f"{latin} ({qual})" if qual else latin


def environment_name(env: str) -> str:
    """복원 환경(유형) 표시명."""
    if _current == LANG_KO or not env:
        return env
    return _json_environments.get(env) or ENVIRONMENT_EN.get(env, env)


def species_sort_key(name: str) -> str:
    """현재 언어의 표시명 기준 정렬 키."""
    return species_name(name)


# ─────────────────────────── JSON 확장 매핑 ───────────────────────────

def load_json_overrides(raw: dict) -> None:
    """species_data.json 의 SPECIES_EN / ENVIRONMENTS_EN 을 반영한다.

    data.py 가 JSON 을 읽을 때 함께 호출된다. 형식이 어긋나면 조용히 무시한다.
    """
    global _json_species, _json_environments
    try:
        species = raw.get("SPECIES_EN") or {}
        environments = raw.get("ENVIRONMENTS_EN") or {}
        if isinstance(species, dict):
            _json_species = {k: v for k, v in species.items()
                             if isinstance(k, str) and isinstance(v, str) and v.strip()}
        if isinstance(environments, dict):
            _json_environments = {k: v for k, v in environments.items()
                                  if isinstance(k, str) and isinstance(v, str) and v.strip()}
    except Exception:
        pass


def missing_scientific_names(names) -> list[str]:
    """학명 매핑이 없는 수종 목록 — 데이터 갱신 시 누락 점검용."""
    missing = []
    for name in names:
        if _json_species.get(name) or SCIENTIFIC_NAMES.get(name):
            continue
        m = _QUALIFIER_RE.match(name)
        if m and scientific_name(m.group("base")):
            continue
        missing.append(name)
    return missing
