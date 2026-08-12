# -*- coding: utf-8 -*-
"""
애플리케이션 전역 폰트 설정 (화면 크기 반응형).

QApplication 의 기본 폰트를 일괄 변경하여 모든 위젯(콤보, 스피너, 라벨,
테이블, 메뉴 등) 의 글자 크기를 한 번에 조정한다.

설계 기준 해상도(1920×1080)에서는 기존과 동일하게 (기본 + FONT_SIZE_DELTA)pt 로
표시되고, 더 작은 모니터에서는 ui_scale 배수만큼 비례 축소하여 화면을 넘지 않게 한다.

matplotlib 폰트는 plotting.set_plot_font_scale 로 동일 스케일을 적용.
"""
from __future__ import annotations

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

from .ui_scale import ui_scale


# 기준 해상도에서의 전체 글꼴 가산량 (전체 텍스트 가독성을 위해 상향)
FONT_SIZE_DELTA = 5

# Qt 가 점-size 를 반환하지 못할 때(픽셀-size 사용) 사용할 폴백
_FALLBACK_BASE_PT = 9


def setup_application_fonts(app: QApplication,
                            scale: float | None = None,
                            delta: int = FONT_SIZE_DELTA) -> None:
    """애플리케이션 기본 폰트를 화면 스케일에 맞춰 설정한다."""
    if scale is None:
        scale = ui_scale(app)

    f: QFont = app.font()
    current = f.pointSize()
    if current <= 0:
        current = _FALLBACK_BASE_PT

    base = current + delta                     # 기준 해상도 디자인 크기 (예: 9+4 = 13pt)
    target = max(9, round(base * scale))       # 작은 화면에서 비례 축소
    f.setPointSize(target)
    app.setFont(f)
