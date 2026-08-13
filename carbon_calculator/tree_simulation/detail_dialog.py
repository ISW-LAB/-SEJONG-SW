"""선택 개체의 현재 연도 특성을 보여주는 작은 상세창."""
from __future__ import annotations

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ..ui_scale import px
from .inspection import InstanceInspection


def _profile_pixmap(info: InstanceInspection) -> QPixmap:
    """외부 사진 대신 현재 render profile을 설명하는 수형 예시 그림을 만든다."""
    pixmap = QPixmap(px(190), px(230))
    pixmap.fill(QColor("#EEF3F0"))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    w, h = pixmap.width(), pixmap.height()
    painter.setPen(QPen(QColor("#8AA07E"), 2))
    painter.drawLine(px(16), h - px(24), w - px(16), h - px(24))
    crown = QColor(info.profile_color)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#76543A"))
    if info.kind == "tree":
        painter.drawRoundedRect(w // 2 - px(8), h // 2, px(16), h // 2 - px(24), 4, 4)
    else:
        for offset in (-px(18), 0, px(18)):
            painter.drawRoundedRect(w // 2 + offset - px(3), h // 2 + px(35), px(6), px(70), 3, 3)
    painter.setBrush(crown)
    shape = info.profile_shape
    if shape in ("layered_conifer", "pyramid"):
        for i in range(3):
            top = px(24 + i * 42)
            half = px(34 + i * 12)
            painter.drawPolygon(
                QPoint(w // 2, top), QPoint(w // 2 - half, top + px(75)),
                QPoint(w // 2 + half, top + px(75)),
            )
    elif shape == "shrub_upright":
        painter.drawEllipse(w // 2 - px(42), px(28), px(84), px(155))
    elif shape == "shrub_spreading":
        painter.drawEllipse(px(18), px(88), w - px(36), px(90))
    else:
        painter.drawEllipse(px(25), px(35), w - px(50), px(135 if info.kind == "tree" else 125))
        if shape in ("open_oval", "spreading", "shrub_multistem"):
            painter.drawEllipse(px(10), px(82), px(85), px(90))
            painter.drawEllipse(w - px(95), px(76), px(85), px(94))
    painter.end()
    return pixmap


class VegetationDetailDialog(QDialog):
    def __init__(self, info: InstanceInspection, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{info.species} · Year {info.year} 개체 정보")
        self.setModal(False)
        self.setMinimumWidth(px(590))
        root = QVBoxLayout(self)
        body = QHBoxLayout()
        image = QLabel()
        image.setPixmap(_profile_pixmap(info))
        image.setAlignment(Qt.AlignCenter)
        image.setToolTip("현재 3D render profile을 단순화한 수형 예시이며 실제 수종 사진이 아닙니다.")
        body.addWidget(image)

        form = QFormLayout()
        kind_label = "교목" if info.kind == "tree" else "관목"
        diameter_name = "DBH" if info.kind == "tree" else "RCD"
        rows = (
            ("수종", info.species), ("구분", kind_label), ("경과 연도", f"Year {info.year}"),
            ("같은 입력 그룹 수량", f"{info.group_quantity:,}주"),
            (f"현재 {diameter_name}", f"{info.diameter:,.2f} {info.diameter_unit}"),
            ("현재 개체 탄소저장량", f"{info.carbon_kgc:,.4f} kgC/주"),
            ("상대생장식 계수", f"a={info.a:g} · b={info.b:g} · CF={info.cf:g}"),
            ("직경 성장률", f"1~10년 {info.growth_y10:g} · 11~20년 {info.growth_y20:g} · 21년+ {info.growth_y21:g} cm/yr"),
            ("지역 내 위치", f"X {info.x_m:,.2f} m · Y {info.y_m:,.2f} m"),
            ("표현 줄기 직경 (시각화용)", f"{info.rendered_trunk_diameter_m:,.3f} m"),
            ("표현 수고 (시각화용)", f"{info.rendered_height_m:,.2f} m"),
            ("표현 수관 폭 (시각화용)", f"{info.crown_width_m:,.2f} m"),
            ("표현 수관 길이 (시각화용)", f"{info.crown_length_m:,.2f} m"),
            ("표현 풍성함 (시각화용)", f"{info.visual_development * 100:,.0f}%"),
            ("데이터 구분", "DBH/RCD·탄소: 기존 프로젝트 데이터 / 수고·수관·풍성함: visual fallback"),
        )
        for label, value in rows:
            field = QLabel(value); field.setWordWrap(True); field.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form.addRow(label, field)
        body.addLayout(form, 1)
        root.addLayout(body)
        note = QLabel("왼쪽 그림과 모든 '표현' 값은 3D 시각화용이며 탄소 계산에는 영향을 주지 않습니다.")
        note.setWordWrap(True); note.setStyleSheet("color:#6B7780; padding:4px;")
        root.addWidget(note)
        close_btn = QPushButton("닫기"); close_btn.clicked.connect(self.close)
        root.addWidget(close_btn, alignment=Qt.AlignRight)
