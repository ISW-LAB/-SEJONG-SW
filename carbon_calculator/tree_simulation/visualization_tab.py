"""Carbon1 오른쪽 결과 탭에 삽입되는 지역별 3D 시각화 QWidget."""
from __future__ import annotations

from typing import Callable

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout,
    QWidget,
)
from pyvistaqt import QtInteractor

from ..ui_scale import pt, px
from .models import RegionVisualizationSnapshot
from .renderer import VegetationRenderer


SnapshotProvider = Callable[[], RegionVisualizationSnapshot]
FingerprintProvider = Callable[[], str]


class VegetationVisualizationTab(QWidget):
    def __init__(self, snapshot_provider: SnapshotProvider,
                 fingerprint_provider: FingerprintProvider, parent=None):
        super().__init__(parent)
        self._snapshot_provider = snapshot_provider
        self._fingerprint_provider = fingerprint_provider
        self._snapshot: RegionVisualizationSnapshot | None = None
        self._build_ui()
        self._play_timer = QTimer(self)
        self._play_timer.setInterval(450)
        self._play_timer.timeout.connect(self._advance_year)
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(900)
        self._sync_timer.timeout.connect(self._check_stale)
        self._sync_timer.start()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(5)

        self.region_label = QLabel("시각화를 새로고침하세요.")
        font = self.region_label.font(); font.setPointSize(pt(11)); font.setBold(True)
        self.region_label.setFont(font)
        self.region_label.setStyleSheet("color: #246B43; padding: 3px;")
        root.addWidget(self.region_label)

        self.plotter = QtInteractor(self, auto_update=False)
        self.plotter.setMinimumHeight(px(300))
        self.plotter.set_background("#EEF3F0")
        # 지면의 Z축을 항상 위쪽으로 유지한다. 기본 trackball 방식에서 가능한
        # 카메라 roll을 제거해 화면이 좌우로 기울어지는 것을 방지한다.
        self.plotter.enable_terrain_style(mouse_wheel_zooms=True, shift_pans=True)
        self.renderer = VegetationRenderer(self.plotter)
        root.addWidget(self.plotter, 1)

        controls = QFrame()
        row = QHBoxLayout(controls); row.setContentsMargins(4, 2, 4, 2)
        self.play_btn = QPushButton("재생")
        self.pause_btn = QPushButton("일시정지")
        self.refresh_btn = QPushButton("새로고침")
        self.play_btn.clicked.connect(self.play)
        self.pause_btn.clicked.connect(self.pause)
        self.refresh_btn.clicked.connect(self.refresh_snapshot)
        row.addWidget(self.play_btn); row.addWidget(self.pause_btn)
        row.addWidget(QLabel("Year 0"))
        self.year_slider = QSlider(Qt.Horizontal)
        self.year_slider.setRange(0, 50)
        self.year_slider.valueChanged.connect(self._on_year_changed)
        row.addWidget(self.year_slider, 1)
        row.addWidget(QLabel("Year 50"))
        self.year_label = QLabel("현재: 0년")
        row.addWidget(self.year_label)
        row.addWidget(self.refresh_btn)
        root.addWidget(controls)

        self.summary_label = QLabel("총 탄소저장량: 0.00 kgC · 교목 0주 / 관목 0주")
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setStyleSheet(
            "background: #FFFFFF; border: 1px solid #D8DEE4; border-radius: 5px; padding: 5px;"
        )
        root.addWidget(self.summary_label)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #B05A2B; padding: 1px 4px;")
        root.addWidget(self.status_label)

        note = QLabel(
            "DBH/RCD 성장은 현재 수종별 생장자료를 사용합니다. 수고 및 수관 변화는 "
            "검증식이 있는 경우 해당 식을 사용하며, 그 외에는 3D 표현용 기본 모델을 사용합니다. "
            "단순 3D 형상에서 식별하기 쉽도록 줄기 굵기는 화면 표시용으로 보정됩니다. "
            "Year 0은 현재 입력 상태입니다."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #6B7780; font-size: 10px; padding: 2px 4px;")
        root.addWidget(note)

    def refresh_snapshot(self) -> None:
        self.pause()
        try:
            snapshot = self._snapshot_provider()
        except Exception as exc:  # 사용자에게 3D 계층 오류를 알리고 기존 앱은 유지
            self.status_label.setText(f"시각화 갱신 실패: {exc}")
            return
        self._snapshot = snapshot
        self.region_label.setText(
            f"지역: {snapshot.region_name or '지역'} · 환경: {snapshot.environment} · "
            f"면적: {snapshot.area_w:g} × {snapshot.area_h:g} m "
            f"({snapshot.area_w * snapshot.area_h:,.0f} ㎡)"
        )
        if not snapshot.instances:
            self.plotter.clear_actors()
            self.renderer.clear()
            self.plotter.add_text("표시할 유효 교목/관목 입력이 없습니다.", position="upper_left")
            self.status_label.setText("항목을 추가한 뒤 계산하거나 새로고침하세요.")
        else:
            self.plotter.clear_actors()
            self.renderer.set_snapshot(snapshot)
            self.status_label.setText(" · ".join(snapshot.warnings))
        self.year_slider.blockSignals(True)
        self.year_slider.setValue(0)
        self.year_slider.blockSignals(False)
        self._on_year_changed(0)

    def _check_stale(self) -> None:
        if not self.isVisible():
            return
        try:
            fingerprint = self._fingerprint_provider()
        except Exception:
            return
        if self._snapshot is None or fingerprint != self._snapshot.input_fingerprint:
            self.status_label.setText("입력이 변경되어 최신 상태로 시각화를 갱신합니다.")
            self.refresh_snapshot()

    def _on_year_changed(self, year: int) -> None:
        self.year_label.setText(f"현재: {year}년")
        if self._snapshot is None:
            return
        self.renderer.update_year(year)
        carbon = float(self._snapshot.total_carbon_by_year_kgc[year])
        self.summary_label.setText(
            f"총 탄소저장량: {carbon:,.2f} kgC · "
            f"교목 {self._snapshot.tree_count:,}주 / 관목 {self._snapshot.shrub_count:,}주"
        )

    def play(self) -> None:
        if self._snapshot is None:
            self.refresh_snapshot()
        if self.year_slider.value() >= 50:
            self.year_slider.setValue(0)
        self._play_timer.start()

    def pause(self) -> None:
        if hasattr(self, "_play_timer"):
            self._play_timer.stop()

    def _advance_year(self) -> None:
        value = self.year_slider.value()
        if value >= 50:
            self.pause()
            return
        next_value = value + 1
        self.year_slider.setValue(next_value)
        if next_value >= 50:
            self.pause()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._check_stale()

    def closeEvent(self, event) -> None:
        self.pause()
        self._sync_timer.stop()
        self.renderer.clear()
        self.plotter.close()
        super().closeEvent(event)
