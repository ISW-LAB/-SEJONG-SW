# -*- coding: utf-8 -*-
"""
통합 실행 진입점.

Carbon1 (자생복원종) 과 Carbon2 (국내·국외 통합) 를 하나의 창에서 탭으로 전환.
이 파일이 탄소저장량측정모듈(핵심 소프트웨어)의 유일한 실행 진입점이며,
build_exe.py 가 이 파일을 빌드 대상으로 삼는다.
"""
import sys

from PyQt5.QtWidgets import QApplication

from carbon_calculator.combined_window import CombinedMainWindow
from carbon_calculator.font_config import setup_application_fonts
from carbon_calculator.plotting import set_plot_font_scale
from carbon_calculator.theme import apply_theme
from carbon_calculator.ui_scale import enable_high_dpi, ui_scale


def main() -> int:
    enable_high_dpi()                  # QApplication 생성 전 (고해상도 스케일링)
    app = QApplication(sys.argv)

    scale = ui_scale(app)              # 모니터 크기 기준 UI 스케일 1회 계산
    setup_application_fonts(app, scale)
    set_plot_font_scale(scale)         # matplotlib 폰트도 동일 스케일
    apply_theme(app, scale)            # 통합 테마(QSS) 적용

    win = CombinedMainWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
