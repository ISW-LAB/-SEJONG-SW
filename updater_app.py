# -*- coding: utf-8 -*-
"""
수종 데이터 업데이터 (자체 완결형).

이 프로그램은 **탄소저장량측정모듈(main.py) 의 전체 코드 로직을 내부에 내장**하고
있어, 소스 폴더 없이 이 exe 하나만으로 새 수종 데이터(JSON)를 반영한 실행파일을
만들 수 있다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
동작 방식
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[① exe 재빌드 — 자체 완결]  통합 species_data.json 을 입력받아,
   내장된 소스(carbon_calculator + main.py + build_exe.py)를 임시 작업폴더로
   풀고 그 안에 JSON 을 넣은 뒤 PyInstaller 로 새 탄소저장량측정모듈.exe 를 빌드한다.
   → 소스 트리를 옆에 둘 필요 없음. (단, PC 에 Python 3.10+ 이 있어야 컴파일 가능)

[② JSON 적용 — Python 불필요]  기존 탄소저장량측정모듈.exe 옆에 JSON 을 복사만 한다.
   다음 실행 시 자동 반영. 재빌드가 필요 없을 때 가장 빠른 경로.

JSON 양식:  species_data.json (통합본 — 교목·관목·국내·국외 4개 섹션)

실행:
    python updater_app.py        (개발 모드)
    수종데이터업데이터.exe        (배포 모드 — 단독 실행)
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAbstractItemView, QSizePolicy, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

# ── 표시 언어 ────────────────────────────────────────────────────────────
# 이 앱은 소스 폴더 없이 단독 배포되므로 carbon_calculator 에 의존하지 않고
# 자체 대응표를 갖는다. 언어 설정은 본 프로그램(탄소저장량측정모듈)과 같은
# QSettings 키를 공유해 두 앱의 표시 언어가 함께 움직인다.
_SETTINGS_ORG = "SejongArboretum"
_SETTINGS_APP = "CarbonStorageModule"
_SETTINGS_KEY = "language"

_EN: dict[str, str] = {
    "수종 데이터 업데이터 (자체 완결형) — 탄소저장량 측정 모듈":
        "Species Data Updater (self-contained) — Carbon Storage Assessment Module",
    "수종 데이터 JSON (통합 species_data.json)":
        "Species data JSON (combined species_data.json)",
    "— 파일을 선택하면 검증됩니다": "— select a file to validate it",
    "파일을 찾을 수 없습니다.": "File not found.",
    "열기...": "Open...",
    "폴더...": "Folder...",
    "파일/폴더 경로를 선택하거나 직접 입력하세요":
        "Choose a file or folder, or type a path",
    "① exe 재빌드   —   내장 소스로 새 탄소저장량측정모듈.exe 생성 (권장)":
        "① Rebuild executable — build a new module executable from the bundled "
        "sources (recommended)",
    "이 업데이터에 내장된 전체 코드 로직을 사용해 JSON 이 반영된 새 exe 를 만듭니다. "
    "소스 폴더가 옆에 없어도 됩니다.\n"
    "※ 컴파일에는 이 PC 에 Python 3.10 이상이 필요합니다 (최초 1회 빌드 환경 자동 구성).":
        "Builds a new executable with the new JSON applied, using the complete source "
        "bundled inside this updater. No source folder is required alongside it.\n"
        "Note: compiling requires Python 3.10 or later on this machine (the build "
        "environment is created automatically on first use).",
    "출력 폴더 (exe 저장 위치)": "Output folder (where the executable is written)",
    "onedir 모드": "onedir mode",
    "디버그 콘솔": "Debug console",
    "UPX 압축": "UPX compression",
    "캐시 초기화": "Clear cache",
    "새 exe 빌드 (PyInstaller)": "Build new executable (PyInstaller)",
    "준비": "Ready",
    "빌드 중...": "Building...",
    "빌드 완료!": "Build complete",
    "빌드 실패 — 로그 확인": "Build failed — check the log",
    "먼저 species_data.json 을 선택하세요.": "Select species_data.json first.",
    "JSON 오류: {msg}": "JSON error: {msg}",
    "출력 폴더를 지정하세요.": "Specify an output folder.",
    "② JSON 적용   —   기존 exe 옆에 복사만 (Python 불필요)":
        "② Apply JSON — copy it next to an existing executable (no Python required)",
    "이미 만들어진 탄소저장량측정모듈.exe 가 있다면, 그 옆에 JSON 을 복사해 "
    "다음 실행 시 즉시 반영합니다. 재빌드가 필요 없을 때 사용하세요.":
        "If a built executable already exists, the JSON is copied next to it and takes "
        "effect the next time it runs. Use this when a rebuild is unnecessary.",
    "탄소저장량측정모듈.exe 위치": "Location of the module executable",
    "찾기...": "Browse...",
    "JSON 적용 (복사)": "Apply JSON (copy)",
    "완료 — JSON 복사됨": "Done — JSON copied",
    "JSON 검증에 실패했습니다 (상단 상태 확인).":
        "JSON validation failed (see the status above).",
    "탄소저장량측정모듈.exe 위치를 선택하세요.":
        "Select the location of the module executable.",
    "로그": "Log",
    "통합 species_data.json 선택": "Select the combined species_data.json",
    "JSON 파일 (*.json)": "JSON file (*.json)",
    "출력 폴더 선택": "Select output folder",
    "탄소저장량측정모듈.exe 선택": "Select the module executable",
    "실행 파일 (*.exe)": "Executable (*.exe)",
    # 검증 결과
    "JSON 파싱 오류: {error}": "JSON parse error: {error}",
    "유효한 수종 섹션이 없습니다. TREE_BASE / SHRUB_SPECIES / DOMESTIC_SPECIES / "
    "FOREIGN_SPECIES 중 하나 이상이 필요합니다.":
        "No valid species section found. At least one of TREE_BASE, SHRUB_SPECIES, "
        "DOMESTIC_SPECIES or FOREIGN_SPECIES is required.",
    "교목 {tree} · 관목 {shrub} · 국내 {dom} · 국외 {for_} 종":
        "{tree} trees · {shrub} shrubs · {dom} domestic · {for_} international species",
    # 빌드 워커
    "Python 인터프리터를 찾을 수 없습니다. Python 3.10+ 를 설치하세요.":
        "No Python interpreter found. Please install Python 3.10 or later.",
    "내장 소스를 찾을 수 없습니다: {path}\nupdater 를 build_updater.py 로 다시 빌드하세요.":
        "Bundled sources not found: {path}\nRebuild the updater with build_updater.py.",
    "[1/4] 작업폴더 준비: {path}": "[1/4] Preparing work folder: {path}",
    "[2/4] 수종 데이터 적용: {src} → {dst}":
        "[2/4] Applying species data: {src} → {dst}",
    "[3/4] 빌드 시작: {cmd}": "[3/4] Starting build: {cmd}",
    "      (최초 실행 시 빌드 전용 venv 생성으로 수 분 소요)":
        "      (the first run creates a dedicated build venv and takes a few minutes)",
    "PyInstaller 빌드가 실패했습니다. 위 로그를 확인하세요.":
        "The PyInstaller build failed. Check the log above.",
    "산출물을 찾을 수 없습니다: {path}": "Build output not found: {path}",
    "[4/4] 산출물 복사 → {path}": "[4/4] Copying build output → {path}",
    "[오류] {error}": "[Error] {error}",
    "[완료] 새 실행파일: {path}": "[Done] New executable: {path}",
    "[실패] {error}": "[Failed] {error}",
    "[완료] {name} → {path}": "[Done] {name} → {path}",
    "[정리] 구버전 JSON 제거: {names}": "[Cleanup] removed legacy JSON: {names}",
    "탄소저장량측정모듈.exe 를 다시 실행하면 새 수종 데이터가 적용됩니다.":
        "Restart the module executable to load the new species data.",
    # 언어 선택
    "언어 / Language": "Language",
    "한국어": "한국어",
    "English": "English",
    # ── 수종 데이터 편집기 ──
    "수종별 상대생장식 (JSON 미리보기 · 추가/수정/삭제)":
        "Growth equations by species (JSON preview · add / edit / delete)",
    "교목 (TREE_BASE)": "Trees (TREE_BASE)",
    "관목 (SHRUB_SPECIES)": "Shrubs (SHRUB_SPECIES)",
    "국내 수종 (DOMESTIC_SPECIES)": "Domestic species (DOMESTIC_SPECIES)",
    "국외 수종 (FOREIGN_SPECIES)": "International species (FOREIGN_SPECIES)",
    "수종명": "Species name", "학명": "Scientific name",
    "최소직경(cm)": "Min diameter (cm)", "최대직경(cm)": "Max diameter (cm)",
    "최소직경(mm)": "Min diameter (mm)", "최대직경(mm)": "Max diameter (mm)",
    "성장률(~10y)": "Growth rate (~10 y)", "성장률(11~20y)": "Growth rate (11–20 y)",
    "성장률(21y~)": "Growth rate (21 y~)", "환경별 계수": "Per-environment coefficients",
    "상대생장식": "Allometric equation", "범위 최소": "Range min", "범위 최대": "Range max",
    "변수1 라벨": "Variable 1 label", "변수2 라벨": "Variable 2 label",
    "변수2 최소": "Variable 2 min", "변수2 최대": "Variable 2 max", "변수2 기본값": "Variable 2 default",
    "셀을 더블클릭해 수정합니다 · 범위를 비우면 '범위 검사 없음' · 변수2 라벨을 비우면 단일변수 식 · "
    "식은 X(첫 변수)·H(두 번째 변수)·^·ln·exp 를 사용합니다":
        "Double-click a cell to edit · leave the range blank for 'no range check' · leave the "
        "variable-2 label blank for a single-variable equation · equations use X (first variable), "
        "H (second variable), ^, ln and exp",
    "+ 새 수종 추가": "+ Add new species", "선택 삭제": "Delete selected",
    "환경별 계수 편집...": "Edit per-environment coefficients...",
    "JSON 파일로 저장": "Save to JSON file",
    "— JSON 파일을 선택하면 여기에 표시됩니다": "— select a JSON file to show it here",
    "변경됨 — 아직 파일에 저장되지 않았습니다": "Modified — not yet saved to the file",
    "변경 없음 (파일과 동기화됨)": "No changes (in sync with the file)",
    "기본값만": "Default only", "{n}개 환경": "{n} environments",
    "새수종": "NewSpecies",
    "삭제할 행을 먼저 선택하세요.": "Select the rows to delete first.",
    "{n}개 수종을 삭제할까요?\n{names}": "Delete {n} species?\n{names}",
    "환경별 계수 — {species}": "Per-environment coefficients — {species}",
    "체크한 환경만 고유 계수를 갖습니다. 체크하지 않은 환경은 기본값(표의 값)을 사용합니다.":
        "Only checked environments carry their own coefficients. Unchecked environments use "
        "the default values from the table.",
    "사용": "Use",
    "교목 표에서 수종 행을 먼저 선택하세요.": "Select a species row in the Trees table first.",
    "입력 오류": "Input error", "검증 실패": "Validation failed", "미저장 변경": "Unsaved changes",
    "교목": "Tree", "관목": "Shrub", "국내": "Domestic", "국외": "International",
    "식은 'Y=' 또는 'ln(Y)=' 로 시작해야 합니다": "The equation must start with 'Y=' or 'ln(Y)='",
    "{what}: 값이 비어 있습니다": "{what}: value is empty",
    "{what}: 숫자가 아닙니다 ({value})": "{what}: not a number ({value})",
    "{where}: 수종명이 비어 있습니다": "{where}: species name is empty",
    "{where}: 수종명 '{name}' 이 중복됩니다": "{where}: species name '{name}' is duplicated",
    "{label} '{name}': 최소직경({a})이 최대직경({b})보다 큽니다":
        "{label} '{name}': min diameter ({a}) exceeds max diameter ({b})",
    "{label} '{name}': 계수 a, b 는 0 보다 커야 합니다": "{label} '{name}': coefficients a and b must be > 0",
    "{label} '{name}': 상대생장식이 비어 있습니다": "{label} '{name}': the equation is empty",
    "{label} '{name}': 범위는 최소·최대를 둘 다 적거나 둘 다 비워야 합니다":
        "{label} '{name}': give both range min and max, or leave both blank",
    "{label} '{name}': 범위 최소({a})가 최대({b})보다 큽니다":
        "{label} '{name}': range min ({a}) exceeds max ({b})",
    "{label} '{name}': 변수2 최소가 최대보다 큽니다": "{label} '{name}': variable-2 min exceeds max",
    "{label} '{name}': 식에 H 가 있지만 변수2 라벨이 비어 있습니다":
        "{label} '{name}': the equation uses H but the variable-2 label is blank",
    "결과가 유한하지 않습니다 (Y={y})": "result is not finite (Y={y})",
    "{label} '{name}': 식 평가 실패 — {error}": "{label} '{name}': equation failed to evaluate — {error}",
    "저장할 JSON 파일 경로가 없습니다. 상단에서 species_data.json 을 지정하세요.":
        "No JSON path to save to. Specify species_data.json above.",
    "저장 전 검증에 실패했습니다:\n\n{errors}": "Validation failed before saving:\n\n{errors}",
    "[저장] {path}": "[Saved] {path}", "[백업] 이전 파일 → {path}": "[Backup] previous file → {path}",
    "저장 실패: {error}": "Save failed: {error}",
    "저장 완료 — 교목 {tree} · 관목 {shrub} · 국내 {dom} · 국외 {for_} 종":
        "Saved — {tree} trees · {shrub} shrubs · {dom} domestic · {for_} international species",
    "편집한 수종 데이터가 아직 파일에 저장되지 않았습니다.\n지금 저장하고 계속할까요?\n\n"
    "예 = 저장 후 진행 · 아니요 = 파일의 기존 내용으로 진행 · 취소 = 중단":
        "The edited species data has not been saved to the file yet.\nSave now and continue?\n\n"
        "Yes = save then continue · No = continue with the file as it is on disk · Cancel = stop",
    "편집 중인 내용을 버리고 새 파일을 불러올까요?": "Discard the current edits and load the new file?",
    "화면 배율": "Zoom",
}


def _current_language() -> str:
    try:
        from PyQt5.QtCore import QSettings
        value = QSettings(_SETTINGS_ORG, _SETTINGS_APP).value(_SETTINGS_KEY)
    except Exception:
        return "ko"
    return "en" if value == "en" else "ko"


def _save_language(code: str) -> None:
    try:
        from PyQt5.QtCore import QSettings
        s = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
        s.setValue(_SETTINGS_KEY, "en" if code == "en" else "ko")
        s.sync()
    except Exception:
        pass


_LANG = "ko"


def tr(text: str) -> str:
    """한글 원문을 현재 언어로. 대응 항목이 없으면 원문 그대로."""
    return _EN.get(text, text) if _LANG == "en" else text


# ── 화면 스케일 (반응형) ────────────────────────────────────────────────
# 본 프로그램의 carbon_calculator.ui_scale / font_config 와 같은 규칙을 자체 구현한다
# (업데이터는 단독 배포이므로 패키지를 import 하지 않는다).
#  - 기준 해상도 1920×1080 의 사용 가능 영역에서 1.0, 작은 화면은 비례 축소(최소 0.70),
#    큰 화면은 최대 1.50 까지만 확대.
#  - 여기에 사용자가 고른 "화면 배율"(85~130%) 을 곱한다. 배율은 QSettings 에 저장.
_REF_W, _REF_H = 1920, 1080
_SCALE_MIN, _SCALE_MAX = 0.70, 1.50
_FONT_DELTA = 3                 # 기준 해상도에서 기본 폰트에 더할 pt (표가 많아 본 프로그램보다 소폭 작게)
_SETTINGS_KEY_ZOOM = "updater_zoom"
_ZOOM_CHOICES = ((0.85, "85%"), (1.0, "100%"), (1.15, "115%"), (1.3, "130%"))
_UI_SCALE = 1.0
_ZOOM = 1.0


def _enable_high_dpi() -> None:
    """고해상도 디스플레이 지원. **QApplication 생성 전** 호출."""
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except Exception:
        pass
    for attr in ("AA_EnableHighDpiScaling", "AA_UseHighDpiPixmaps"):
        flag = getattr(Qt, attr, None)
        if flag is not None:
            try:
                QApplication.setAttribute(flag, True)
            except Exception:
                pass


def _screen_geometry():
    app = QApplication.instance()
    screen = app.primaryScreen() if app is not None else None
    return screen.availableGeometry() if screen is not None else None


def _load_zoom() -> float:
    try:
        from PyQt5.QtCore import QSettings
        v = float(QSettings(_SETTINGS_ORG, _SETTINGS_APP).value(_SETTINGS_KEY_ZOOM, 1.0))
        return v if 0.5 <= v <= 2.0 else 1.0
    except Exception:
        return 1.0


def _save_zoom(z: float) -> None:
    try:
        from PyQt5.QtCore import QSettings
        st = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
        st.setValue(_SETTINGS_KEY_ZOOM, float(z))
        st.sync()
    except Exception:
        pass


def _compute_ui_scale(zoom: float = 1.0, geo=None) -> float:
    """모니터 사용 가능 영역 기준 자동 스케일 × 사용자 배율."""
    if geo is None:
        geo = _screen_geometry()
    auto = 1.0
    if geo is not None and geo.width() > 0 and geo.height() > 0:
        auto = min(geo.width() / _REF_W, geo.height() / _REF_H)
    auto = max(_SCALE_MIN, min(_SCALE_MAX, auto))
    return max(0.55, min(1.9, auto * zoom))


def _set_ui_scale(zoom: float) -> None:
    global _UI_SCALE, _ZOOM
    _ZOOM = zoom
    _UI_SCALE = _compute_ui_scale(zoom)


def _px(v: float) -> int:
    return max(1, round(v * _UI_SCALE))


def _pt(v: float) -> int:
    return max(7, round(v * _UI_SCALE))


_BASE_PT: int | None = None     # 앱 최초 기본 폰트 크기 — 배율을 바꿔도 항상 이 값에서 계산한다


def _apply_app_font(app: QApplication) -> None:
    """앱 기본 폰트를 스케일에 맞춘다 (모든 위젯에 일괄 반영).

    현재 폰트가 아니라 최초 기본 크기(_BASE_PT)에서 계산해야 배율을 여러 번 바꿔도
    크기가 누적되지 않는다.
    """
    global _BASE_PT
    f = app.font()
    if _BASE_PT is None:
        _BASE_PT = f.pointSize() if f.pointSize() > 0 else 9
    if "Malgun" not in f.family() and "맑은" not in f.family():
        f.setFamily("Malgun Gothic")
    f.setPointSize(max(8, round((_BASE_PT + _FONT_DELTA) * _UI_SCALE)))
    app.setFont(f)


def _fit_window(win: QWidget, wfrac: float = 0.86, hfrac: float = 0.88,
                min_w: int = 1000, min_h: int = 640) -> None:
    """창을 화면 비율로 맞추고 화면을 넘지 않게 클램프한 뒤 중앙에 둔다."""
    geo = _screen_geometry()
    if geo is None:
        win.resize(1180, 900)
        return
    aw, ah = geo.width(), geo.height()
    eff_w, eff_h = min(_px(min_w), aw), min(_px(min_h), ah)
    win.setMinimumSize(eff_w, eff_h)
    w = max(eff_w, min(int(aw * wfrac), aw))
    h = max(eff_h, min(int(ah * hfrac), ah))
    win.resize(w, h)
    win.move(geo.x() + (aw - w) // 2, geo.y() + (ah - h) // 2)


def _fit_dialog(dlg: QWidget, width: int, height: int, margin: int = 48) -> None:
    w, h = _px(width), _px(height)
    geo = _screen_geometry()
    if geo is not None:
        w, h = min(w, geo.width() - margin), min(h, geo.height() - margin)
    dlg.resize(max(360, w), max(240, h))


_STATUS_INDENT: int | None = None   # 상태 라벨 들여쓰기 — 창이 라벨 폭을 계산해 채운다


def _status_css(color) -> str:
    c = "color: %s; " % color if color else ""
    indent = _STATUS_INDENT if _STATUS_INDENT is not None else _px(223)
    return "%smargin-left: %dpx;" % (c, indent)


def _note_css() -> str:
    return "color: #555; font-size: %dpt;" % _pt(9)


_IS_EXE = hasattr(sys, '_MEIPASS')
HERE = Path(sys.executable).parent if _IS_EXE else Path(__file__).resolve().parent

# 내장 소스 루트:
#   frozen  → PyInstaller 가 _MEIPASS/bundled_src 로 풀어놓은 소스
#   dev     → 이 파일이 있는 Code 폴더 자체
if _IS_EXE:
    SRC_ROOT = Path(sys._MEIPASS) / "bundled_src"   # type: ignore[attr-defined]
else:
    SRC_ROOT = HERE

BUILD_VENV    = Path.home() / ".carboncalc_build_venv"
JSON_NAME     = "species_data.json"

# ── 플랫폼별 venv 레이아웃 / 실행파일 확장자 ──────────────────────────────
_VENV_BIN     = "Scripts" if os.name == "nt" else "bin"
_EXE_EXT      = ".exe" if os.name == "nt" else ""
MAIN_APP_NAME = "탄소저장량측정모듈"
MAIN_EXE_NAME = f"{MAIN_APP_NAME}{_EXE_EXT}"

# 작업폴더로 복사할 때 제외할 항목
_COPY_IGNORE = shutil.ignore_patterns(
    "build", "dist", "__pycache__", "*.pyc", ".git",
    ".build_venv", "*.spec",
)


def _find_python() -> Path | None:
    """빌드용 Python 탐색: 빌드 venv → 시스템 PATH."""
    p = BUILD_VENV / _VENV_BIN / f"python{_EXE_EXT}"
    if p.exists():
        return p
    for name in ("python", "python3"):
        found = shutil.which(name)
        if found:
            try:
                r = subprocess.run([found, "--version"], capture_output=True, timeout=5)
                if r.returncode == 0:
                    return Path(found)
            except Exception:
                pass
    return None


def _auto_find_main_exe() -> Path | None:
    """탄소저장량측정모듈.exe 를 자동 탐색 (현재 폴더 / dist/)."""
    for candidate in [
        HERE / MAIN_EXE_NAME,
        HERE / "dist" / MAIN_EXE_NAME,
        HERE / "dist" / MAIN_EXE_NAME.replace(".exe", "") / MAIN_EXE_NAME,
    ]:
        if candidate.exists():
            return candidate
    return None


# ─────────────────────────── JSON 검증 ───────────────────────────

def _validate_species_json(path: Path) -> tuple[bool, str]:
    """통합 species_data.json 검증. 4개 섹션 중 하나 이상 존재하면 유효."""
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        return False, tr("JSON 파싱 오류: {error}").format(error=e)

    n_tree = len(data.get('TREE_BASE', {}))
    n_shrub = len(data.get('SHRUB_SPECIES', {}))
    n_dom = len(data.get('DOMESTIC_SPECIES', {}))
    n_for = len(data.get('FOREIGN_SPECIES', {}))

    if (n_tree + n_shrub + n_dom + n_for) == 0:
        return False, (tr("유효한 수종 섹션이 없습니다. "
                       "TREE_BASE / SHRUB_SPECIES / DOMESTIC_SPECIES / FOREIGN_SPECIES 중 "
                       "하나 이상이 필요합니다."))

    return True, tr("교목 {tree} · 관목 {shrub} · 국내 {dom} · 국외 {for_} 종").format(
        tree=n_tree, shrub=n_shrub, dom=n_dom, for_=n_for)


# ─────────────────────────── 빌드 워커 ───────────────────────────

class BuildWorker(QThread):
    """임시 작업폴더 구성 → build_exe.py 실행 → 산출물 복사 를 백그라운드로 수행."""
    log_line = pyqtSignal(str)
    finished = pyqtSignal(bool, str)   # (성공여부, 산출물 경로 또는 오류메시지)

    def __init__(self, json_path: Path, out_dir: Path, options: list[str]):
        super().__init__()
        self.json_path = json_path
        self.out_dir = out_dir
        self.options = options

    def _emit(self, msg: str):
        self.log_line.emit(msg)

    def run(self):
        workdir = None
        try:
            python = _find_python()
            if python is None:
                self.finished.emit(False,
                    tr("Python 인터프리터를 찾을 수 없습니다. Python 3.10+ 를 설치하세요."))
                return

            if not (SRC_ROOT / "build_exe.py").exists():
                self.finished.emit(False,
                    tr("내장 소스를 찾을 수 없습니다: {path}\n"
                       "updater 를 build_updater.py 로 다시 빌드하세요.")
                    .format(path=SRC_ROOT))
                return

            # ── 1) 내장 소스를 임시 작업폴더로 복사 ──────────────────────
            workdir = Path(tempfile.mkdtemp(prefix="carboncalc_build_"))
            self._emit(tr("[1/4] 작업폴더 준비: {path}").format(path=workdir))
            shutil.copytree(SRC_ROOT, workdir, dirs_exist_ok=True, ignore=_COPY_IGNORE)

            # ── 2) 사용자 JSON 투입 (구 carbon1/2 파일은 충돌 방지 위해 제거) ──
            for _old in ("carbon1_species_data.json", "carbon2_species_data.json"):
                _p = workdir / _old
                if _p.exists():
                    _p.unlink()
            shutil.copy2(self.json_path, workdir / JSON_NAME)
            self._emit(tr("[2/4] 수종 데이터 적용: {src} → {dst}")
                       .format(src=self.json_path.name, dst=JSON_NAME))

            # ── 3) build_exe.py 실행 (PyInstaller) ──────────────────────
            cmd = [str(python), str(workdir / "build_exe.py")] + self.options
            self._emit(tr("[3/4] 빌드 시작: {cmd}").format(cmd=" ".join(cmd)))
            self._emit(tr("      (최초 실행 시 빌드 전용 venv 생성으로 수 분 소요)"))
            self._emit("=" * 70)

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace',
                cwd=str(workdir),
            )
            for line in proc.stdout:
                self._emit(line.rstrip())
            proc.wait()

            if proc.returncode != 0:
                self.finished.emit(False, tr("PyInstaller 빌드가 실패했습니다. 위 로그를 확인하세요."))
                return

            # ── 4) 산출물 복사 ─────────────────────────────────────────
            onedir = "--onedir" in self.options
            if onedir:
                produced = workdir / "dist" / MAIN_APP_NAME
            else:
                produced = workdir / "dist" / MAIN_EXE_NAME

            if not produced.exists():
                self.finished.emit(
                    False,
                    tr("산출물을 찾을 수 없습니다: {path}").format(path=produced))
                return

            self.out_dir.mkdir(parents=True, exist_ok=True)
            self._emit("=" * 70)
            self._emit(tr("[4/4] 산출물 복사 → {path}").format(path=self.out_dir))

            if onedir:
                dest = self.out_dir / MAIN_APP_NAME
                if dest.exists():
                    shutil.rmtree(dest, ignore_errors=True)
                shutil.copytree(produced, dest)
                final = dest / MAIN_EXE_NAME
            else:
                final = self.out_dir / MAIN_EXE_NAME
                shutil.copy2(produced, final)

            self.finished.emit(True, str(final))

        except Exception as e:
            self.finished.emit(False, tr("[오류] {error}").format(error=e))
        finally:
            if workdir and workdir.exists():
                shutil.rmtree(workdir, ignore_errors=True)


# ─────────────────────────── UI 헬퍼 ───────────────────────────

class FilePickRow(QWidget):
    def __init__(self, label: str, btn_label: str | None = None, parent=None,
                 label_width: int | None = None):
        super().__init__(parent)
        if btn_label is None:
            btn_label = tr("열기...")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label_w = QLabel(label)
        # 라벨 폭은 폰트 크기에 따라 창이 계산해 넘긴다(큰 배율에서 글자가 잘리지 않도록)
        self.label_w.setFixedWidth(label_width or _px(215))
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(tr("파일/폴더 경로를 선택하거나 직접 입력하세요"))
        self.btn = QPushButton(btn_label)
        self.btn.setFixedWidth(_px(75))
        layout.addWidget(self.label_w)
        layout.addWidget(self.edit)
        layout.addWidget(self.btn)

    @property
    def path(self) -> Path | None:
        t = self.edit.text().strip()
        return Path(t) if t else None


# ─────────────────────────── 수종 데이터 편집기 ───────────────────────────
# species_data.json 의 4개 섹션(교목·관목·국내·국외)을 표로 보여주고 셀 단위로
# 추가·수정·삭제한 뒤 같은 파일에 저장한다. 저장 시 형식은 data.py / data2.py 의
# 로더가 읽는 그대로 유지한다:
#   TREE_BASE      : {"default": [a,b,cf,dmin,dmax,g10,g20,g21], "by_env": {환경: [...]}}
#   SHRUB_SPECIES  : [a,b,cf,dmin,dmax,g10,g20,g21]
#   DOMESTIC/FOREIGN: {"equation", "range": [min,max]|[null,null], "var1", "var2"?}
# 학명(SPECIES_EN)은 꼬리표를 뗀 기본 수종명 기준으로 함께 갱신한다.

_SECTION_TREE, _SECTION_SHRUB, _SECTION_DOM, _SECTION_FOR = (
    "TREE_BASE", "SHRUB_SPECIES", "DOMESTIC_SPECIES", "FOREIGN_SPECIES")

# 열 정의: (표시 헤더, 내부 키). 헤더는 tr() 로 번역된다.
_COEF_KEYS = ("a", "b", "cf", "dmin", "dmax", "g10", "g20", "g21")
_TREE_COLS = [
    ("수종명", "name"), ("학명", "sci"), ("a", "a"), ("b", "b"), ("CF", "cf"),
    ("최소직경(cm)", "dmin"), ("최대직경(cm)", "dmax"),
    ("성장률(~10y)", "g10"), ("성장률(11~20y)", "g20"), ("성장률(21y~)", "g21"),
    ("환경별 계수", "env"),
]
_SHRUB_COLS = [
    ("수종명", "name"), ("학명", "sci"), ("a", "a"), ("b", "b"), ("CF", "cf"),
    ("최소직경(mm)", "dmin"), ("최대직경(mm)", "dmax"),
    ("성장률(~10y)", "g10"), ("성장률(11~20y)", "g20"), ("성장률(21y~)", "g21"),
]
_EQ_COLS = [
    ("수종명", "name"), ("학명", "sci"), ("상대생장식", "eq"),
    ("범위 최소", "rmin"), ("범위 최대", "rmax"), ("변수1 라벨", "v1"),
    ("변수2 라벨", "v2"), ("변수2 최소", "v2min"), ("변수2 최대", "v2max"),
    ("변수2 기본값", "v2def"),
]
_ROLE_BY_ENV = Qt.UserRole + 1     # 교목 수종명 셀에 by_env dict 를 보관
_ROLE_TRUE_NAME = Qt.UserRole + 2  # 수종명 셀이 학명으로 표시(영문 모드·읽기전용)될 때 실제 저장 키(국문)


class _PyBox:
    """Qt 아이템 데이터에 dict 를 그대로 넣으면 PyQt 가 QVariantMap(키 정렬) 으로
    변환해 환경 순서가 바뀐다. Python 객체로 감싸 변환을 막는다."""
    __slots__ = ("v",)

    def __init__(self, v):
        self.v = v


def _get_by_env(item) -> dict:
    box = item.data(_ROLE_BY_ENV) if item is not None else None
    if isinstance(box, _PyBox):
        return dict(box.v)
    return dict(box) if isinstance(box, dict) else {}


def _set_by_env(item, by_env: dict) -> None:
    item.setData(_ROLE_BY_ENV, _PyBox(dict(by_env)))


def _set_true_name(item, name: str) -> None:
    item.setData(_ROLE_TRUE_NAME, name)


def _get_true_name(item) -> str:
    """0열(수종명) 셀의 실제 저장 키. 편집 가능한 상태(한국어 모드, 또는 학명이 아직
    없는 새 행)면 화면 텍스트가 곧 키다. 학명으로 치환되어 읽기전용이 된 상태에서만
    숨겨둔 원본(국문) 이름을 쓴다 — 그래야 편집 중인 텍스트가 저장 키로 조용히
    무시되는 일이 없다."""
    if item is None:
        return ""
    if not (item.flags() & Qt.ItemIsEditable):
        stored = item.data(_ROLE_TRUE_NAME)
        if stored:
            return stored
    return item.text()

# 식 검증용 최소 평가기 — carbon_calculator.equation_eval 과 같은 규칙
# (^ → **, ln/log/exp/sqrt 허용, "ln(Y)=" 이면 exp 적용). 업데이터는 단독 배포되므로
# 본 프로그램 패키지를 import 하지 않고 여기서 자체 검사한다.
_EVAL_FUNCS = {
    "ln": math.log, "log": math.log, "exp": math.exp,
    "sqrt": math.sqrt, "pow": pow, "abs": abs,
}


def _eval_equation(equation: str, x: float, h: float | None = None) -> float:
    eqn = equation.strip().replace("^", "**")
    env: dict = {"__builtins__": {}}
    env.update(_EVAL_FUNCS)
    env["X"] = float(x)
    if h is not None:
        env["H"] = float(h)
    if "ln(Y)=" in eqn:
        return math.exp(eval(eqn.split("ln(Y)=", 1)[1], env))
    if "Y=" in eqn:
        return float(eval(eqn.split("Y=", 1)[1], env))
    raise ValueError(tr("식은 'Y=' 또는 'ln(Y)=' 로 시작해야 합니다"))


def _fmt_num(v) -> str:
    """JSON 숫자 → 표 셀 문자열. 지수표기 없이, 불필요한 0 없이."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e12:
            return str(int(v))
        s = ("%.10f" % v).rstrip("0").rstrip(".")
        return s if s not in ("", "-0", "-") else repr(v)
    return str(v)


def _parse_num(text: str, what: str, allow_blank: bool = False) -> float | None:
    t = (text or "").strip()
    if not t:
        if allow_blank:
            return None
        raise ValueError(tr("{what}: 값이 비어 있습니다").format(what=what))
    try:
        return float(t)
    except ValueError:
        raise ValueError(tr("{what}: 숫자가 아닙니다 ({value})").format(what=what, value=t))


def _num_out(v: float | None):
    """저장용: 정수값이면 int 로 (JSON 을 원본처럼 깔끔하게)."""
    if v is None:
        return None
    return int(v) if float(v) == int(v) and abs(v) < 1e12 else float(v)


def _base_name(name: str) -> str:
    """'후박나무(지상부)' → '후박나무'. 학명(SPECIES_EN) 키."""
    return name.split("(", 1)[0].strip()


def _tidy_columns(t: QTableWidget) -> None:
    """내용 기준으로 열 폭을 잡되, 긴 식/경로 열은 상한을 두어 다른 열이 밀리지 않게 한다."""
    t.resizeColumnsToContents()
    cap = _px(420)
    for c in range(t.columnCount()):
        if t.columnWidth(c) > cap:
            t.setColumnWidth(c, cap)


def _mk_item(text: str, editable: bool = True) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    if text and len(text) > 24:
        it.setToolTip(text)          # 긴 식·라벨은 마우스를 올리면 전체가 보인다
    if not editable:
        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
        it.setForeground(Qt.darkGray)
    return it


class TreeEnvDialog(QDialog):
    """교목 한 종의 복원 환경별 계수(by_env) 편집."""

    def __init__(self, species: str, environments: list[str], default_arr: list,
                 by_env: dict, env_en: dict | None = None, sci_name: str = "", parent=None):
        super().__init__(parent)
        title_name = sci_name if (_LANG == "en" and sci_name) else species
        self.setWindowTitle(tr("환경별 계수 — {species}").format(species=title_name))
        self._envs = list(environments)
        env_en = env_en or {}
        v = QVBoxLayout(self)
        note = QLabel(tr("체크한 환경만 고유 계수를 갖습니다. 체크하지 않은 환경은 기본값(표의 값)을 사용합니다."))
        note.setWordWrap(True)
        note.setStyleSheet(_note_css())
        v.addWidget(note)

        headers = [tr("사용")] + [tr(h) for h, _k in _TREE_COLS[2:10]]
        self.table = QTableWidget(len(self._envs), len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        # 세로 헤더는 표시용 — 저장 키는 self._envs(원본 국문)를 그대로 쓴다.
        row_labels = [env_en.get(e, e) if _LANG == "en" else e for e in self._envs]
        self.table.setVerticalHeaderLabels(row_labels)
        self.table.verticalHeader().setDefaultSectionSize(_px(26))
        self.table.horizontalHeader().setStretchLastSection(True)
        for r, env in enumerate(self._envs):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked if env in by_env else Qt.Unchecked)
            self.table.setItem(r, 0, chk)
            arr = by_env.get(env, default_arr)
            for c in range(8):
                self.table.setItem(r, c + 1, _mk_item(_fmt_num(arr[c] if c < len(arr) else None)))
        self.table.resizeColumnsToContents()
        # 환경 수만큼 행이 스크롤 없이 다 보이도록, 화면을 넘지 않는 범위에서 크기를 잡는다
        _fit_dialog(self, 960, 150 + 30 * max(1, len(self._envs)))
        v.addWidget(self.table)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        v.addWidget(btns)
        self._result: dict = {}

    def _accept(self):
        result = {}
        for r, env in enumerate(self._envs):
            if self.table.item(r, 0).checkState() != Qt.Checked:
                continue
            arr = []
            for c in range(8):
                what = "%s / %s" % (env, tr(_TREE_COLS[c + 2][0]))
                try:
                    arr.append(_num_out(_parse_num(self.table.item(r, c + 1).text(), what)))
                except ValueError as e:
                    QMessageBox.warning(self, tr("입력 오류"), str(e))
                    return
            result[env] = arr
        self._result = result
        self.accept()

    def result_by_env(self) -> dict:
        return self._result


class SpeciesEditor(QGroupBox):
    """species_data.json 4개 섹션의 표 편집기 (추가·수정·삭제·저장)."""

    dirty_changed = pyqtSignal(bool)
    save_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(tr("수종별 상대생장식 (JSON 미리보기 · 추가/수정/삭제)"), parent)
        self._data: dict | None = None      # 마지막으로 불러온/저장한 원본 dict
        self._dirty = False
        self._loading = False
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────
    def _build_ui(self):
        v = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tables: dict[str, QTableWidget] = {}
        for section, title, cols in (
            (_SECTION_TREE, "교목 (TREE_BASE)", _TREE_COLS),
            (_SECTION_SHRUB, "관목 (SHRUB_SPECIES)", _SHRUB_COLS),
            (_SECTION_DOM, "국내 수종 (DOMESTIC_SPECIES)", _EQ_COLS),
            (_SECTION_FOR, "국외 수종 (FOREIGN_SPECIES)", _EQ_COLS),
        ):
            t = QTableWidget(0, len(cols))
            t.setHorizontalHeaderLabels([tr(h) for h, _k in cols])
            t.setSelectionBehavior(QAbstractItemView.SelectRows)
            t.setSelectionMode(QAbstractItemView.ExtendedSelection)
            t.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
                              | QAbstractItemView.AnyKeyPressed)
            t.setAlternatingRowColors(True)
            t.verticalHeader().setDefaultSectionSize(_px(26))
            t.horizontalHeader().setStretchLastSection(True)
            t.setMinimumHeight(_px(170))
            t.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            t.itemChanged.connect(self._on_item_changed)
            t.cellDoubleClicked.connect(self._on_cell_double_clicked)
            self.tables[section] = t
            self.tabs.addTab(t, tr(title))
        self.tabs.currentChanged.connect(self._sync_buttons)
        v.addWidget(self.tabs, 1)

        hint = QLabel(tr("셀을 더블클릭해 수정합니다 · 범위를 비우면 '범위 검사 없음' · 변수2 라벨을 비우면 단일변수 식 · "
                         "식은 X(첫 변수)·H(두 번째 변수)·^·ln·exp 를 사용합니다"))
        hint.setWordWrap(True)
        hint.setStyleSheet(_note_css())
        v.addWidget(hint)

        row = QHBoxLayout()
        self.add_btn = QPushButton(tr("+ 새 수종 추가"))
        self.del_btn = QPushButton(tr("선택 삭제"))
        self.env_btn = QPushButton(tr("환경별 계수 편집..."))
        self.add_btn.clicked.connect(self.add_row)
        self.del_btn.clicked.connect(self.delete_selected)
        self.env_btn.clicked.connect(self.edit_env)
        row.addWidget(self.add_btn)
        row.addWidget(self.del_btn)
        row.addWidget(self.env_btn)
        row.addStretch(1)
        v.addLayout(row)

        status_row = QHBoxLayout()
        self.status = QLabel("")
        self.save_btn = QPushButton(tr("JSON 파일로 저장"))
        self.save_btn.clicked.connect(self.save_requested.emit)
        status_row.addWidget(self.status)
        status_row.addStretch(1)
        status_row.addWidget(self.save_btn)
        v.addLayout(status_row)
        self._set_dirty(False)
        self._sync_buttons()

    def _sync_buttons(self, *_):
        loaded = self._data is not None
        is_tree = self.tabs.currentWidget() is self.tables.get(_SECTION_TREE)
        self.add_btn.setEnabled(loaded)
        self.del_btn.setEnabled(loaded)
        self.env_btn.setEnabled(loaded and is_tree)
        self.env_btn.setVisible(is_tree)

    # ── 상태 ──────────────────────────────────────────────────────
    def is_dirty(self) -> bool:
        return self._dirty

    def is_loaded(self) -> bool:
        return self._data is not None

    def _set_dirty(self, dirty: bool):
        self._dirty = dirty
        if self._data is None:
            self.status.setText(tr("— JSON 파일을 선택하면 여기에 표시됩니다"))
            self.status.setStyleSheet("color: gray;")
        elif dirty:
            self.status.setText(tr("변경됨 — 아직 파일에 저장되지 않았습니다"))
            self.status.setStyleSheet("color: #b35c00; font-weight: bold;")
        else:
            self.status.setText(tr("변경 없음 (파일과 동기화됨)"))
            self.status.setStyleSheet("color: gray;")
        self.save_btn.setEnabled(self._data is not None and dirty)
        self.dirty_changed.emit(dirty)

    def _on_item_changed(self, _item):
        if not self._loading:
            self._set_dirty(True)

    def _current_table(self) -> QTableWidget:
        return self.tabs.currentWidget()

    def _current_section(self) -> str:
        t = self._current_table()
        for k, w in self.tables.items():
            if w is t:
                return k
        return _SECTION_TREE

    # ── 불러오기 ──────────────────────────────────────────────────
    def load(self, data: dict):
        """JSON dict 를 표에 채운다. 저장 상태로 초기화."""
        self._loading = True
        try:
            self._data = data
            sci = data.get("SPECIES_EN") or {}
            self._fill_coef_table(self.tables[_SECTION_TREE], data.get(_SECTION_TREE) or {}, sci, tree=True)
            self._fill_coef_table(self.tables[_SECTION_SHRUB], data.get(_SECTION_SHRUB) or {}, sci, tree=False)
            self._fill_eq_table(self.tables[_SECTION_DOM], data.get(_SECTION_DOM) or {}, sci)
            self._fill_eq_table(self.tables[_SECTION_FOR], data.get(_SECTION_FOR) or {}, sci)
            for t in self.tables.values():
                _tidy_columns(t)
        finally:
            self._loading = False
        self._set_dirty(False)
        self._sync_buttons()

    def _fill_coef_table(self, t: QTableWidget, section: dict, sci: dict, tree: bool):
        t.setRowCount(0)
        for name, entry in section.items():
            if isinstance(entry, dict) and "default" in entry:
                arr, by_env = entry["default"], dict(entry.get("by_env") or {})
            else:
                arr, by_env = entry, {}
            self._append_coef_row(t, name, sci.get(_base_name(name), ""), arr, by_env, tree)

    def _append_coef_row(self, t: QTableWidget, name: str, sci_name: str, arr: list,
                         by_env: dict, tree: bool):
        r = t.rowCount()
        t.insertRow(r)
        # 영문 모드 + 학명이 있으면 0열은 학명을 보여주는 읽기전용 표시로 바뀐다.
        # 저장 키(국문 수종명)는 화면에 보이지 않아도 _ROLE_TRUE_NAME 에 그대로 남는다.
        swap = (_LANG == "en" and bool(sci_name))
        name_it = _mk_item(sci_name if swap else name, editable=not swap)
        _set_true_name(name_it, name)
        if tree:
            _set_by_env(name_it, dict(by_env))
        t.setItem(r, 0, name_it)
        t.setItem(r, 1, _mk_item(sci_name))
        for c in range(8):
            t.setItem(r, c + 2, _mk_item(_fmt_num(arr[c] if c < len(arr) else None)))
        if tree:
            t.setItem(r, 10, _mk_item(self._env_summary(by_env), editable=False))

    def _env_summary(self, by_env: dict) -> str:
        if not by_env:
            return tr("기본값만")
        env_en = (self._data or {}).get("ENVIRONMENTS_EN") or {}
        shown = [env_en.get(e, e) if _LANG == "en" else e for e in by_env.keys()]
        return tr("{n}개 환경").format(n=len(by_env)) + " (" + ", ".join(shown) + ")"

    def _fill_eq_table(self, t: QTableWidget, section: dict, sci: dict):
        t.setRowCount(0)
        for name, e in section.items():
            rng = e.get("range") or [None, None]
            v2 = e.get("var2") or {}
            self._append_eq_row(t, [
                name, sci.get(_base_name(name), ""), e.get("equation", ""),
                _fmt_num(rng[0]), _fmt_num(rng[1]), e.get("var1", "DBH (cm)"),
                v2.get("label", ""), _fmt_num(v2.get("min")) if v2 else "",
                _fmt_num(v2.get("max")) if v2 else "", _fmt_num(v2.get("default")) if v2 else "",
            ])

    @staticmethod
    def _append_eq_row(t: QTableWidget, values: list):
        r = t.rowCount()
        t.insertRow(r)
        name = values[0] if values else ""
        sci_name = values[1] if len(values) > 1 else ""
        # 0열도 _append_coef_row 와 같은 규칙: 영문 모드 + 학명이 있으면 학명을
        # 읽기전용으로 보여주고, 저장 키(국문)는 _ROLE_TRUE_NAME 에 보관한다.
        swap = (_LANG == "en" and bool(sci_name))
        for c, val in enumerate(values):
            if c == 0:
                it = _mk_item(sci_name if swap else name, editable=not swap)
                _set_true_name(it, name)
            else:
                it = _mk_item(val)
            t.setItem(r, c, it)

    # ── 추가/삭제/환경 ─────────────────────────────────────────────
    def add_row(self):
        section = self._current_section()
        t = self._current_table()
        self._loading = True
        try:
            if section == _SECTION_TREE:
                self._append_coef_row(t, tr("새수종"), "", [0.1, 2.5, 0.5, 1, 30, 0.1, 0.1, 0.1], {}, True)
            elif section == _SECTION_SHRUB:
                self._append_coef_row(t, tr("새수종"), "", [0.0002, 2.5, 0.5, 5, 40, 0.2, 0.2, 0.2], {}, False)
            else:
                self._append_eq_row(t, [tr("새수종") + "(전체)", "", "Y=0.1*X^2.5",
                                        "", "", "DBH (cm)", "", "", "", ""])
        finally:
            self._loading = False
        r = t.rowCount() - 1
        t.scrollToItem(t.item(r, 0))
        t.setCurrentCell(r, 0)
        t.editItem(t.item(r, 0))
        self._set_dirty(True)

    def delete_selected(self):
        t = self._current_table()
        rows = sorted({i.row() for i in t.selectedItems()}, reverse=True)
        if not rows:
            QMessageBox.information(self, tr("선택 삭제"), tr("삭제할 행을 먼저 선택하세요."))
            return
        names = ", ".join(t.item(r, 0).text() for r in reversed(rows))
        if QMessageBox.question(
                self, tr("선택 삭제"),
                tr("{n}개 수종을 삭제할까요?\n{names}").format(n=len(rows), names=names),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        for r in rows:
            t.removeRow(r)
        self._set_dirty(True)

    def _on_cell_double_clicked(self, row: int, col: int):
        if self._current_section() == _SECTION_TREE and col == 10:
            self.edit_env()

    def edit_env(self):
        t = self.tables[_SECTION_TREE]
        r = t.currentRow()
        if r < 0:
            QMessageBox.information(self, tr("환경별 계수"), tr("교목 표에서 수종 행을 먼저 선택하세요."))
            return
        name_it = t.item(r, 0)
        true_name = _get_true_name(name_it)
        try:
            default_arr = [_num_out(_parse_num(t.item(r, c + 2).text(), tr(_TREE_COLS[c + 2][0])))
                           for c in range(8)]
        except ValueError as e:
            QMessageBox.warning(self, tr("입력 오류"), str(e))
            return
        envs = list((self._data or {}).get("ENVIRONMENTS") or [])
        env_en = (self._data or {}).get("ENVIRONMENTS_EN") or {}
        sci = (self._data or {}).get("SPECIES_EN") or {}
        sci_name = sci.get(_base_name(true_name), "")
        dlg = TreeEnvDialog(true_name, envs, default_arr, _get_by_env(name_it),
                             env_en, sci_name, self)
        if dlg.exec_() == QDialog.Accepted:
            by_env = dlg.result_by_env()
            _set_by_env(name_it, by_env)
            self._loading = True
            try:
                t.item(r, 10).setText(self._env_summary(by_env))
            finally:
                self._loading = False
            self._set_dirty(True)

    # ── 검증 + JSON 조립 ──────────────────────────────────────────
    def validate_and_build(self) -> tuple[list[str], dict | None]:
        """표 내용을 검증하고 저장할 dict 를 만든다. (오류목록, dict|None)"""
        if self._data is None:
            return [tr("먼저 species_data.json 을 선택하세요.")], None
        errors: list[str] = []
        sci_map: dict[str, str] = {}
        out = dict(self._data)     # _schema · ENVIRONMENTS · ENVIRONMENTS_EN 등은 그대로

        def _sci(name: str, text: str):
            # 같은 기본 수종명이 여러 행에 걸쳐 있을 때(예: 단풍나무(전체)/단풍나무(경남)),
            # 학명은 기본명당 하나만 저장되므로 맨 처음 값이 있는 행만 사용한다.
            # 나머지 행은 비워둬도 되고, 값이 있어도 조용히 무시한다(불일치 에러 없음).
            b = _base_name(name)
            s = (text or "").strip()
            if s and b not in sci_map:
                sci_map[b] = s

        out[_SECTION_TREE] = self._collect_coef(self.tables[_SECTION_TREE], True, errors, _sci)
        out[_SECTION_SHRUB] = self._collect_coef(self.tables[_SECTION_SHRUB], False, errors, _sci)
        out[_SECTION_DOM] = self._collect_eq(self.tables[_SECTION_DOM], tr("국내"), errors, _sci)
        out[_SECTION_FOR] = self._collect_eq(self.tables[_SECTION_FOR], tr("국외"), errors, _sci)

        if errors:
            return errors, None
        # 학명 표: 표에 있는 기본명만 남기고, 표에서 준 값으로 갱신
        old_sci = dict(self._data.get("SPECIES_EN") or {})
        live_bases = {_base_name(n) for sec in (_SECTION_TREE, _SECTION_SHRUB, _SECTION_DOM, _SECTION_FOR)
                      for n in out[sec]}
        new_sci = {b: v for b, v in old_sci.items() if b in live_bases}
        new_sci.update(sci_map)
        out["SPECIES_EN"] = new_sci
        # 키 순서를 원본과 같게
        ordered = {}
        for k in ("_schema", "ENVIRONMENTS", "ENVIRONMENTS_EN", "SPECIES_EN",
                  _SECTION_TREE, _SECTION_SHRUB, _SECTION_DOM, _SECTION_FOR):
            if k in out:
                ordered[k] = out[k]
        for k, v in out.items():
            ordered.setdefault(k, v)
        return [], ordered

    def _collect_coef(self, t: QTableWidget, tree: bool, errors: list, sci_cb) -> dict:
        label = tr("교목") if tree else tr("관목")
        result: dict = {}
        for r in range(t.rowCount()):
            name = _get_true_name(t.item(r, 0)).strip()
            where = "%s #%d" % (label, r + 1)
            if not name:
                errors.append(tr("{where}: 수종명이 비어 있습니다").format(where=where)); continue
            if name in result:
                errors.append(tr("{where}: 수종명 '{name}' 이 중복됩니다").format(where=where, name=name)); continue
            arr = []
            ok = True
            for c in range(8):
                what = "%s '%s' / %s" % (label, name, tr(_TREE_COLS[c + 2][0]))
                try:
                    arr.append(_num_out(_parse_num(t.item(r, c + 2).text() if t.item(r, c + 2) else "", what)))
                except ValueError as e:
                    errors.append(str(e)); ok = False
            if not ok:
                continue
            if arr[3] > arr[4]:
                errors.append(tr("{label} '{name}': 최소직경({a})이 최대직경({b})보다 큽니다")
                              .format(label=label, name=name, a=_fmt_num(arr[3]), b=_fmt_num(arr[4])))
                continue
            if arr[0] <= 0 or arr[1] <= 0:
                errors.append(tr("{label} '{name}': 계수 a, b 는 0 보다 커야 합니다").format(label=label, name=name))
                continue
            sci_cb(name, t.item(r, 1).text() if t.item(r, 1) else "")
            if tree:
                by_env = _get_by_env(t.item(r, 0))
                entry = {"default": arr}
                if by_env:
                    entry["by_env"] = {env: list(v) for env, v in by_env.items()}
                result[name] = entry
            else:
                result[name] = arr
        return result

    def _collect_eq(self, t: QTableWidget, label: str, errors: list, sci_cb) -> dict:
        result: dict = {}
        for r in range(t.rowCount()):
            g = lambda c: (t.item(r, c).text() if t.item(r, c) else "").strip()
            name = _get_true_name(t.item(r, 0)).strip()
            where = "%s #%d" % (label, r + 1)
            if not name:
                errors.append(tr("{where}: 수종명이 비어 있습니다").format(where=where)); continue
            if name in result:
                errors.append(tr("{where}: 수종명 '{name}' 이 중복됩니다").format(where=where, name=name)); continue
            eq = g(2)
            if not eq:
                errors.append(tr("{label} '{name}': 상대생장식이 비어 있습니다").format(label=label, name=name)); continue
            try:
                rmin = _parse_num(g(3), "%s '%s' / %s" % (label, name, tr("범위 최소")), allow_blank=True)
                rmax = _parse_num(g(4), "%s '%s' / %s" % (label, name, tr("범위 최대")), allow_blank=True)
            except ValueError as e:
                errors.append(str(e)); continue
            if (rmin is None) != (rmax is None):
                errors.append(tr("{label} '{name}': 범위는 최소·최대를 둘 다 적거나 둘 다 비워야 합니다")
                              .format(label=label, name=name)); continue
            if rmin is not None and rmin > rmax:
                errors.append(tr("{label} '{name}': 범위 최소({a})가 최대({b})보다 큽니다")
                              .format(label=label, name=name, a=_fmt_num(rmin), b=_fmt_num(rmax))); continue
            var1 = g(5) or "DBH (cm)"
            v2label = g(6)
            entry: dict = {"equation": eq, "range": [_num_out(rmin), _num_out(rmax)], "var1": var1}
            h_test = None
            if v2label:
                try:
                    v2min = _parse_num(g(7), "%s '%s' / %s" % (label, name, tr("변수2 최소")))
                    v2max = _parse_num(g(8), "%s '%s' / %s" % (label, name, tr("변수2 최대")))
                    v2def = _parse_num(g(9), "%s '%s' / %s" % (label, name, tr("변수2 기본값")))
                except ValueError as e:
                    errors.append(str(e)); continue
                if v2min > v2max:
                    errors.append(tr("{label} '{name}': 변수2 최소가 최대보다 큽니다").format(label=label, name=name)); continue
                entry["var2"] = {"label": v2label, "min": _num_out(v2min), "max": _num_out(v2max),
                                 "default": _num_out(v2def)}
                h_test = v2def
            elif "H" in eq.replace("ln(", "").replace("exp(", ""):
                errors.append(tr("{label} '{name}': 식에 H 가 있지만 변수2 라벨이 비어 있습니다")
                              .format(label=label, name=name)); continue
            # 식 평가 검사 (범위 안의 값 또는 10 으로)
            x_test = rmin if (rmin is not None and rmin > 0) else 10.0
            try:
                y = _eval_equation(eq, x_test, h_test)
                if not math.isfinite(y):
                    raise ValueError(tr("결과가 유한하지 않습니다 (Y={y})").format(y=y))
            except Exception as e:
                errors.append(tr("{label} '{name}': 식 평가 실패 — {error}").format(label=label, name=name, error=e))
                continue
            sci_cb(name, g(1))
            result[name] = entry
        return result

    def mark_saved(self, data: dict):
        """저장 완료 후 원본을 갱신하고 '변경 없음' 으로."""
        self._data = data
        self._set_dirty(False)

    # ── 언어 전환 시 표 내용 보존 ─────────────────────────────────
    def snapshot(self) -> dict:
        rows = {}
        for sec, t in self.tables.items():
            sec_rows = []
            for r in range(t.rowCount()):
                cells = [(t.item(r, c).text() if t.item(r, c) else "") for c in range(t.columnCount())]
                if t.item(r, 0):
                    cells[0] = _get_true_name(t.item(r, 0))   # 0열은 항상 저장 키(국문)로 스냅샷
                by_env = _get_by_env(t.item(r, 0)) if (sec == _SECTION_TREE and t.item(r, 0)) else None
                sec_rows.append((cells, by_env))
            rows[sec] = sec_rows
        return {"data": self._data, "dirty": self._dirty, "rows": rows,
                "tab": self.tabs.currentIndex()}

    def restore(self, snap: dict):
        self._loading = True
        try:
            self._data = snap.get("data")
            for sec, t in self.tables.items():
                t.setRowCount(0)
                for cells, by_env in snap["rows"].get(sec, []):
                    r = t.rowCount()
                    t.insertRow(r)
                    true_name = cells[0] if cells else ""
                    sci_name = cells[1] if len(cells) > 1 else ""
                    swap = (_LANG == "en" and bool(sci_name))
                    for c, text in enumerate(cells):
                        if c == 0:
                            it = _mk_item(sci_name if swap else true_name, editable=not swap)
                            _set_true_name(it, true_name)
                        else:
                            editable = not (sec == _SECTION_TREE and c == 10)
                            it = _mk_item(text, editable)
                        t.setItem(r, c, it)
                    if sec == _SECTION_TREE and by_env is not None:
                        _set_by_env(t.item(r, 0), by_env)
                        t.item(r, 10).setText(self._env_summary(by_env))
                _tidy_columns(t)
            self.tabs.setCurrentIndex(snap.get("tab", 0))
        finally:
            self._loading = False
        self._set_dirty(bool(snap.get("dirty")))
        self._sync_buttons()


# ─────────────────────────── 메인 창 ───────────────────────────

class UpdaterWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("수종 데이터 업데이터 (자체 완결형) — 탄소저장량 측정 모듈"))
        self.setMinimumWidth(960)
        self._worker: BuildWorker | None = None
        self._out_user_edited = False   # 출력 폴더를 사용자가 직접 지정했는지
        self._editor_loaded_path: Path | None = None   # 편집기에 올라간 JSON 경로
        self._setup_ui()
        self._auto_detect()

    def _on_language_changed(self, _index: int) -> None:
        """언어를 저장하고 창을 다시 만들어 즉시 반영한다 (입력값은 그대로 유지)."""
        global _LANG
        code = self.lang_combo.currentData()
        if code == _LANG:
            return
        _LANG = code
        _save_language(code)
        self._rebuild_ui()

    def _on_zoom_changed(self, _index: int) -> None:
        """화면 배율을 저장하고 폰트·여백을 다시 계산해 창을 재구성한다."""
        zoom = self.zoom_combo.currentData()
        if zoom is None or abs(zoom - _ZOOM) < 1e-6:
            return
        _save_zoom(zoom)
        _set_ui_scale(zoom)
        _apply_app_font(QApplication.instance())
        self._rebuild_ui()
        _fit_window(self)

    def _rebuild_ui(self) -> None:
        """중앙 위젯을 새로 만들되 입력 경로·편집 중인 표 내용은 그대로 유지한다."""
        keep = (self.json_row.edit.text(), self.out_row.edit.text(),
                self.exe_row.edit.text(), self._out_user_edited)
        snap = self.editor.snapshot()
        self.setWindowTitle(tr("수종 데이터 업데이터 (자체 완결형) — 탄소저장량 측정 모듈"))
        old = self.centralWidget()
        self._setup_ui()
        old.deleteLater()
        # 경로를 되돌릴 때 편집기가 다시 로드되지 않도록 먼저 스냅샷을 복원한다
        self.editor.restore(snap)
        self.json_row.edit.blockSignals(True)
        self.json_row.edit.setText(keep[0])
        self.json_row.edit.blockSignals(False)
        self._recheck_json(load_editor=False)
        self.out_row.edit.setText(keep[1])
        self.exe_row.edit.setText(keep[2])
        self._out_user_edited = keep[3]

    def _setup_ui(self):
        root = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)
        v = QVBoxLayout(root)
        v.setSpacing(_px(10))
        v.setContentsMargins(_px(12), _px(12), _px(12), _px(12))

        # ── 언어 (본 프로그램과 설정을 공유) ─────────────────────────
        lang_row = QHBoxLayout()
        lang_row.addStretch(1)
        lang_row.addWidget(QLabel(tr("언어 / Language")))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("한국어", "ko")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.setCurrentIndex(1 if _LANG == "en" else 0)
        self.lang_combo.setFixedWidth(_px(140))
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(self.lang_combo)
        lang_row.addSpacing(_px(16))
        lang_row.addWidget(QLabel(tr("화면 배율")))
        self.zoom_combo = QComboBox()
        for z, label in _ZOOM_CHOICES:
            self.zoom_combo.addItem(label, z)
        idx = min(range(len(_ZOOM_CHOICES)), key=lambda i: abs(_ZOOM_CHOICES[i][0] - _ZOOM))
        self.zoom_combo.setCurrentIndex(idx)
        self.zoom_combo.setFixedWidth(_px(90))
        self.zoom_combo.currentIndexChanged.connect(self._on_zoom_changed)
        lang_row.addWidget(self.zoom_combo)
        v.addLayout(lang_row)

        # 세 경로 행의 라벨 폭을 현재 폰트로 잰 가장 긴 라벨에 맞춘다 (배율이 커져도 잘리지 않음)
        global _STATUS_INDENT
        fm = self.fontMetrics()
        _label_texts = ("species_data.json", tr("출력 폴더 (exe 저장 위치)"), tr("탄소저장량측정모듈.exe 위치"))
        self._label_w = max(_px(215), max(fm.horizontalAdvance(t) for t in _label_texts) + _px(16))
        _STATUS_INDENT = self._label_w + _px(8)

        # ── 통합 JSON 선택 ─────────────────────────────────────────
        json_grp = QGroupBox(tr("수종 데이터 JSON (통합 species_data.json)"))
        jl = QVBoxLayout(json_grp)
        self.json_row = FilePickRow("species_data.json", label_width=self._label_w)
        self.json_row.btn.clicked.connect(self._pick_json)
        self.json_row.edit.textChanged.connect(self._recheck_json)
        self.json_status = QLabel(tr("— 파일을 선택하면 검증됩니다"))
        self.json_status.setWordWrap(True)      # 긴 메시지가 창 폭을 밀어올리지 않도록
        self.json_status.setStyleSheet(_status_css("gray"))
        jl.addWidget(self.json_row)
        jl.addWidget(self.json_status)
        v.addWidget(json_grp)

        # ── 수종 데이터 편집기 (표) ─────────────────────────────────
        self.editor = SpeciesEditor()
        self.editor.save_requested.connect(self._save_editor)
        v.addWidget(self.editor, 3)

        # ── ① exe 재빌드 (자체 완결) ───────────────────────────────
        build_grp = QGroupBox(tr("① exe 재빌드   —   내장 소스로 새 탄소저장량측정모듈.exe 생성 (권장)"))
        build_grp.setStyleSheet("QGroupBox { font-weight: bold; }")
        bl = QVBoxLayout(build_grp)

        _note = QLabel(
            tr("이 업데이터에 내장된 전체 코드 로직을 사용해 JSON 이 반영된 새 exe 를 만듭니다. "
            "소스 폴더가 옆에 없어도 됩니다.\n"
            "※ 컴파일에는 이 PC 에 Python 3.10 이상이 필요합니다 (최초 1회 빌드 환경 자동 구성)."))
        _note.setStyleSheet(_note_css())
        _note.setWordWrap(True)
        bl.addWidget(_note)

        self.out_row = FilePickRow(tr("출력 폴더 (exe 저장 위치)"), tr("폴더..."), label_width=self._label_w)
        self.out_row.btn.clicked.connect(self._pick_out_dir)
        self.out_row.edit.textEdited.connect(self._mark_out_edited)
        bl.addWidget(self.out_row)

        opt_row = QHBoxLayout()
        self.onedir_cb = QCheckBox(tr("onedir 모드"))
        self.debug_cb  = QCheckBox(tr("디버그 콘솔"))
        self.upx_cb    = QCheckBox(tr("UPX 압축"))
        self.clean_cb  = QCheckBox(tr("캐시 초기화"))
        for cb in (self.onedir_cb, self.debug_cb, self.upx_cb, self.clean_cb):
            opt_row.addWidget(cb)
        opt_row.addStretch()
        bl.addLayout(opt_row)

        self.build_btn = QPushButton(tr("새 exe 빌드 (PyInstaller)"))
        self.build_btn.setFixedHeight(_px(42))
        f = self.build_btn.font(); f.setBold(True)   # 크기는 앱 폰트(스케일 적용)를 그대로 따른다
        self.build_btn.setFont(f)
        self.build_btn.clicked.connect(self._start_build)
        bl.addWidget(self.build_btn)

        self.build_status = QLabel(tr("준비"))
        self.build_status.setAlignment(Qt.AlignCenter)
        bl.addWidget(self.build_status)
        v.addWidget(build_grp)

        # ── ② JSON 적용 (Python 불필요) ────────────────────────────
        apply_grp = QGroupBox(tr("② JSON 적용   —   기존 exe 옆에 복사만 (Python 불필요)"))
        al = QVBoxLayout(apply_grp)
        _anote = QLabel(
            tr("이미 만들어진 탄소저장량측정모듈.exe 가 있다면, 그 옆에 JSON 을 복사해 "
            "다음 실행 시 즉시 반영합니다. 재빌드가 필요 없을 때 사용하세요."))
        _anote.setStyleSheet(_note_css())
        _anote.setWordWrap(True)
        al.addWidget(_anote)

        self.exe_row = FilePickRow(tr("탄소저장량측정모듈.exe 위치"), tr("찾기..."), label_width=self._label_w)
        self.exe_row.btn.clicked.connect(self._pick_exe)
        self.exe_row.edit.textChanged.connect(self._recheck_exe)
        self.exe_status = QLabel("")
        self.exe_status.setWordWrap(True)       # 긴 exe 경로가 창의 최소 폭을 키우지 않도록
        self.exe_status.setStyleSheet(_status_css(None))
        al.addWidget(self.exe_row)
        al.addWidget(self.exe_status)

        self.apply_btn = QPushButton(tr("JSON 적용 (복사)"))
        self.apply_btn.setFixedHeight(_px(36))
        self.apply_btn.clicked.connect(self._apply_json)
        al.addWidget(self.apply_btn)

        self.apply_status = QLabel(tr("준비"))
        self.apply_status.setAlignment(Qt.AlignCenter)
        al.addWidget(self.apply_status)
        v.addWidget(apply_grp)

        # ── 로그 ──────────────────────────────────────────────────
        log_grp = QGroupBox(tr("로그"))
        ll = QVBoxLayout(log_grp)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", _pt(9)))
        self.log.setMinimumHeight(_px(150))
        ll.addWidget(self.log)
        v.addWidget(log_grp, 1)

    # ── 자동 탐색 ──────────────────────────────────────────────────

    def _auto_detect(self):
        # 내장/근처 JSON 자동 채움
        for cand in (HERE / JSON_NAME, SRC_ROOT / JSON_NAME):
            if cand.exists():
                self.json_row.edit.setText(str(cand))
                break
        # 출력 폴더 기본값 = updater 위치
        self.out_row.edit.setText(str(HERE))
        # 기존 exe 자동 탐색
        exe = _auto_find_main_exe()
        if exe:
            self.exe_row.edit.setText(str(exe))

    # ── JSON 선택·검증 ──────────────────────────────────────────────

    def _pick_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("통합 species_data.json 선택"), str(HERE), tr("JSON 파일 (*.json)"))
        if path:
            self.json_row.edit.setText(path)
            # "해당 디렉토리에 빌드" — 출력 폴더를 선택한 JSON 이 있는 폴더로 자동 지정
            # (사용자가 이미 직접 바꾼 경우는 존중)
            if not self._out_user_edited:
                self.out_row.edit.blockSignals(True)
                self.out_row.edit.setText(str(Path(path).parent))
                self.out_row.edit.blockSignals(False)

    def _recheck_json(self, load_editor: bool = True):
        p = self.json_row.path
        if not p:
            self.json_status.setText(tr("— 파일을 선택하면 검증됩니다"))
            self.json_status.setStyleSheet(_status_css("gray"))
        elif p.exists():
            ok, msg = _validate_species_json(p)
            color = "green" if ok else "red"
            mark = "✓" if ok else "✗"
            self.json_status.setText(f"{mark} {msg}")
            self.json_status.setStyleSheet(_status_css(color))
            if ok and load_editor:
                self._load_into_editor(p)
        else:
            self.json_status.setText(tr("파일을 찾을 수 없습니다."))
            self.json_status.setStyleSheet(_status_css("red"))

    def _pick_out_dir(self):
        d = QFileDialog.getExistingDirectory(self, tr("출력 폴더 선택"), str(HERE))
        if d:
            self._out_user_edited = True
            self.out_row.edit.setText(d)

    def _mark_out_edited(self, _text: str):
        self._out_user_edited = True

    # ── exe 선택 (② 모드) ──────────────────────────────────────────

    def _pick_exe(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("탄소저장량측정모듈.exe 선택"), str(HERE), tr("실행 파일 (*.exe)"))
        if path:
            self.exe_row.edit.setText(path)

    def _recheck_exe(self):
        p = self.exe_row.path
        if p and p.exists():
            self.exe_status.setText(f"✓ {p}")
            self.exe_status.setStyleSheet(_status_css("green"))
        elif p:
            self.exe_status.setText(tr("파일을 찾을 수 없습니다."))
            self.exe_status.setStyleSheet(_status_css("red"))
        else:
            self.exe_status.setText("")

    # ── ① exe 재빌드 ────────────────────────────────────────────────

    def _start_build(self):
        if self._worker and self._worker.isRunning():
            return
        if not self._ensure_editor_saved():
            return

        json_path = self.json_row.path
        if not json_path or not json_path.exists():
            self._set_build_status(tr("먼저 species_data.json 을 선택하세요."), "red")
            return
        ok, msg = _validate_species_json(json_path)
        if not ok:
            self._set_build_status(tr("JSON 오류: {msg}").format(msg=msg), "red")
            return

        out_dir = self.out_row.path
        if not out_dir:
            self._set_build_status(tr("출력 폴더를 지정하세요."), "red")
            return

        options: list[str] = []
        if self.onedir_cb.isChecked(): options.append("--onedir")
        if self.debug_cb.isChecked():  options.append("--debug")
        if self.upx_cb.isChecked():    options.append("--upx")
        if self.clean_cb.isChecked():  options.append("--clean-cache")

        self.log.clear()
        self.build_btn.setEnabled(False)
        self._set_build_status(tr("빌드 중..."), "black")

        self._worker = BuildWorker(json_path, out_dir, options)
        self._worker.log_line.connect(self._append_log)
        self._worker.finished.connect(self._on_build_done)
        self._worker.start()

    def _on_build_done(self, success: bool, info: str):
        self.build_btn.setEnabled(True)
        self.log.appendPlainText("=" * 70)
        if success:
            self._set_build_status(tr("빌드 완료!"), "green")
            self.log.appendPlainText(tr("[완료] 새 실행파일: {path}").format(path=info))
        else:
            self._set_build_status(tr("빌드 실패 — 로그 확인"), "red")
            self.log.appendPlainText(tr("[실패] {error}").format(error=info))

    def _set_build_status(self, text: str, color: str):
        self.build_status.setText(text)
        self.build_status.setStyleSheet(f"color: {color};")

    # ── ② JSON 적용 ────────────────────────────────────────────────

    def _apply_json(self):
        if not self._ensure_editor_saved():
            return
        json_path = self.json_row.path
        if not json_path or not json_path.exists():
            self.apply_status.setText(tr("먼저 species_data.json 을 선택하세요."))
            self.apply_status.setStyleSheet("color: red;")
            return
        ok, _ = _validate_species_json(json_path)
        if not ok:
            self.apply_status.setText(tr("JSON 검증에 실패했습니다 (상단 상태 확인)."))
            self.apply_status.setStyleSheet("color: red;")
            return

        exe_path = self.exe_row.path
        if not exe_path or not exe_path.exists():
            self.apply_status.setText(tr("탄소저장량측정모듈.exe 위치를 선택하세요."))
            self.apply_status.setStyleSheet("color: red;")
            return

        target_dir = exe_path.parent
        dst = target_dir / JSON_NAME
        shutil.copy2(json_path, dst)
        # 구버전 분리 JSON 이 남아 통합본을 가리지 않도록 정리
        removed = []
        for _old in ("carbon1_species_data.json", "carbon2_species_data.json"):
            _p = target_dir / _old
            if _p.exists():
                try:
                    _p.unlink()
                    removed.append(_old)
                except Exception:
                    pass

        self.log.clear()
        self.log.appendPlainText(
            tr("[완료] {name} → {path}").format(name=JSON_NAME, path=dst))
        if removed:
            self.log.appendPlainText(
                tr("[정리] 구버전 JSON 제거: {names}").format(names=", ".join(removed)))
        self.log.appendPlainText("")
        self.log.appendPlainText(tr("탄소저장량측정모듈.exe 를 다시 실행하면 새 수종 데이터가 적용됩니다."))
        self.apply_status.setText(tr("완료 — JSON 복사됨"))
        self.apply_status.setStyleSheet("color: green;")

    # ── 수종 데이터 편집기 ───────────────────────────────────────────

    def _load_into_editor(self, path: Path):
        """검증된 JSON 을 표에 올린다. 같은 파일이면 다시 올리지 않는다."""
        try:
            same = self._editor_loaded_path is not None and path.resolve() == self._editor_loaded_path.resolve()
        except OSError:
            same = False
        if same and self.editor.is_loaded():
            return
        if self.editor.is_dirty():
            if QMessageBox.question(
                    self, tr("미저장 변경"), tr("편집 중인 내용을 버리고 새 파일을 불러올까요?"),
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except Exception as e:
            self._append_log(tr("JSON 파싱 오류: {error}").format(error=e))
            return
        self.editor.load(data)
        self._editor_loaded_path = path

    def _save_editor(self) -> bool:
        """표 내용을 검증해 JSON 파일에 쓴다. 성공하면 True."""
        path = self.json_row.path
        if not path:
            QMessageBox.warning(self, tr("검증 실패"),
                                tr("저장할 JSON 파일 경로가 없습니다. 상단에서 species_data.json 을 지정하세요."))
            return False
        errors, data = self.editor.validate_and_build()
        if errors:
            text = "\n".join("• " + e for e in errors[:30])
            if len(errors) > 30:
                text += "\n…"
            QMessageBox.warning(self, tr("검증 실패"),
                                tr("저장 전 검증에 실패했습니다:\n\n{errors}").format(errors=text))
            for e in errors:
                self._append_log("[!] " + e)
            return False
        try:
            if path.exists():
                bak = path.with_suffix(path.suffix + ".bak")
                shutil.copy2(path, bak)
                self._append_log(tr("[백업] 이전 파일 → {path}").format(path=bak))
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding='utf-8')
        except Exception as e:
            QMessageBox.warning(self, tr("검증 실패"), tr("저장 실패: {error}").format(error=e))
            return False
        self.editor.mark_saved(data)
        self._editor_loaded_path = path
        self._recheck_json(load_editor=False)
        self._append_log(tr("[저장] {path}").format(path=path))
        self._append_log(tr("저장 완료 — 교목 {tree} · 관목 {shrub} · 국내 {dom} · 국외 {for_} 종").format(
            tree=len(data.get("TREE_BASE", {})), shrub=len(data.get("SHRUB_SPECIES", {})),
            dom=len(data.get("DOMESTIC_SPECIES", {})), for_=len(data.get("FOREIGN_SPECIES", {}))))
        return True

    def _ensure_editor_saved(self) -> bool:
        """빌드/적용 직전: 미저장 변경이 있으면 저장할지 묻는다. 진행 가능하면 True."""
        if not self.editor.is_dirty():
            return True
        r = QMessageBox.question(
            self, tr("미저장 변경"),
            tr("편집한 수종 데이터가 아직 파일에 저장되지 않았습니다.\n지금 저장하고 계속할까요?\n\n"
               "예 = 저장 후 진행 · 아니요 = 파일의 기존 내용으로 진행 · 취소 = 중단"),
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)
        if r == QMessageBox.Yes:
            return self._save_editor()
        return r == QMessageBox.No

    # ── 로그 ──────────────────────────────────────────────────────

    def _append_log(self, line: str):
        self.log.appendPlainText(line)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())


def main():
    global _LANG
    _enable_high_dpi()                   # QApplication 생성 전
    app = QApplication(sys.argv)
    _LANG = _current_language()          # 본 프로그램에서 고른 언어를 그대로 따른다
    _set_ui_scale(_load_zoom())          # 모니터 크기 × 저장된 배율
    _apply_app_font(app)
    win = UpdaterWindow()
    _fit_window(win)                     # 화면 비율로 크기·중앙 배치 (화면 초과 방지)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
