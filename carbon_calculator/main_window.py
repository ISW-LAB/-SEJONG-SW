# -*- coding: utf-8 -*-
"""
복원본지 탄소저장량 측정 모듈 - PyQt5 메인 윈도우.

레이아웃:
- 좌측: TabWidget 2개 (교목 / 관목)
    * 각 탭 상단에 "추가" 버튼 → 팝업 다이얼로그로 1행 추가
    * 추가된 행은 스크롤 영역에 누적되며 각 행마다 [삭제] 버튼 보유
- 우측 상단: 게이지 3개 (교목/관목/총합) + 숫자 표시
- 우측 중단: 그래프 sub tab 4개 (교목 추정 / 교목 기여도 / 관목 추정 / 관목 기여도)
- 우측 하단: 결과 테이블 (그래프 ↔ 테이블 세로 스플리터)
"""
from __future__ import annotations

import datetime
import io
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFileDialog, QFormLayout, QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSpinBox,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .calculations import (
    CarbonRow, RangeViolation, calculate_carbon, project_future_carbon,
)
from .data import (
    DEFAULT_ENVIRONMENT, SpeciesData, shrub_species_for_env, tree_species_for_env,
)
from .excel_export import export_carbon1_to_excel
from .plotting import MatplotlibCanvas
from .ui_scale import apply_dialog_size, pt, px
from .widgets import (
    LinearGauge, NoWheelComboBox, NoWheelDoubleSpinBox, NoWheelSpinBox, ResultTable,
    SearchableComboBox,
)
from .tree_simulation.models import VisualizationInputGroup
from .tree_simulation.snapshot import build_snapshot, input_fingerprint
from .tree_simulation.visualization_tab import VegetationVisualizationTab


# 한 행의 계산 결과 + 그래프 투영에 필요한 모든 정보를 담는 경량 컨테이너.
# label / curve 는 계산 후 `_build_curves` 에서 채워진다 (50년 투영 곡선).
@dataclass
class _Entry:
    species: str
    species_data: SpeciesData  # 오버라이드가 적용된 최종 계수
    diameter: float
    quantity: int
    carbon_kg: float
    unit: str
    label: str = ""
    curve: object = None       # numpy 배열 (연도별 탄소저장량) — _build_curves 에서 설정


# 사용자 편집 가능한 (a, b, CF) 오버라이드 타입.
OverrideCoeffs = Tuple[float, float, float]


def _coeffs_equal(a1: OverrideCoeffs, a2: OverrideCoeffs, tol: float = 1e-9) -> bool:
    return all(abs(x - y) <= tol for x, y in zip(a1, a2))


# ------------------------------ 입력 다이얼로그 ------------------------------

class AddSpeciesDialog(QDialog):
    """
    수종/직경/수량 + 상대생장식 (a, b, CF) 편집 다이얼로그.

    좌측 패널: 카테고리(수종) · 변수(DBH/RCD) · 개수(수량)
    우측 패널:
      (1) 상대생장식 [a, b, CF 편집 가능 — 수정하면 그 행 계산에 반영]
      (2) CSV 권장 정보 (유효 범위, 성장차 - 읽기 전용)
    """

    def __init__(self, kind: str, species_map: dict, names: list, parent=None):
        super().__init__(parent)
        self.kind = kind  # "tree" or "shrub"
        is_tree = kind == "tree"

        self.setWindowTitle("교목 추가" if is_tree else "관목 추가")
        self.setModal(True)
        apply_dialog_size(self, 820, 500)

        # 환경별로 해석된 수종 맵/목록을 호출측(MainWindow)에서 주입받는다.
        self._species_map = species_map
        self._diameter_unit = "cm" if is_tree else "mm"
        diameter_label = f"변수 ({'DBH' if is_tree else 'RCD'} · {self._diameter_unit})"
        diameter_max = 50 if is_tree else 100

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self._build_left_panel(names, diameter_label, diameter_max), 1)
        body.addWidget(self._build_right_panel(), 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("추가 (Ctrl+Enter)")
        buttons.button(QDialogButtonBox.Cancel).setText("취소")
        # 일반 Enter 로는 추가되지 않도록 기본 버튼 해제 (keyPressEvent 에서 Ctrl+Enter 만 허용)
        buttons.button(QDialogButtonBox.Ok).setAutoDefault(False)
        buttons.button(QDialogButtonBox.Ok).setDefault(False)
        buttons.button(QDialogButtonBox.Cancel).setAutoDefault(False)
        buttons.button(QDialogButtonBox.Cancel).setDefault(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(body, 1)
        layout.addWidget(buttons)

        # 콤보 변경 시 우측 정보 자동 갱신 + 기본값 로드
        self.combo.currentIndexChanged.connect(
            lambda _i: self._on_species_changed(self.combo.currentText())
        )
        self.a_spin.valueChanged.connect(self._refresh_formula)
        self.b_spin.valueChanged.connect(self._refresh_formula)
        self.cf_spin.valueChanged.connect(self._refresh_formula)
        self._on_species_changed(self.combo.currentText())

    def keyPressEvent(self, event) -> None:
        """일반 Enter 로는 닫히지 않게 하고, Ctrl+Enter 일 때만 '추가'(accept)."""
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ControlModifier:
                self.accept()
            # 일반 Enter: 다이얼로그 동작 없음 (검색창 추천 선택은 별도 처리됨)
            event.accept()
            return
        super().keyPressEvent(event)

    # ----- 좌/우 패널 빌드 -----

    def _build_left_panel(self, names: List[str], diameter_label: str, diameter_max: int) -> QWidget:
        group = QGroupBox("입력")
        form = QFormLayout(group)
        form.setSpacing(10)

        self.combo = SearchableComboBox("🔍 수종 검색 (예: 소나무, 회양목)")
        self.combo.set_items([(n, n) for n in names])
        form.addRow("카테고리 (수종)", self.combo)

        # 직경: 입력 자체는 제한하지 않고 넓게 연다 (검증은 '추가' 클릭 시 수행).
        # diameter_max 는 더 이상 입력 상한이 아니며 표시용 정보로만 쓰인다.
        self.diameter_spin = NoWheelSpinBox()
        self.diameter_spin.setRange(1, 100000)
        self.diameter_spin.setValue(1)
        form.addRow(diameter_label, self.diameter_spin)

        self.quantity_spin = NoWheelSpinBox()
        self.quantity_spin.setRange(1, 99999)
        self.quantity_spin.setValue(1)
        form.addRow("개수 (수량)", self.quantity_spin)

        return group

    def _build_right_panel(self) -> QWidget:
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        # (1) 상대생장식 편집
        eq_group = QGroupBox("(1) 상대생장식 — 값 수정 시 이 행의 계산에 반영")
        eq_layout = QVBoxLayout(eq_group)
        eq_layout.setSpacing(8)

        self.formula_label = QLabel()
        self.formula_label.setStyleSheet(
            "background: #F0F8F0; padding: 8px; border: 1px solid #C8E0C8; "
            "border-radius: 3px; font-weight: bold;"
        )
        self.formula_label.setAlignment(Qt.AlignCenter)
        eq_layout.addWidget(self.formula_label)

        form = QFormLayout()
        form.setSpacing(8)

        self.a_spin = NoWheelDoubleSpinBox()
        self.a_spin.setRange(0.0, 9999.0)
        self.a_spin.setDecimals(8)
        self.a_spin.setSingleStep(0.0001)
        form.addRow("계수 a", self.a_spin)

        self.b_spin = NoWheelDoubleSpinBox()
        self.b_spin.setRange(0.0, 20.0)
        self.b_spin.setDecimals(4)
        self.b_spin.setSingleStep(0.01)
        form.addRow("지수 b", self.b_spin)

        self.cf_spin = NoWheelDoubleSpinBox()
        self.cf_spin.setRange(0.0, 1.0)
        self.cf_spin.setDecimals(2)
        self.cf_spin.setSingleStep(0.05)
        form.addRow("탄소전환계수 CF", self.cf_spin)
        eq_layout.addLayout(form)

        reset_btn = QPushButton("기본값으로 복원")
        reset_btn.clicked.connect(self._reset_to_defaults)
        eq_layout.addWidget(reset_btn, alignment=Qt.AlignRight)
        v.addWidget(eq_group)

        # (2) CSV 권장 정보 (읽기 전용)
        info_group = QGroupBox("(2) CSV 권장 정보 (읽기 전용)")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(6)

        self.range_value_label = QLabel("-")
        info_layout.addRow("유효 직경 범위", self.range_value_label)

        self.growth_value_label = QLabel("-")
        info_layout.addRow("성장차 (1-10/11-20/21+ 년, cm/yr)", self.growth_value_label)

        self.default_coeffs_label = QLabel("-")
        self.default_coeffs_label.setStyleSheet("color: #555;")
        info_layout.addRow("기본 (a, b, CF)", self.default_coeffs_label)

        v.addWidget(info_group)
        v.addStretch(1)
        return wrap

    # ----- 이벤트 -----

    def _on_species_changed(self, species: str) -> None:
        sp = self._species_map.get(species)
        if sp is None:
            return
        # 우측 편집 스피너 = 기본값
        self.a_spin.blockSignals(True); self.b_spin.blockSignals(True); self.cf_spin.blockSignals(True)
        self.a_spin.setValue(sp.a)
        self.b_spin.setValue(sp.b)
        self.cf_spin.setValue(sp.cf)
        self.a_spin.blockSignals(False); self.b_spin.blockSignals(False); self.cf_spin.blockSignals(False)
        # 직경 입력은 제한하지 않는다(범위 밖 값도 입력 가능). 다만 수종을 바꿨을 때
        # 현재 값이 새 수종의 유효 범위를 벗어나면 유효 최소값으로 한 번 맞춰 주어
        # 합리적인 기본값에서 시작하도록 한다(사용자는 이후 자유롭게 수정 가능).
        d = self.diameter_spin.value()
        if d < sp.diameter_min or d > sp.diameter_max:
            self.diameter_spin.setValue(int(sp.diameter_min))
        # CSV 정보 표시
        u = self._diameter_unit
        self.range_value_label.setText(f"{sp.diameter_min:g} {u} ~ {sp.diameter_max:g} {u}")
        self.growth_value_label.setText(
            f"{sp.growth_y10:.2f}  /  {sp.growth_y20:.2f}  /  {sp.growth_y21:.2f}"
        )
        self.default_coeffs_label.setText(f"a = {sp.a:g} ,  b = {sp.b:g} ,  CF = {sp.cf:g}")
        self._refresh_formula()

    def _refresh_formula(self) -> None:
        a = self.a_spin.value()
        b = self.b_spin.value()
        cf = self.cf_spin.value()
        self.formula_label.setText(
            f"Y  =  {a:g}  ×  X^{b:g}      C  =  Y  ×  {cf:g}  ×  N"
        )

    def _reset_to_defaults(self) -> None:
        sp = self._species_map.get(self.combo.currentText())
        if sp is None:
            return
        self.a_spin.setValue(sp.a)
        self.b_spin.setValue(sp.b)
        self.cf_spin.setValue(sp.cf)

    def accept(self) -> None:
        """'추가' 시 유효 직경 범위를 검증. 범위 밖이면 경고 후 다이얼로그를 닫지 않는다."""
        species = self.combo.currentText()
        sp = self._species_map.get(species)
        if sp is not None:
            d = self.diameter_spin.value()
            if d < sp.diameter_min or d > sp.diameter_max:
                u = self._diameter_unit
                QMessageBox.warning(
                    self, "유효 직경 범위 아님",
                    f"입력한 직경 {d:g}{u} 은(는) '{species}'의 유효 범위"
                    f"({sp.diameter_min:g}{u} ~ {sp.diameter_max:g}{u})를 벗어납니다.\n\n"
                    f"값을 유효 범위 안으로 수정한 뒤 다시 [추가]를 눌러 주세요.",
                )
                self.diameter_spin.setFocus()
                self.diameter_spin.selectAll()
                return  # 다이얼로그 유지 — 행은 추가되지 않음
        super().accept()

    # ----- 결과 -----

    def values(self) -> Tuple[str, int, int, Optional[OverrideCoeffs]]:
        """
        Returns: (species, diameter, quantity, override_coeffs_or_None)
        override_coeffs 는 a/b/CF 중 하나라도 기본값에서 변경된 경우에만 (a, b, cf) 튜플.
        """
        species = self.combo.currentText()
        diameter = self.diameter_spin.value()
        quantity = self.quantity_spin.value()

        current: OverrideCoeffs = (self.a_spin.value(), self.b_spin.value(), self.cf_spin.value())
        sp = self._species_map.get(species)
        default: OverrideCoeffs = (sp.a, sp.b, sp.cf) if sp else (0.0, 0.0, 0.0)
        override = None if _coeffs_equal(current, default) else current

        return species, diameter, quantity, override


# ------------------------------ 동적 입력 행 --------------------------------

class SpeciesInputRow(QFrame):
    """수종(콤보) + 직경(스피너) + 수량(스피너) + [삭제] 한 행. 인라인 편집 가능.

    `override_coeffs` 가 주어지면 해당 행은 사용자 정의 (a, b, CF) 로 계산된다.
    인라인 콤보(수종)를 변경하면 오버라이드는 자동으로 해제되고 기본값으로 복귀.
    """

    deleted = pyqtSignal(object)         # emits self

    def __init__(self, kind: str, species: str, diameter: int, quantity: int,
                 names: list, override_coeffs: Optional[OverrideCoeffs] = None, parent=None):
        super().__init__(parent)
        self.kind = kind
        is_tree = kind == "tree"
        self._override_coeffs: Optional[OverrideCoeffs] = override_coeffs
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "QFrame { background: #FBFDFC; border: 1px solid #DCE1E6; border-radius: 8px; }"
        )

        diameter_label = "DBH(cm)" if is_tree else "RCD(mm)"
        diameter_max = 50 if is_tree else 100

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(4)

        # 1행: 수종 콤보 + 삭제 버튼
        # (그래프 표시 토글은 우측 추정 그래프 옆의 체크박스 범례에서 항목별로 제어한다)
        top = QHBoxLayout()
        top.setSpacing(4)
        self.combo = NoWheelComboBox()
        self.combo.addItems(names)
        if species in names:
            self.combo.setCurrentText(species)
        # 반응형: 패널을 좁혀도 콤보가 줄어들어 삭제 버튼이 항상 보이도록.
        # (긴 수종명 때문에 최소 너비가 커져 행이 뷰포트를 넘기는 문제 방지)
        self.combo.setSizeAdjustPolicy(NoWheelComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo.setMinimumContentsLength(3)
        self.combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo.setToolTip(self.combo.currentText())
        self.combo.currentTextChanged.connect(self._on_species_changed)
        top.addWidget(self.combo, 1)

        self.delete_button = QPushButton("삭제")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.setFixedWidth(px(54))
        self.delete_button.clicked.connect(self._on_delete)
        top.addWidget(self.delete_button)
        outer.addLayout(top)

        # 2행: 직경
        d_row = QHBoxLayout()
        d_row.setSpacing(4)
        d_label = QLabel(diameter_label)
        d_label.setMinimumWidth(px(60))
        d_row.addWidget(d_label)
        self.diameter_spin = NoWheelSpinBox()
        self.diameter_spin.setRange(1, diameter_max)
        self.diameter_spin.setValue(max(1, int(diameter)))
        d_row.addWidget(self.diameter_spin, 1)
        outer.addLayout(d_row)

        # 3행: 수량
        q_row = QHBoxLayout()
        q_row.setSpacing(4)
        q_label = QLabel("수량")
        q_label.setMinimumWidth(px(60))
        q_row.addWidget(q_label)
        self.quantity_spin = NoWheelSpinBox()
        self.quantity_spin.setRange(0, 99999)
        self.quantity_spin.setValue(max(0, int(quantity)))
        q_row.addWidget(self.quantity_spin, 1)
        outer.addLayout(q_row)

        # 4행: 오버라이드 표시 라벨 (수정된 a/b/CF 가 적용된 경우만 표시)
        self.override_label = QLabel()
        self.override_label.setStyleSheet(
            "color: #C0392B; font-style: italic; padding: 0 2px;"
        )
        self.override_label.setVisible(False)
        outer.addWidget(self.override_label)
        self._refresh_override_label()

    def _on_delete(self) -> None:
        self.deleted.emit(self)

    def _on_species_changed(self, _new: str) -> None:
        # 좁아진 콤보에서 텍스트가 잘려도 전체 수종명을 툴팁으로 확인 가능
        self.combo.setToolTip(_new)
        # 수종을 인라인 변경하면 오버라이드 해제 (기본 계수로 복원)
        if self._override_coeffs is not None:
            self._override_coeffs = None
            self._refresh_override_label()

    def _refresh_override_label(self) -> None:
        if self._override_coeffs is None:
            self.override_label.setVisible(False)
            return
        a, b, cf = self._override_coeffs
        self.override_label.setText(
            f"⚙ 사용자 식 적용: a={a:g}, b={b:g}, CF={cf:g}"
        )
        self.override_label.setVisible(True)

    def values(self) -> Tuple[str, int, int]:
        return self.combo.currentText(), self.diameter_spin.value(), self.quantity_spin.value()

    def override_coeffs(self) -> Optional[OverrideCoeffs]:
        return self._override_coeffs


# ------------------------------ 메인 윈도우 ----------------------------------

class MainWindow(QMainWindow):

    def __init__(self, environment: str = DEFAULT_ENVIRONMENT,
                 region_name: str = "", area_w: int = 0, area_h: int = 0):
        super().__init__()
        self.setWindowTitle("복원본지 탄소저장량 측정 모듈 (Ver. 1.1 - Python)")
        # 창 크기는 combined_window(통합 실행 진입점 main.py) 에서 설정.
        # centralWidget 만 사용되므로 이 창 자체의 크기는 영향 없음.

        # 지역 메타데이터(통합창에서 주입) — Excel 자동 네이밍·요약 시트에 사용.
        self.region_name = region_name
        self.area_w = area_w
        self.area_h = area_h

        # 복원 환경(유형)에 따라 교목 계수/성장차가 매핑된다 (관목은 현재 환경 무관).
        self.environment = environment
        self._tree_species = tree_species_for_env(environment)
        self._shrub_species = shrub_species_for_env(environment)
        self._tree_names = list(self._tree_species.keys())
        self._shrub_names = list(self._shrub_species.keys())

        self.tree_rows: List[SpeciesInputRow] = []
        self.shrub_rows: List[SpeciesInputRow] = []

        # 마지막 계산 결과 캐시 — Excel 저장·체크박스 범례 재렌더에 사용.
        #   _{kind}_entries : List[_Entry] (각 항목의 곡선 curve/label 포함, 계산 후 채워짐)
        #   _{kind}_years   : 연도축 배열 (0~50) 또는 None (아직 계산 전/유효 항목 없음)
        #   _{kind}_checks  : 항목별 표시 체크박스 (entries 와 같은 순서)
        #   _{kind}_total_cb: "총 탄소저장량" 표시 체크박스 또는 None (항목 2개 미만이면 None)
        self._tree_entries: List[_Entry] = []
        self._shrub_entries: List[_Entry] = []
        self._tree_years = None
        self._shrub_years = None
        self._tree_checks: List[QCheckBox] = []
        self._shrub_checks: List[QCheckBox] = []
        self._tree_total_cb: Optional[QCheckBox] = None
        self._shrub_total_cb: Optional[QCheckBox] = None

        self._build_ui()

    # ----- UI 구성 -----

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        left = self._build_left_panel()
        right = self._build_right_panel()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        # 반응형: 입력 패널(좌)은 폭을 유지하고, 창을 키우면 그래프/결과(우)가 확장.
        splitter.setChildrenCollapsible(False)
        left.setMinimumWidth(px(300))
        left.setMaximumWidth(px(560))
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([px(340), px(1000)])
        root.addWidget(splitter)

    def _build_left_panel(self) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        # 교목 탭
        tree_tab, self.tree_rows_layout = self._build_input_tab("tree", "+ 교목 추가")
        tabs.addTab(tree_tab, "교목")

        # 관목 탭
        shrub_tab, self.shrub_rows_layout = self._build_input_tab("shrub", "+ 관목 추가")
        tabs.addTab(shrub_tab, "관목")

        # 하단 보조 버튼 행: [전체 초기화] [Excel로 저장]
        actions = QHBoxLayout()
        actions.setSpacing(6)
        self.clear_button = QPushButton("전체 초기화")
        self.clear_button.setObjectName("deleteButton")
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.clicked.connect(self.on_clear)
        actions.addWidget(self.clear_button)

        self.save_button = QPushButton("Excel로 저장")
        self.save_button.setObjectName("accentButton")
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.clicked.connect(self.on_save_excel)
        actions.addWidget(self.save_button)
        layout.addLayout(actions)

        # 계산 버튼 (주 액션 — 스타일은 전역 테마의 #calcButton 규칙)
        self.calc_button = QPushButton("계   산")
        self.calc_button.setObjectName("calcButton")
        font = QFont()
        font.setPointSize(pt(18))
        font.setBold(True)
        self.calc_button.setFont(font)
        self.calc_button.setCursor(Qt.PointingHandCursor)
        self.calc_button.clicked.connect(self.on_calculate)
        layout.addWidget(self.calc_button)

        return wrap

    def _build_input_tab(self, kind: str, add_button_text: str) -> Tuple[QWidget, QVBoxLayout]:
        """수종 입력 탭 1개 구성. (탭위젯, 행 컨테이너 레이아웃) 반환."""
        tab = QWidget()
        v = QVBoxLayout(tab)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(6)

        # 상단 추가 버튼 (스타일은 전역 테마의 #accentButton 규칙)
        add_btn = QPushButton(add_button_text)
        add_btn.setObjectName("accentButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(lambda _checked=False, k=kind: self._open_add_dialog(k))
        v.addWidget(add_btn)

        # 스크롤 가능한 행 컨테이너
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        # 가로 스크롤 금지 → 행이 패널 폭에 맞춰 줄어들고 삭제 버튼이 잘리지 않음
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        rows_layout = QVBoxLayout(container)
        rows_layout.setContentsMargins(2, 2, 2, 2)
        rows_layout.setSpacing(6)
        rows_layout.addStretch(1)  # 행은 stretch 위로 추가됨

        scroll.setWidget(container)
        v.addWidget(scroll, 1)

        # 안내 라벨 (행이 비었을 때 보임)
        empty_hint = QLabel("아직 추가된 항목이 없습니다.\n위의 추가 버튼을 눌러 입력하세요.")
        empty_hint.setAlignment(Qt.AlignCenter)
        empty_hint.setStyleSheet("color: #888; padding: 12px;")
        # 안내는 스크롤 컨테이너 내부에 함께 둠
        rows_layout.insertWidget(0, empty_hint)
        if kind == "tree":
            self._tree_empty_hint = empty_hint
        else:
            self._shrub_empty_hint = empty_hint

        return tab, rows_layout

    def _open_add_dialog(self, kind: str) -> None:
        if kind == "tree":
            species_map, names = self._tree_species, self._tree_names
        else:
            species_map, names = self._shrub_species, self._shrub_names
        dlg = AddSpeciesDialog(kind, species_map, names, self)
        if dlg.exec_() != QDialog.Accepted:
            return
        species, diameter, quantity, override = dlg.values()
        self._append_row(kind, species, diameter, quantity, override_coeffs=override)

    def _append_row(self, kind: str, species: str, diameter: int, quantity: int,
                    override_coeffs: Optional[OverrideCoeffs] = None) -> None:
        names = self._tree_names if kind == "tree" else self._shrub_names
        row = SpeciesInputRow(kind, species, diameter, quantity, names,
                              override_coeffs=override_coeffs)
        row.deleted.connect(self._on_row_deleted)

        if kind == "tree":
            self.tree_rows.append(row)
            layout = self.tree_rows_layout
            self._tree_empty_hint.setVisible(False)
        else:
            self.shrub_rows.append(row)
            layout = self.shrub_rows_layout
            self._shrub_empty_hint.setVisible(False)

        # stretch 바로 앞에 삽입 (rows_layout에 stretch가 마지막에 있음)
        insert_index = layout.count() - 1
        layout.insertWidget(insert_index, row)

    def _on_row_deleted(self, row: "SpeciesInputRow") -> None:
        if row in self.tree_rows:
            self.tree_rows.remove(row)
            if not self.tree_rows:
                self._tree_empty_hint.setVisible(True)
        elif row in self.shrub_rows:
            self.shrub_rows.remove(row)
            if not self.shrub_rows:
                self._shrub_empty_hint.setVisible(True)
        row.setParent(None)
        row.deleteLater()

    def _build_right_panel(self) -> QWidget:
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        # 게이지 3개
        self.tree_gauge = LinearGauge(0, 2000, [0, 500, 1000, 1500, 2000])
        self.shrub_gauge = LinearGauge(0, 100, [0, 20, 40, 60, 80, 100])
        self.total_gauge = LinearGauge(0, 3000, [0, 500, 1000, 1500, 2000, 2500, 3000])

        self.tree_value_label = self._make_value_field("0.00")
        self.shrub_value_label = self._make_value_field("0.00")
        self.total_value_label = self._make_value_field("0.00")

        v.addLayout(self._gauge_row("교목 탄소저장량 (kgC)", self.tree_gauge, self.tree_value_label))
        v.addLayout(self._gauge_row("관목 탄소저장량 (kgC)", self.shrub_gauge, self.shrub_value_label))
        v.addLayout(self._gauge_row("총 탄소저장량 (kgC)",  self.total_gauge, self.total_value_label))

        # 그래프 영역: [교목 추정 / 교목 기여도 / 관목 추정 / 관목 기여도] sub tab.
        # 2-row 동시 배치는 그래프가 작아 보이므로, 각 그래프가 전체 영역을 차지하도록 탭 분리.
        self.tree_canvas = MatplotlibCanvas(width=7, height=4)
        self.tree_canvas.show_message("계산 버튼을 눌러주세요")
        self.tree_pie_canvas = MatplotlibCanvas(width=5, height=4)
        self.tree_pie_canvas.show_message("계산 버튼을 눌러주세요")
        self.shrub_canvas = MatplotlibCanvas(width=7, height=4)
        self.shrub_canvas.show_message("계산 버튼을 눌러주세요")
        self.shrub_pie_canvas = MatplotlibCanvas(width=5, height=4)
        self.shrub_pie_canvas.show_message("계산 버튼을 눌러주세요")

        graph_tabs = QTabWidget()
        graph_tabs.setDocumentMode(True)
        graph_tabs.addTab(self._build_estimation_tab("tree"), "교목 추정")
        graph_tabs.addTab(self._build_pie_tab("tree"), "교목 기여도")
        graph_tabs.addTab(self._build_estimation_tab("shrub"), "관목 추정")
        graph_tabs.addTab(self._build_pie_tab("shrub"), "관목 기여도")
        # 지역별 3D 시각화는 독립 모듈에 위임한다. 기존 계산/그래프 경로에는 개입하지 않는다.
        self.visualization_tab = VegetationVisualizationTab(
            snapshot_provider=self._build_visualization_snapshot,
            fingerprint_provider=self._visualization_fingerprint,
            parent=self,
        )
        graph_tabs.addTab(self.visualization_tab, "시각화")

        # 결과 테이블
        tables_widget = QWidget()
        tables = QHBoxLayout(tables_widget)
        tables.setContentsMargins(0, 0, 0, 0)
        self.tree_table = self._make_result_table()
        self.shrub_table = self._make_result_table()
        tables.addLayout(self._table_box("교목 결과 (DBH·cm)", self.tree_table))
        tables.addLayout(self._table_box("관목 결과 (RCD·mm)", self.shrub_table))

        # 그래프(sub tab) ↔ 결과 테이블 사이 높이를 세로 드래그로 조절
        body_splitter = QSplitter(Qt.Vertical)
        body_splitter.setChildrenCollapsible(False)
        body_splitter.addWidget(graph_tabs)
        body_splitter.addWidget(tables_widget)
        body_splitter.setStretchFactor(0, 3)
        body_splitter.setStretchFactor(1, 1)
        body_splitter.setSizes([px(680), px(200)])
        v.addWidget(body_splitter, 1)

        return wrap

    def _build_estimation_tab(self, kind: str) -> QWidget:
        """추정 곡선 sub tab: [항목별 표시 체크박스 범례] + [추정 곡선 캔버스]."""
        canvas = self.tree_canvas if kind == "tree" else self.shrub_canvas

        wrap = QFrame()
        wrap.setFrameShape(QFrame.StyledPanel)
        col = QVBoxLayout(wrap)
        col.setContentsMargins(2, 2, 2, 2)
        col.setSpacing(2)

        legend_scroll = QScrollArea()
        legend_scroll.setWidgetResizable(True)
        legend_scroll.setFrameShape(QFrame.NoFrame)
        legend_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        legend_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        legend_scroll.setFixedHeight(px(34))
        legend_host = QWidget()
        legend_layout = QHBoxLayout(legend_host)
        legend_layout.setContentsMargins(4, 0, 4, 0)
        legend_layout.setSpacing(px(12))
        legend_layout.addStretch(1)
        legend_scroll.setWidget(legend_host)
        col.addWidget(legend_scroll)

        canvas.setMinimumWidth(px(220))
        col.addWidget(canvas, 1)

        if kind == "tree":
            self._tree_legend_layout = legend_layout
        else:
            self._shrub_legend_layout = legend_layout
        return wrap

    def _build_pie_tab(self, kind: str) -> QWidget:
        """기여도 파이 sub tab."""
        canvas = self.tree_pie_canvas if kind == "tree" else self.shrub_pie_canvas
        wrap = QFrame()
        wrap.setFrameShape(QFrame.StyledPanel)
        col = QVBoxLayout(wrap)
        col.setContentsMargins(2, 2, 2, 2)
        col.addWidget(canvas, 1)
        return wrap

    def _make_value_field(self, initial: str) -> QLabel:
        lbl = QLabel(initial)
        lbl.setMinimumWidth(px(130))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            "background: #FFFFFF; border: 1px solid #C4CCD3; "
            "border-radius: 6px; padding: 6px; color: #246B43;"
        )
        font = QFont()
        font.setPointSize(pt(15))
        font.setBold(True)
        lbl.setFont(font)
        return lbl

    def _gauge_row(self, title: str, gauge: LinearGauge, value_label: QLabel) -> QHBoxLayout:
        row = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setMinimumWidth(px(150))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-weight: bold;")
        row.addWidget(title_label)
        row.addWidget(gauge, 1)
        row.addWidget(value_label)
        return row

    def _make_result_table(self) -> QTableWidget:
        # 수종(0열)이 flex — 남는 폭을 흡수해 패널 폭에 정확히 맞춤
        table = ResultTable(flex_col=0)
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["수종", "직경", "수량", "탄소량(kgC)"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)

        # 테이블 값/헤더 글꼴 대폭 확대 — 본문 폰트보다 +4pt
        tfont = table.font()
        base = tfont.pointSize() if tfont.pointSize() > 0 else 12
        tfont.setPointSize(base + 4)
        table.setFont(tfont)

        # 숫자 열 기본 너비(드래그 조절 가능). 수종 열은 ResultTable 이 잔여 폭으로 채움.
        table.setColumnWidth(1, px(90))    # 직경
        table.setColumnWidth(2, px(80))    # 수량
        table.setColumnWidth(3, px(130))   # 탄소량
        # 행 높이는 글꼴 크기에 맞춰 자동
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        return table

    def _table_box(self, title: str, table: QTableWidget) -> QVBoxLayout:
        box = QVBoxLayout()
        lbl = QLabel(title)
        # 결과 섹션 제목 — 강조색 + 본문 폰트보다 +3pt
        title_font = lbl.font()
        base = title_font.pointSize() if title_font.pointSize() > 0 else 12
        title_font.setPointSize(base + 3)
        title_font.setBold(True)
        lbl.setFont(title_font)
        lbl.setStyleSheet("color: #246B43;")
        box.addWidget(lbl)
        box.addWidget(table)
        return box

    # ----- 동작 -----

    def on_calculate(self) -> None:
        tree_entries, total_tree, tree_qty, w_tree = self._collect_entries("tree")
        shrub_entries, total_shrub, shrub_qty, w_shrub = self._collect_entries("shrub")

        # 다음 계산/저장에서 재사용할 수 있도록 캐시.
        self._tree_entries = tree_entries
        self._shrub_entries = shrub_entries

        # 결과 테이블
        self._populate_table(self.tree_table, [self._entry_to_row(e) for e in tree_entries])
        self._populate_table(self.shrub_table, [self._entry_to_row(e) for e in shrub_entries])

        # 게이지 + 숫자
        self.tree_gauge.setValue(total_tree)
        self.shrub_gauge.setValue(total_shrub)
        grand_total = total_tree + total_shrub
        self.total_gauge.setValue(grand_total)
        self.tree_value_label.setText(f"{round(total_tree, 2):,.2f}")
        self.shrub_value_label.setText(f"{round(total_shrub, 2):,.2f}")
        self.total_value_label.setText(f"{round(grand_total, 2):,.2f}")

        # 추정 그래프(체크박스 범례) + 기여도 파이
        self._build_curves("tree", tree_entries)
        self._build_curves("shrub", shrub_entries)
        self._build_legend("tree", tree_entries)
        self._build_legend("shrub", shrub_entries)
        self._render_projection("tree")
        self._render_projection("shrub")
        self._render_pie("tree", tree_entries)
        self._render_pie("shrub", shrub_entries)

        # (요구사항 4) 총 개수 1,000 초과 경고 — 계산은 이미 끝났고, 막지 않는다.
        count_warnings: List[str] = []
        if tree_qty > 1000:
            count_warnings.append(f"교목 총 개수가 {tree_qty:,}주로 1,000주를 초과합니다.")
        if shrub_qty > 1000:
            count_warnings.append(f"관목 총 개수가 {shrub_qty:,}주로 1,000주를 초과합니다.")

        # 경고 표시 (범위 위반 → 대량 입력 순). 어느 쪽도 계산을 중단시키지 않는다.
        warnings = w_tree + w_shrub
        if warnings:
            QMessageBox.warning(
                self, "입력값 오류 (해당 행 제외)", "\n".join(warnings)
            )
        if count_warnings:
            QMessageBox.warning(
                self, "대량 입력 경고",
                "\n".join(count_warnings) + "\n\n계산은 정상적으로 수행되었습니다.",
            )

    def on_clear(self) -> None:
        """입력 행·결과 테이블·게이지·그래프를 모두 비운다 (누적/캐시 방지)."""
        # 입력 행 전부 제거 (교목·관목)
        for row in list(self.tree_rows) + list(self.shrub_rows):
            row.setParent(None)
            row.deleteLater()
        self.tree_rows.clear()
        self.shrub_rows.clear()
        self._tree_empty_hint.setVisible(True)
        self._shrub_empty_hint.setVisible(True)

        # 결과·캐시 비우기
        self.tree_table.setRowCount(0)
        self.shrub_table.setRowCount(0)
        self._tree_entries = []
        self._shrub_entries = []
        self._tree_years = None
        self._shrub_years = None
        # 체크박스 범례 비우고 stretch 만 남김
        self._clear_layout(self._tree_legend_layout)
        self._tree_legend_layout.addStretch(1)
        self._clear_layout(self._shrub_legend_layout)
        self._shrub_legend_layout.addStretch(1)
        self._tree_checks = []
        self._shrub_checks = []
        self._tree_total_cb = None
        self._shrub_total_cb = None

        # 게이지·숫자 초기화
        self.tree_gauge.setValue(0)
        self.shrub_gauge.setValue(0)
        self.total_gauge.setValue(0)
        self.tree_value_label.setText("0.00")
        self.shrub_value_label.setText("0.00")
        self.total_value_label.setText("0.00")

        # 그래프·파이 초기 메시지로 복귀
        self.tree_canvas.show_message("계산 버튼을 눌러주세요")
        self.shrub_canvas.show_message("계산 버튼을 눌러주세요")
        self.tree_pie_canvas.show_message("계산 버튼을 눌러주세요")
        self.shrub_pie_canvas.show_message("계산 버튼을 눌러주세요")

    @staticmethod
    def _entry_to_row(e: _Entry) -> CarbonRow:
        return CarbonRow(e.species, e.diameter, e.quantity, e.carbon_kg)

    def region_total_carbon(self) -> Tuple[float, float, float]:
        """현재 입력 기준 (교목 합, 관목 합, 총합) — 지역 종합 분석에서 사용.

        UI 부수효과·경고창 없이 합계만 계산한다(범위 위반 행은 제외).
        """
        _te, total_tree, _tq, _wt = self._collect_entries("tree")
        _se, total_shrub, _sq, _ws = self._collect_entries("shrub")
        return total_tree, total_shrub, total_tree + total_shrub

    def _collect_entries(self, kind: str) -> Tuple[List[_Entry], float, int, List[str]]:
        """입력 행을 순회해 유효 행의 `_Entry` 리스트·합계·총 수량·경고 메시지를 반환.

        반환하는 `total_qty` 는 **입력된 전체 수량**(직경 범위를 벗어나 결과에서 제외된
        행의 수량도 포함)이다. 1,000 초과 경고가 "입력한 그루 수" 기준이 되도록 하기 위함.

        범위 위반 행은 경고에 누적하고 결과(합계·테이블)에서 제외하지만, 호출측에서 경고를
        한 번에 표시하도록 여기서는 메시지박스를 띄우지 않는다.
        """
        if kind == "tree":
            input_rows = self.tree_rows
            species_map = self._tree_species
            unit = "cm"
        else:
            input_rows = self.shrub_rows
            species_map = self._shrub_species
            unit = "mm"

        entries: List[_Entry] = []
        total = 0.0
        total_qty = 0
        warnings: List[str] = []
        for input_row in input_rows:
            species_name, diameter, quantity = input_row.values()
            if quantity <= 0:
                continue
            base = species_map.get(species_name)
            if base is None:
                continue
            # 입력된 전체 수량 누적 (범위 위반으로 곧 제외될 행도 포함) — 1,000 초과 경고용.
            total_qty += quantity
            # 행에 사용자 정의 (a, b, CF) 가 있으면 임시 SpeciesData 구성.
            override = input_row.override_coeffs()
            if override is not None:
                a, b, cf = override
                species_data = SpeciesData(
                    a=a, b=b, cf=cf,
                    diameter_min=base.diameter_min,
                    diameter_max=base.diameter_max,
                    growth_y10=base.growth_y10,
                    growth_y20=base.growth_y20,
                    growth_y21=base.growth_y21,
                )
            else:
                species_data = base
            try:
                row = calculate_carbon(species_name, species_data, diameter, quantity, unit)
            except RangeViolation as e:
                warnings.append(str(e))
                continue
            if row is not None:
                entries.append(_Entry(
                    species=species_name, species_data=species_data,
                    diameter=diameter, quantity=quantity, carbon_kg=row.carbon_kg, unit=unit,
                ))
                total += row.carbon_kg

        return entries, total, total_qty, warnings

    # ----- 지역별 3D 시각화 adapter -----

    def _visualization_inputs(self) -> Tuple[tuple[VisualizationInputGroup, ...], tuple[str, ...]]:
        """현재 입력 위젯을 3D 전용 plain DTO로 복사한다.

        `_Entry`나 마지막 계산 캐시에 의존하지 않으며, 기존 계산과 동일하게 범위 밖 행은
        제외한다. 이 메서드 이후의 모든 처리는 tree_simulation 패키지가 담당한다.
        """
        result: list[VisualizationInputGroup] = []
        warnings: list[str] = []
        for kind, input_rows, species_map, unit in (
            ("tree", self.tree_rows, self._tree_species, "cm"),
            ("shrub", self.shrub_rows, self._shrub_species, "mm"),
        ):
            for input_row in input_rows:
                species, diameter, quantity = input_row.values()
                if quantity <= 0:
                    continue
                base = species_map.get(species)
                if base is None:
                    continue
                if diameter < base.diameter_min or diameter > base.diameter_max:
                    warnings.append(
                        f"{species}: 유효 범위 {base.diameter_min:g}~"
                        f"{base.diameter_max:g}{unit} 밖의 입력은 제외됨"
                    )
                    continue
                override = input_row.override_coeffs()
                if override is None:
                    species_data = base
                else:
                    a, b, cf = override
                    species_data = SpeciesData(
                        a=a, b=b, cf=cf,
                        diameter_min=base.diameter_min,
                        diameter_max=base.diameter_max,
                        growth_y10=base.growth_y10,
                        growth_y20=base.growth_y20,
                        growth_y21=base.growth_y21,
                    )
                result.append(VisualizationInputGroup(
                    species=species,
                    kind=kind,
                    diameter=float(diameter),
                    quantity=int(quantity),
                    diameter_unit=unit,
                    species_data=species_data,
                ))
        return tuple(result), tuple(warnings)

    def _visualization_fingerprint(self) -> str:
        inputs, _warnings = self._visualization_inputs()
        return input_fingerprint(
            self.region_name, self.environment, self.area_w, self.area_h, inputs,
        )

    def _build_visualization_snapshot(self):
        inputs, warnings = self._visualization_inputs()
        return build_snapshot(
            region_name=self.region_name,
            environment=self.environment,
            area_w=self.area_w,
            area_h=self.area_h,
            inputs=inputs,
            warnings=warnings,
        )

    def _populate_table(self, table: QTableWidget, rows: List[CarbonRow]) -> None:
        table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row.as_table_row()):
                text = str(val)
                item = QTableWidgetItem(text)
                # 수종(0열)은 좌측 정렬(긴 이름 가독), 숫자 열은 가운데 정렬
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if j == 0 else Qt.AlignCenter))
                item.setToolTip(text)  # 잘려도 전체 값을 툴팁으로 확인
                table.setItem(i, j, item)
        # 패널 폭에 맞춰 열 너비 재조정 (수종 열이 잔여 폭 흡수)
        if isinstance(table, ResultTable):
            table.fit_columns()

    # ----- 그래프 (추정 곡선 · 기여도 파이) -----

    @staticmethod
    def _clear_layout(layout) -> None:
        """레이아웃의 모든 항목(위젯·스페이서)을 제거한다."""
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    @staticmethod
    def _sum_carbon(carbons: list):
        """탄소량 배열 리스트의 연도별 합 (입력이 비면 None). 새 배열을 만들어 반환."""
        total = None
        for c in carbons:
            total = c if total is None else total + c
        return total

    def _build_curves(self, kind: str, entries: List[_Entry]) -> None:
        """각 항목을 독립적으로 50년 투영해 entry.curve/label 에 채우고 연도축을 캐시."""
        mm = (kind == "shrub")
        years_ref = None
        for e in entries:
            years, carbon = project_future_carbon(
                e.species_data, e.diameter, e.quantity, years=50, mm_scale=mm,
            )
            e.curve = carbon
            e.label = f"{e.species} ({e.diameter:g}{e.unit}·{e.quantity:g}주)"
            years_ref = years
        if kind == "tree":
            self._tree_years = years_ref
        else:
            self._shrub_years = years_ref

    def _build_legend(self, kind: str, entries: List[_Entry]) -> None:
        """추정 그래프 위에 항목별 표시 체크박스 + '총 탄소저장량' 체크박스를 동적으로 구성.

        각 체크박스를 켜고 끄면 즉시 해당 분류의 추정 그래프가 다시 그려진다 (요구사항 2).
        """
        layout = self._tree_legend_layout if kind == "tree" else self._shrub_legend_layout
        self._clear_layout(layout)

        checks: List[QCheckBox] = []
        for e in entries:
            cb = QCheckBox(e.label)
            cb.setChecked(True)
            cb.setToolTip(f"{e.label} 곡선 표시")
            cb.toggled.connect(lambda _c, k=kind: self._render_projection(k))
            layout.addWidget(cb)
            checks.append(cb)

        total_cb = None
        if len(entries) >= 2:  # 항목이 2개 이상일 때만 총합 곡선/체크박스 제공
            total_cb = QCheckBox("총 탄소저장량")
            total_cb.setChecked(True)
            total_cb.setToolTip("전체 항목 합계 곡선 표시")
            total_cb.setStyleSheet("QCheckBox { color: #C0392B; font-weight: bold; }")
            total_cb.toggled.connect(lambda _c, k=kind: self._render_projection(k))
            layout.addWidget(total_cb)

        layout.addStretch(1)
        if kind == "tree":
            self._tree_checks, self._tree_total_cb = checks, total_cb
        else:
            self._shrub_checks, self._shrub_total_cb = checks, total_cb

    def _render_projection(self, kind: str) -> None:
        """범례 체크박스 상태에 따라 추정 그래프를 다시 그린다.

        - 체크된 각 항목 → 개별 곡선.
        - '총 탄소저장량' 체크 → 전체 항목 합계 곡선(개별 체크와 독립적으로 토글).
        - 아무것도 체크되지 않으면 안내 메시지를 표시.
        """
        if kind == "tree":
            canvas, entries, years = self.tree_canvas, self._tree_entries, self._tree_years
            checks, total_cb, label_kr = self._tree_checks, self._tree_total_cb, "교목"
        else:
            canvas, entries, years = self.shrub_canvas, self._shrub_entries, self._shrub_years
            checks, total_cb, label_kr = self._shrub_checks, self._shrub_total_cb, "관목"

        if years is None or not entries:
            canvas.show_message(f"{label_kr} 정보 없음")
            return

        series: list = []
        for e, cb in zip(entries, checks):
            if cb.isChecked():
                series.append((e.label, years, e.curve, False))

        # '총 탄소저장량' = 전체 항목의 연도별 합 (개별 항목 체크 여부와 무관하게 토글).
        if total_cb is not None and total_cb.isChecked():
            series.append(("총 탄소저장량", years, self._sum_carbon([e.curve for e in entries]), True))

        if not series:
            canvas.show_message(f"{label_kr}: 표시할 항목을 선택하세요 (그래프 위 체크박스)")
            return

        # 제목은 패널 상단 라벨로 표시하므로 축 제목은 끈다 (그래프 영역 확보).
        canvas.plot_multi_projection(
            series, f"[{label_kr}] 향후 50년 탄소저장량 변동 추정", show_title=False,
        )

    def _render_pie(self, kind: str, entries: List[_Entry]) -> None:
        """수종별 탄소저장량 기여도 파이차트를 그린다 (기여도 sub tab)."""
        canvas = self.tree_pie_canvas if kind == "tree" else self.shrub_pie_canvas
        label_kr = "교목" if kind == "tree" else "관목"
        values = [e.carbon_kg for e in entries]
        if not entries or sum(values) <= 0:
            canvas.show_message(f"[{label_kr}]\n기여도 없음")
            return
        labels = [e.species for e in entries]
        # 제목은 패널 상단 라벨로 표시하므로 차트 제목은 끈다.
        canvas.plot_pie(
            labels, values, title=f"{label_kr} 수종별 기여도",
            top_n=5, label_fs=10, title_fs=12, show_title=False,
        )

    # ----- Excel 저장 (요구사항 3) -----

    def on_save_excel(self) -> None:
        # 화면(마지막 계산)과 저장 내용을 일치시키기 위해, 아직 계산 전이면 먼저 계산한다.
        if self._tree_years is None and self._shrub_years is None:
            self.on_calculate()
        if not self._tree_entries and not self._shrub_entries:
            QMessageBox.information(
                self, "저장할 내용 없음",
                "저장할 입력/결과가 없습니다. 먼저 항목을 추가한 뒤 [계 산]을 눌러 주세요.",
            )
            return

        # 통합 창에 임베드된 경우 MainWindow 자체는 표시되지 않으므로, 화면에 보이는
        # 최상위 창(통합 윈도우 또는 단독 창)을 부모로 삼아 다이얼로그가 올바른 위치에 뜨게 한다.
        parent = QApplication.activeWindow() or self
        # 지역별 자동 파일명: 지역명이 있으면 '탄소저장량_<지역명>.xlsx'.
        default_name = (f"탄소저장량_{self._safe_filename(self.region_name)}.xlsx"
                        if self.region_name else "탄소저장량_결과.xlsx")
        path, _filter = QFileDialog.getSaveFileName(
            parent, "Excel로 저장", default_name, "Excel 파일 (*.xlsx)",
        )
        if not path:
            return  # 사용자가 취소
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        payload = self._build_export_payload()

        try:
            export_carbon1_to_excel(path, payload)
        except PermissionError:
            QMessageBox.warning(
                self, "저장 실패",
                "파일이 다른 프로그램(Excel 등)에서 열려 있어 저장할 수 없습니다.\n"
                "해당 파일을 닫고 다시 시도해 주세요.",
            )
            return
        except Exception as exc:  # noqa: BLE001 — 사용자에게 원인 안내
            QMessageBox.warning(self, "저장 실패", f"저장 중 오류가 발생했습니다:\n{exc}")
            return

        QMessageBox.information(
            self, "저장 완료", f"현재 화면(마지막 계산) 기준으로 저장되었습니다:\n{path}",
        )

    @staticmethod
    def _safe_filename(name: str) -> str:
        """파일명에 부적합한 문자를 _ 로 치환한 안전한 이름."""
        cleaned = re.sub(r'[\\/:*?"<>|]+', "_", (name or "").strip())
        return cleaned or "지역"

    def _render_graph_images(self) -> list:
        """현재 4개 그래프(교목/관목 × 추정/기여도)를 PNG 바이트로 렌더 → Excel 임베드용."""
        specs = [
            ("교목 향후 50년 탄소저장량 변동 추정", self.tree_canvas),
            ("교목 수종별 기여도", self.tree_pie_canvas),
            ("관목 향후 50년 탄소저장량 변동 추정", self.shrub_canvas),
            ("관목 수종별 기여도", self.shrub_pie_canvas),
        ]
        images = []
        for title, canvas in specs:
            try:
                buf = io.BytesIO()
                # 그림은 constrained_layout 으로 이미 정돈됨(범례 포함). 그대로 PNG 저장.
                canvas.figure.savefig(buf, format="png", dpi=150)
                images.append({"title": title, "png": buf.getvalue()})
            except Exception:  # noqa: BLE001 — 이미지 실패해도 나머지 저장은 진행
                continue
        return images

    def build_export_payload(self):
        """공개 래퍼: 계산 결과가 없으면 None, 있으면 export payload dict를 반환."""
        if not self._tree_entries and not self._shrub_entries:
            return None
        return self._build_export_payload()

    def _build_export_payload(self) -> dict:
        total_tree = sum(e.carbon_kg for e in self._tree_entries)
        total_shrub = sum(e.carbon_kg for e in self._shrub_entries)
        return {
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "grand_total": total_tree + total_shrub,
            "region": {
                "name": self.region_name,
                "environment": self.environment,
                "area_w": self.area_w,
                "area_h": self.area_h,
                "area": self.area_w * self.area_h,
            },
            "tree": self._payload_for("tree", total_tree),
            "shrub": self._payload_for("shrub", total_shrub),
            "images": self._render_graph_images(),
        }

    def _payload_for(self, kind: str, total: float) -> dict:
        if kind == "tree":
            entries, years, checks = self._tree_entries, self._tree_years, self._tree_checks
        else:
            entries, years, checks = self._shrub_entries, self._shrub_years, self._shrub_checks
        unit = "cm" if kind == "tree" else "mm"

        rows = [
            {
                "species": e.species, "diameter": e.diameter, "quantity": e.quantity,
                "carbon": e.carbon_kg,
                "checked": (checks[i].isChecked() if i < len(checks) else True),
                "a": e.species_data.a, "b": e.species_data.b, "cf": e.species_data.cf,
                "dmin": e.species_data.diameter_min, "dmax": e.species_data.diameter_max,
            }
            for i, e in enumerate(entries)
        ]
        total_qty = sum(e.quantity for e in entries)

        projection = None
        if years is not None and entries:
            # 저장 파일에는 '총 탄소저장량'(전체 항목 합)을 기록 — 항목이 2개 이상일 때만.
            grand = self._sum_carbon([e.curve for e in entries]) if len(entries) >= 2 else None
            projection = {
                "years": [int(y) for y in years],
                "series": [
                    {
                        "label": e.label,
                        "checked": (checks[i].isChecked() if i < len(checks) else True),
                        "carbon": [float(x) for x in e.curve],
                    }
                    for i, e in enumerate(entries)
                ],
                "total": ([float(x) for x in grand] if grand is not None else None),
            }

        contribution = []
        if total > 0:
            agg: dict = {}
            for e in entries:
                agg[e.species] = agg.get(e.species, 0.0) + e.carbon_kg
            for species_name, val in sorted(agg.items(), key=lambda kv: -kv[1]):
                contribution.append({
                    "species": species_name, "carbon": val, "percent": val / total * 100,
                })

        return {
            "unit": unit, "total": total, "total_qty": total_qty,
            "rows": rows, "projection": projection, "contribution": contribution,
        }
