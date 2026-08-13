# -*- coding: utf-8 -*-
"""
MATLAB uigauge('linear') 와 유사한 수평 게이지 위젯.
"""
from __future__ import annotations

import difflib

from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtWidgets import (
    QComboBox, QDoubleSpinBox, QHeaderView, QLineEdit, QListWidget,
    QListWidgetItem, QSpinBox, QTableWidget, QVBoxLayout, QWidget,
)

from .ui_scale import pt, px


# 마우스 휠로 값이 의도치 않게 바뀌는 것을 방지하기 위한 입력 위젯들.
# 스크롤 영역 안의 행에서 스크롤할 때 카테고리/직경/수량 값이 변경되는 문제를 해결.
class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event):
        event.ignore()


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()


def rank_items(query: str, items: list[tuple[str, object]]) -> list[tuple[str, object]]:
    """
    검색어로 (표시텍스트, 데이터) 목록을 유사도 순으로 정렬·필터.

    - 부분일치(공백 무시) 항목을 최우선 (등장 위치가 빠를수록 상위).
    - 부분일치가 없으면 difflib 유사도 상위 항목을 제시.
    - 어느 것도 없으면(완전 무관) 전체를 유사도순으로 반환해 콤보가 비지 않게 함.
    """
    q = "".join(query.split()).lower()
    if not q:
        return list(items)

    subs: list[tuple[int, int, str, object]] = []
    fuzzy: list[tuple[float, str, object]] = []
    for text, data in items:
        t = "".join(text.split()).lower()
        pos = t.find(q)
        if pos >= 0:
            subs.append((pos, len(t), text, data))
        else:
            ratio = difflib.SequenceMatcher(None, q, t).ratio()
            fuzzy.append((ratio, text, data))

    if subs:
        subs.sort(key=lambda e: (e[0], e[1]))
        return [(text, data) for _, _, text, data in subs]

    fuzzy.sort(key=lambda e: -e[0])
    close = [(text, data) for ratio, text, data in fuzzy if ratio >= 0.34]
    return close if close else [(text, data) for _, text, data in fuzzy]


class SearchableComboBox(QWidget):
    """
    검색창(QLineEdit) + 콤보박스(QComboBox) + 실시간 추천 리스트 결합 위젯.

    - 검색창에 키워드를 입력할 때마다 유사도 높은 순으로 콤보가 필터링되고,
      **검색창 바로 아래의 추천 리스트**에 후보가 실시간으로 표시된다(유사도 1위가 맨 위).
    - 추천 항목을 클릭하거나 Enter(검색창) 를 누르면 그 수종이 선택된다.
    - 각 항목은 (표시텍스트, 임의 데이터) 형태로 보관하며 ``current_data()`` 로
      선택 항목의 데이터를 얻는다.
    """

    currentIndexChanged = pyqtSignal(int)

    SUGGEST_LIMIT = 10   # 추천 리스트 최대 표시 개수

    def __init__(self, placeholder: str = "🔍 검색 (예: 소나무)", parent=None):
        super().__init__(parent)
        self._all: list[tuple[str, object]] = []

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(px(4))

        self.search = QLineEdit()
        self.search.setPlaceholderText(placeholder)
        self.search.setClearButtonEnabled(True)
        v.addWidget(self.search)

        self.combo = NoWheelComboBox()
        v.addWidget(self.combo)

        # 실시간 추천 리스트 (검색 중에만 표시)
        self.suggestions = QListWidget()
        self.suggestions.setVisible(False)
        self.suggestions.setMaximumHeight(px(210))
        self.suggestions.setStyleSheet(
            "QListWidget { border: 1px solid #C4CCD3; border-radius: 6px; background: #FFFFFF; }"
            "QListWidget::item { padding: 4px 6px; }"
            "QListWidget::item:selected { background: #E8F4EC; color: #232A2E; }"
        )
        v.addWidget(self.suggestions)

        self.search.textChanged.connect(self._on_search)
        self.search.returnPressed.connect(self._choose_top_suggestion)
        self.suggestions.itemClicked.connect(self._on_suggestion_chosen)
        self.combo.currentIndexChanged.connect(self.currentIndexChanged)

    def set_items(self, items: list[tuple[str, object]]) -> None:
        self._all = list(items)
        self._apply("")

    def _apply(self, query: str) -> None:
        ranked = rank_items(query, self._all)

        # 콤보 갱신 (현재 선택 = 유사도 1위)
        self.combo.blockSignals(True)
        self.combo.clear()
        for text, data in ranked:
            self.combo.addItem(text, data)
        self.combo.blockSignals(False)
        if self.combo.count() > 0:
            self.combo.setCurrentIndex(0)

        # 추천 리스트 갱신 (검색어가 있을 때만 표시)
        self._update_suggestions(query, ranked)

        # 목록이 바뀌었으니 현재 선택을 알림 (다이얼로그 우측 정보 갱신용)
        self.currentIndexChanged.emit(self.combo.currentIndex())

    def _update_suggestions(self, query: str, ranked: list[tuple[str, object]]) -> None:
        self.suggestions.clear()
        if not query.strip() or not ranked:
            self.suggestions.setVisible(False)
            return
        for rank, (text, data) in enumerate(ranked[: self.SUGGEST_LIMIT], 1):
            item = QListWidgetItem(f"{rank}. {text}")
            item.setData(Qt.UserRole, data)
            item.setData(Qt.UserRole + 1, text)   # 원본 표시텍스트(번호 제외)
            self.suggestions.addItem(item)
        self.suggestions.setCurrentRow(0)
        self.suggestions.setVisible(True)

    def _on_search(self, text: str) -> None:
        self._apply(text)

    def _select_data(self, data, display_text: str) -> None:
        idx = self.combo.findData(data)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
        # 선택한 수종명을 검색창에 반영 (재필터 방지 위해 시그널 차단)
        self.search.blockSignals(True)
        self.search.setText(display_text)
        self.search.blockSignals(False)
        self.suggestions.setVisible(False)

    def _on_suggestion_chosen(self, item: QListWidgetItem) -> None:
        self._select_data(item.data(Qt.UserRole), item.data(Qt.UserRole + 1))

    def _choose_top_suggestion(self) -> None:
        if self.suggestions.isVisible() and self.suggestions.count() > 0:
            row = max(0, self.suggestions.currentRow())
            self._on_suggestion_chosen(self.suggestions.item(row))

    # ----- 조회 API -----
    def current_data(self):
        return self.combo.currentData()

    def currentText(self) -> str:
        return self.combo.currentText()

    def count(self) -> int:
        return self.combo.count()


class ResultTable(QTableWidget):
    """
    결과 테이블 — 패널 폭에 항상 정확히 맞고, 각 열 너비를 드래그로 조절 가능.

    동작
    ----
    - 모든 열 ``Interactive`` → 사용자가 열 경계를 드래그해 너비 조절.
    - ``flex_col``(기본 0번=수종)이 남는 폭을 흡수 → 모든 열 너비의 합이 항상
      뷰포트 폭과 정확히 일치한다(가로 스크롤바·우측 빈 공간 없음).
    - 창/패널 크기가 바뀌면 ``resizeEvent`` 에서 자동 재맞춤.
    - 사용자가 숫자 열을 드래그하면 그만큼 flex 열(수종)이 늘거나 줄어 폭을 유지한다.

    → 긴 수종명도 flex 열이 가용 폭을 최대한 차지하므로 잘림이 최소화되고,
      그래도 부족하면 셀 툴팁으로 전체 값을 확인할 수 있다(호출측에서 설정).
    """

    def __init__(self, flex_col: int = 0, parent=None):
        super().__init__(parent)
        self._flex_col = flex_col
        self._fitting = False
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(px(48))
        # 가로 스크롤 금지 → 항상 패널 폭에 맞춤
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        header.sectionResized.connect(self._on_section_resized)

    def fit_columns(self) -> None:
        """flex 열을 조정해 전체 열 너비 합 = 뷰포트 폭이 되도록 맞춘다."""
        n = self.columnCount()
        if n == 0:
            return
        vp = self.viewport().width()
        if vp <= 0:
            return
        min_sec = self.horizontalHeader().minimumSectionSize()
        others = sum(self.columnWidth(c) for c in range(n) if c != self._flex_col)
        flex_w = max(min_sec, vp - others)
        if self.columnWidth(self._flex_col) == flex_w:
            return
        self._fitting = True
        self.setColumnWidth(self._flex_col, flex_w)
        self._fitting = False

    def _on_section_resized(self, idx: int, _old: int, _new: int) -> None:
        # flex 열 자체의 변경/내부 보정 중에는 무시(재귀 방지)
        if self._fitting or idx == self._flex_col:
            return
        # 숫자 열을 사용자가 드래그 → flex 열이 잔여 폭을 흡수
        self.fit_columns()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fit_columns()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.fit_columns()


class LinearGauge(QWidget):
    """수평 선형 게이지 (눈금 + 채워지는 바)."""

    def __init__(self, minimum: float = 0.0, maximum: float = 100.0,
                 major_ticks: list[float] | None = None, parent=None):
        super().__init__(parent)
        self._min = float(minimum)
        self._max = float(maximum)
        self._value = 0.0
        self._major_ticks = list(major_ticks) if major_ticks else self._default_ticks()
        self.setMinimumHeight(px(52))

    def _default_ticks(self) -> list[float]:
        span = self._max - self._min
        if span <= 0:
            return [self._min, self._max]
        step = span / 5
        return [self._min + step * i for i in range(6)]

    def setValue(self, v: float) -> None:
        self._value = max(self._min, min(self._max, float(v)))
        self.update()

    def setRange(self, minimum: float, maximum: float,
                 major_ticks: list[float] | None = None) -> None:
        self._min = float(minimum)
        self._max = max(self._min + 1e-9, float(maximum))
        self._major_ticks = list(major_ticks) if major_ticks else self._default_ticks()
        self._value = max(self._min, min(self._max, self._value))
        self.update()

    def value(self) -> float:
        return self._value

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        track_top = 6
        track_h = max(10, h // 3)
        track_rect = QRectF(2, track_top, w - 4, track_h)

        # Track
        p.setPen(QPen(QColor(150, 150, 150), 1))
        p.setBrush(QColor(235, 235, 235))
        p.drawRoundedRect(track_rect, 4, 4)

        # Fill bar
        span = max(self._max - self._min, 1e-9)
        ratio = (self._value - self._min) / span
        ratio = max(0.0, min(1.0, ratio))
        fill_rect = QRectF(track_rect.x(), track_rect.y(),
                           track_rect.width() * ratio, track_rect.height())
        # color: green → orange → red
        if ratio < 0.6:
            color = QColor(0x2E, 0x8B, 0x57)
        elif ratio < 0.85:
            color = QColor(0xE0, 0x9A, 0x2B)
        else:
            color = QColor(0xC0, 0x39, 0x2B)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(fill_rect, 4, 4)

        # Ticks + labels
        p.setPen(QPen(QColor(80, 80, 80), 1))
        font = QFont()
        font.setPointSize(pt(11))
        p.setFont(font)
        for tick in self._major_ticks:
            t_ratio = (tick - self._min) / span
            x = track_rect.x() + track_rect.width() * t_ratio
            p.drawLine(int(x), int(track_rect.bottom()), int(x), int(track_rect.bottom()) + 4)
            label = f"{tick:g}"
            metrics = p.fontMetrics()
            tw = metrics.horizontalAdvance(label)
            p.drawText(int(x - tw / 2), int(track_rect.bottom()) + 20, label)
