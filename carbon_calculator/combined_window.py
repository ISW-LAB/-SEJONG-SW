# -*- coding: utf-8 -*-
"""
통합 메인 윈도우 — **지역(권역)별 동적 탭** 관리 (Ver. 4.4).

- 상단 탭은 지역별로 동적으로 추가/삭제된다. 좌상단 [+ 지역 추가] 로 팝업을 띄워
  지역명·면적(가로×세로 m)·환경(산불피해지 자연복원/인공복원/채석장 인공복원)을 입력하면
  그 지역명을 라벨로 하는 새 탭(자생복원종 탄소저장량 추정 + 기여도 화면)이 생성된다.
- 우상단 [지역 종합 분석] 으로 모든 지역의 총 탄소저장량을 비교하는 대시보드를 연다.
- 국내·국외 통합 기여도(Carbon2) 모듈은 화면에 노출하지 않되 코드/인스턴스/수식은 보존한다.
"""
from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAction, QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QSpinBox, QStatusBar,
    QTabBar, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from .data import RESTORATION_ENVIRONMENTS
from .excel_export import export_all_regions_to_excel
from .main_window import MainWindow as Carbon1Window
from .main_window2 import Carbon2MainWindow
from .plotting import MatplotlibCanvas
from .ui_scale import apply_dialog_size, apply_window_size, pt, px


# 환경(복원 유형) 선택지 — data.py 를 단일 출처로 사용 (교목 계수/성장차 매핑 키와 일치).
ENVIRONMENTS = RESTORATION_ENVIRONMENTS


# ------------------------------ 지역 추가 다이얼로그 ------------------------------

class AddRegionDialog(QDialog):
    """지역명 · 면적(가로×세로 m) · 환경 입력 모달."""

    def __init__(self, existing_names: List[str], parent=None):
        super().__init__(parent)
        self._existing = set(existing_names)
        self.setWindowTitle("지역 추가")
        self.setModal(True)
        apply_dialog_size(self, 460, 320)

        form = QFormLayout()
        form.setSpacing(12)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("예: 세종, 청주, 오송 ...")
        form.addRow("지역명", self.name_edit)

        # 면적: 가로 × 세로 (m), 기본 20 × 20
        area_row = QHBoxLayout()
        area_row.setSpacing(6)
        self.w_spin = QSpinBox(); self.w_spin.setRange(1, 100000); self.w_spin.setValue(20)
        self.w_spin.setSuffix(" m")
        self.h_spin = QSpinBox(); self.h_spin.setRange(1, 100000); self.h_spin.setValue(20)
        self.h_spin.setSuffix(" m")
        area_row.addWidget(self.w_spin, 1)
        area_row.addWidget(QLabel("×"))
        area_row.addWidget(self.h_spin, 1)
        area_wrap = QWidget(); area_wrap.setLayout(area_row)
        form.addRow("면적 (가로 × 세로)", area_wrap)

        self.env_combo = QComboBox()
        self.env_combo.addItems(ENVIRONMENTS)
        form.addRow("환경 (복원 유형)", self.env_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("추가")
        buttons.button(QDialogButtonBox.Cancel).setText("취소")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form, 1)
        layout.addWidget(buttons)

        self.name_edit.setFocus()

    def accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "입력 필요", "지역명을 입력해 주세요.")
            self.name_edit.setFocus()
            return
        if name in self._existing:
            QMessageBox.warning(self, "중복된 지역명",
                                f"‘{name}’ 지역이 이미 있습니다. 다른 이름을 사용해 주세요.")
            self.name_edit.setFocus()
            self.name_edit.selectAll()
            return
        super().accept()

    def values(self):
        """(지역명, 가로 m, 세로 m, 환경) 반환."""
        return (self.name_edit.text().strip(),
                self.w_spin.value(), self.h_spin.value(),
                self.env_combo.currentText())


# ------------------------------ 지역 선택 다이얼로그 ------------------------------

class RegionSelectDialog(QDialog):
    """종합 분석에 포함할 지역을 체크박스로 선택하는 모달 (기본 전체 선택)."""

    def __init__(self, names: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("지역 선택 — 종합 분석")
        self.setModal(True)
        apply_dialog_size(self, 420, 460)

        v = QVBoxLayout(self)
        v.addWidget(QLabel("비교 분석할 지역을 선택하세요 (2개 이상 권장):"))

        self.list = QListWidget()
        for name in names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.list.addItem(item)
        v.addWidget(self.list, 1)

        # 전체 선택/해제
        toggle_row = QHBoxLayout()
        all_btn = QPushButton("전체 선택")
        all_btn.clicked.connect(lambda: self._set_all(Qt.Checked))
        none_btn = QPushButton("전체 해제")
        none_btn.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        toggle_row.addWidget(all_btn)
        toggle_row.addWidget(none_btn)
        toggle_row.addStretch(1)
        v.addLayout(toggle_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("분석")
        buttons.button(QDialogButtonBox.Cancel).setText("취소")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

    def _set_all(self, state) -> None:
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(state)

    def selected_indices(self) -> List[int]:
        return [i for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.Checked]


# ------------------------------ 지역 종합 분석 대시보드 ------------------------------

class RegionComparisonDialog(QDialog):
    """지역별 총 탄소저장량 비교 대시보드 (막대 차트 + 표)."""

    def __init__(self, data: List[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("지역 종합 분석")
        self.setModal(True)
        # 대시보드는 크게 (화면을 넘지 않도록 apply_dialog_size 가 자동 클램프).
        apply_dialog_size(self, 1280, 860)

        v = QVBoxLayout(self)
        v.setSpacing(8)

        title = QLabel("지역별 탄소저장량 비교")
        tf = title.font(); tf.setPointSize(pt(16)); tf.setBold(True)
        title.setFont(tf); title.setStyleSheet("color: #246B43;")
        v.addWidget(title)

        # 합계 요약
        grand = sum(d["total"] for d in data)
        if data:
            top = max(data, key=lambda d: d["total"])
            summary = (f"총 {len(data)}개 지역 · 전체 합계 {grand:,.2f} kgC"
                       f"   |   최대: {top['name']} ({top['total']:,.2f} kgC)")
        else:
            summary = "지역 데이터 없음"
        sub = QLabel(summary); sub.setStyleSheet("color: #555;")
        v.addWidget(sub)

        # 막대 차트 (지역별 총 탄소저장량 비교 — 지역마다 색상+해치 구분)
        canvas = MatplotlibCanvas(width=10, height=4.6)
        canvas.plot_region_bars(
            [d["name"] for d in data],
            [d["tree"] for d in data],
            [d["shrub"] for d in data],
            show_title=False,
        )
        v.addWidget(canvas, 3)

        # 비교 표
        table = QTableWidget()
        headers = ["지역", "면적(㎡)", "환경", "교목(kgC)", "관목(kgC)",
                   "총 탄소저장량(kgC)", "단위면적당(kgC/㎡)"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(data))
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for i, d in enumerate(data):
            cells = [
                d["name"],
                f"{d['area']:,}",
                d["env"],
                f"{d['tree']:,.2f}",
                f"{d['shrub']:,.2f}",
                f"{d['total']:,.2f}",
                f"{d['density']:,.4f}",
            ]
            for j, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if j in (0, 2) else Qt.AlignCenter))
                table.setItem(i, j, item)
        v.addWidget(table, 2)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setText("닫기")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        v.addWidget(buttons)


# ------------------------------ 통합 메인 윈도우 ------------------------------

class CombinedMainWindow(QMainWindow):
    """지역별 동적 탭을 관리하는 최상위 윈도우."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("복원본지 탄소저장량 측정 모듈 - 통합 (Ver. 4.4)")
        apply_window_size(self, wfrac=0.84, hfrac=0.88, min_w=1100, min_h=680)

        # 지역 목록: 각 항목 {name, w, h, env, window(Carbon1Window), container}
        self._regions: List[dict] = []
        self._placeholder: Optional[QWidget] = None

        # 국내·국외 통합(Carbon2)은 화면에 노출하지 않되 코드/수식 재사용을 위해 인스턴스 보존.
        self._carbon2 = Carbon2MainWindow()

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.North)
        tabs.setDocumentMode(False)
        tabs.setMovable(True)
        tabs.setTabsClosable(True)
        tabs.tabCloseRequested.connect(self._close_region)
        tab_font = QFont(); tab_font.setPointSize(pt(13)); tab_font.setBold(True)
        tabs.tabBar().setFont(tab_font)

        # 좌상단 [+ 지역 추가], 우상단 [지역 종합 분석]
        add_btn = QPushButton("+ 지역 추가")
        add_btn.setObjectName("accentButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_region)
        tabs.setCornerWidget(add_btn, Qt.TopLeftCorner)

        # 우상단 버튼 컨테이너 — 지역 종합 분석 + 통합 Excel 저장
        right_corner = QWidget()
        right_layout = QHBoxLayout(right_corner)
        right_layout.setContentsMargins(0, 0, 4, 0)
        right_layout.setSpacing(6)

        dash_btn = QPushButton("지역 종합 분석")
        dash_btn.setObjectName("accentButton")
        dash_btn.setCursor(Qt.PointingHandCursor)
        dash_btn.clicked.connect(self._open_dashboard)

        export_btn = QPushButton("통합 Excel 저장")
        export_btn.setObjectName("accentButton")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_all_regions_excel)

        right_layout.addWidget(dash_btn)
        right_layout.addWidget(export_btn)
        tabs.setCornerWidget(right_corner, Qt.TopRightCorner)

        self._tabs = tabs
        self.setCentralWidget(tabs)
        self._set_placeholder(True)

        self._build_menu()
        self._build_statusbar()

    # ----- 지역 추가/삭제 -----

    def _add_region(self) -> None:
        dlg = AddRegionDialog([r["name"] for r in self._regions], self)
        if dlg.exec_() != QDialog.Accepted:
            return
        name, w, h, env = dlg.values()
        self._create_region(name, w, h, env)

    def _create_region(self, name: str, w: int, h: int, env: str) -> int:
        """지역 탭을 생성하고 추가한다. 추가된 탭 인덱스를 반환."""
        self._set_placeholder(False)
        # 지역의 환경(복원 유형)·이름·면적을 Carbon1 에 전달 → 계수 매핑 + Excel 자동 네이밍/요약.
        window = Carbon1Window(environment=env, region_name=name, area_w=w, area_h=h)
        container = self._wrap_region(window, name, w, h, env)
        idx = self._tabs.addTab(container, name)
        self._tabs.setTabToolTip(idx, f"{name} · {w}×{h} m · {env}")
        self._regions.append({
            "name": name, "w": w, "h": h, "env": env,
            "window": window, "container": container,
        })
        self._tabs.setCurrentIndex(idx)
        self._status_label.setText(
            f"‘{name}’ 지역 추가됨 — 교목/관목 탭에서 [+ 추가] 후 [계 산]. "
            f"여러 지역은 우상단 [지역 종합 분석]으로 비교."
        )
        return idx

    def _wrap_region(self, window: Carbon1Window, name: str, w: int, h: int, env: str) -> QWidget:
        """지역 정보 배너 + Carbon1 화면을 묶은 탭 컨테이너."""
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(6)
        banner = QLabel(
            f"📍 지역: <b>{name}</b>　|　면적: {w} × {h} m  (<b>{w * h:,}</b> ㎡)　|　"
            f"환경: <b>{env}</b>"
        )
        banner.setStyleSheet(
            "background: #EEF4EF; border: 1px solid #D8E3DB; border-radius: 6px; "
            "padding: 6px 10px; color: #246B43;"
        )
        v.addWidget(banner)
        v.addWidget(window.centralWidget(), 1)
        return container

    def _close_region(self, index: int) -> None:
        widget = self._tabs.widget(index)
        region = next((r for r in self._regions if r["container"] is widget), None)
        if region is None:
            return  # 안내(placeholder) 등 지역이 아닌 탭은 무시
        if QMessageBox.question(
            self, "지역 삭제",
            f"‘{region['name']}’ 지역을 삭제할까요? 입력/결과가 사라집니다.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        self._tabs.removeTab(index)
        self._regions.remove(region)
        region["window"].close()
        region["window"].deleteLater()
        region["container"].deleteLater()
        if not self._regions:
            self._set_placeholder(True)

    def _set_placeholder(self, visible: bool) -> None:
        """지역이 없을 때 안내용 탭을 표시/제거한다."""
        if visible:
            if self._placeholder is not None:
                return
            hint = QLabel(
                "‘+ 지역 추가’ 버튼으로 지역을 추가하세요.\n\n"
                "각 지역은 독립적인 [자생복원종 탄소저장량 추정 + 기여도] 화면을 가지며,\n"
                "여러 지역을 추가한 뒤 우상단 [지역 종합 분석]으로 총 탄소저장량을 비교할 수 있습니다."
            )
            hint.setAlignment(Qt.AlignCenter)
            hint.setStyleSheet("color: #888; padding: 24px;")
            self._placeholder = hint
            idx = self._tabs.addTab(hint, "안내")
            # 안내 탭에는 닫기 버튼을 두지 않는다.
            self._tabs.tabBar().setTabButton(idx, QTabBar.RightSide, None)
            self._tabs.tabBar().setTabButton(idx, QTabBar.LeftSide, None)
        else:
            if self._placeholder is None:
                return
            i = self._tabs.indexOf(self._placeholder)
            if i >= 0:
                self._tabs.removeTab(i)
            self._placeholder.deleteLater()
            self._placeholder = None

    # ----- 지역 종합 분석 -----

    def _regions_in_tab_order(self) -> List[dict]:
        """현재 탭 순서대로 정렬된 지역 목록 (안내 placeholder 탭은 자연히 제외)."""
        by_container = {r["container"]: r for r in self._regions}
        ordered = []
        for i in range(self._tabs.count()):
            r = by_container.get(self._tabs.widget(i))
            if r is not None:
                ordered.append(r)
        return ordered

    def _open_dashboard(self) -> None:
        if not self._regions:
            QMessageBox.information(
                self, "지역 없음",
                "분석할 지역이 없습니다. ‘+ 지역 추가’로 지역을 먼저 추가해 주세요.",
            )
            return

        # 탭을 드래그로 옮겨도 선택 목록 순서가 화면 탭 순서와 일치하도록 탭 순서로 정렬.
        ordered = self._regions_in_tab_order()

        # 비교할 지역을 사용자가 선택 (기본 전체 선택).
        sel = RegionSelectDialog([r["name"] for r in ordered], self)
        if sel.exec_() != QDialog.Accepted:
            return
        indices = sel.selected_indices()
        if not indices:
            QMessageBox.information(
                self, "선택 필요", "비교할 지역을 1개 이상 선택해 주세요.",
            )
            return

        data: List[dict] = []
        for i in indices:
            r = ordered[i]
            tree, shrub, total = r["window"].region_total_carbon()
            area = r["w"] * r["h"]
            data.append({
                "name": r["name"], "w": r["w"], "h": r["h"], "area": area,
                "env": r["env"], "tree": tree, "shrub": shrub, "total": total,
                "density": (total / area if area else 0.0),
            })
        RegionComparisonDialog(data, self).exec_()

    def _export_all_regions_excel(self) -> None:
        """선택한 지역들의 탄소저장량 추정치·기여도·비교분석·그래프를 통합 Excel로 저장."""
        if not self._regions:
            QMessageBox.information(
                self, "지역 없음",
                "내보낼 지역이 없습니다. '+ 지역 추가'로 지역을 먼저 추가해 주세요.",
            )
            return

        ordered = self._regions_in_tab_order()
        sel = RegionSelectDialog([r["name"] for r in ordered], self)
        if sel.exec_() != QDialog.Accepted:
            return
        indices = sel.selected_indices()
        if not indices:
            QMessageBox.information(self, "선택 필요", "내보낼 지역을 1개 이상 선택해 주세요.")
            return

        payloads        = []
        comparison_data = []
        skipped         = []
        for i in indices:
            r       = ordered[i]
            payload = r["window"].build_export_payload()
            if payload is None:
                skipped.append(r["name"])
                continue
            payloads.append(payload)
            tree, shrub, total = r["window"].region_total_carbon()
            area = r["w"] * r["h"]
            comparison_data.append({
                "name": r["name"], "w": r["w"], "h": r["h"], "area": area,
                "env": r["env"], "tree": tree, "shrub": shrub, "total": total,
                "density": (total / area if area else 0.0),
            })

        if not payloads:
            QMessageBox.information(
                self, "저장할 내용 없음",
                "선택한 지역에 계산 결과가 없습니다.\n"
                "각 지역에서 항목을 추가한 뒤 [계 산]을 눌러 주세요.",
            )
            return

        if skipped:
            QMessageBox.information(
                self, "일부 지역 제외",
                f"계산 결과가 없어 제외된 지역: {', '.join(skipped)}\n"
                "나머지 지역으로 내보내기를 진행합니다.",
            )

        parent = QApplication.activeWindow() or self
        path, _ = QFileDialog.getSaveFileName(
            parent, "통합 Excel로 저장", "탄소저장량_통합분석.xlsx", "Excel 파일 (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        try:
            export_all_regions_to_excel(path, payloads, comparison_data)
        except PermissionError:
            QMessageBox.warning(
                self, "저장 실패",
                "파일이 다른 프로그램(Excel 등)에서 열려 있어 저장할 수 없습니다.\n"
                "해당 파일을 닫고 다시 시도해 주세요.",
            )
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "저장 실패", f"저장 중 오류가 발생했습니다:\n{exc}")
            return

        QMessageBox.information(
            self, "저장 완료",
            f"통합 분석 결과가 저장되었습니다:\n{path}\n\n"
            f"포함된 시트: 지역별_추정치 · 탄소_기여도 · 지역_비교분석 · 그래프",
        )

    # ----- 메뉴/상태바 -----

    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("파일(&F)")
        export_action = QAction("통합 Excel 저장(&E)", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export_all_regions_excel)
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        exit_action = QAction("종료(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(exit_action)

        region_menu = menubar.addMenu("지역(&R)")
        add_action = QAction("지역 추가(&A)", self)
        add_action.setShortcut("Ctrl+T")
        add_action.triggered.connect(self._add_region)
        region_menu.addAction(add_action)
        dash_action = QAction("지역 종합 분석(&D)", self)
        dash_action.setShortcut("Ctrl+D")
        dash_action.triggered.connect(self._open_dashboard)
        region_menu.addAction(dash_action)

        help_menu = menubar.addMenu("도움말(&H)")
        about_action = QAction("정보(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _build_statusbar(self) -> None:
        bar = QStatusBar()
        self._status_label = QLabel("‘+ 지역 추가’로 지역을 추가하세요.")
        bar.addWidget(self._status_label, 1)
        version_label = QLabel("Carbon1 v4.x · 통합(지역별) v4.4")
        version_label.setStyleSheet("color: #777;")
        bar.addPermanentWidget(version_label)
        self.setStatusBar(bar)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "복원본지 탄소저장량 측정 모듈",
            "<b>복원본지 탄소저장량 측정 모듈 (통합 Ver. 4.4)</b><br><br>"
            "지역(권역)별로 탭을 동적으로 추가해 각 지역의 <b>탄소저장량 추정 + 수종별 기여도</b>를 "
            "독립적으로 다룹니다.<br>"
            "&nbsp;&nbsp;· [+ 지역 추가] — 지역명/면적/환경 입력 → 지역 탭 생성<br>"
            "&nbsp;&nbsp;· [지역 종합 분석] — 지역별 총 탄소저장량 비교 대시보드<br><br>"
            "<i>국내·국외 통합 기여도 모듈은 현재 화면에서 비표시(코드·수식은 보존).</i><br><br>"
            "데이터 출처: <i>상대생장식 자료_최종본.xlsx</i> 「기초 DB 자료」 시트",
        )

    def closeEvent(self, event) -> None:
        """창을 닫을 때 모든 지역 인스턴스와 보존된 Carbon2 인스턴스를 정리."""
        try:
            for r in self._regions:
                r["window"].close()
            self._carbon2.close()
        finally:
            super().closeEvent(event)
