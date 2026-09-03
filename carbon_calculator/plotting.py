# -*- coding: utf-8 -*-
"""
matplotlib 캔버스 래퍼 (PyQt5 임베드).
"""
from __future__ import annotations

import warnings

import matplotlib
matplotlib.use("Qt5Agg")

# 캔버스를 매우 좁게(스플리터로) 끌면 constrained_layout 이 "axes collapsed to zero"
# 경고를 매 draw 마다 출력한다. 그림은 정상적으로 그려지므로(무해) 콘솔 스팸만 억제한다.
warnings.filterwarnings("ignore", message=".*constrained_layout not applied.*")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from PyQt5.QtWidgets import QSizePolicy  # noqa: E402

from .i18n import species_name, tr  # noqa: E402


# 기준 해상도(1920×1080, scale=1.0)에서의 matplotlib 폰트 크기.
# set_plot_font_scale 로 화면 스케일을 곱해 작은 모니터에서 비례 축소한다.
_BASE_PLOT_FONTS = {
    "font.size": 18,
    "axes.titlesize": 20,
    "axes.labelsize": 18,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 16,
}

# 인라인 fontsize(파이/메시지/툴팁)에도 적용할 현재 스케일.
_PLOT_SCALE = 1.0


def set_plot_font_scale(scale: float = 1.0) -> None:
    """그래프 한글 폰트 + 글자 크기를 화면 스케일에 맞춰 설정. 실패 시 기본 폰트 유지."""
    global _PLOT_SCALE
    _PLOT_SCALE = scale
    try:
        plt.rcParams["font.family"] = "Malgun Gothic"
        plt.rcParams["axes.unicode_minus"] = False
        for key, base in _BASE_PLOT_FONTS.items():
            plt.rcParams[key] = max(7, round(base * scale))
    except Exception:
        pass


def _fs(base: float) -> int:
    """인라인 fontsize 를 현재 스케일로 변환."""
    return max(6, round(base * _PLOT_SCALE))


# 기본(scale=1.0) 설정 — run 진입점에서 set_plot_font_scale 로 재설정됨.
set_plot_font_scale(1.0)


class MatplotlibCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width: float = 5, height: float = 2, dpi: int = 100):
        # constrained_layout: 폰트·라벨 크기 변화에 자동 적응 (tight_layout 보다 견고).
        # tight_layout 과 동시 사용 시 UserWarning 발생하므로 layout 만 사용한다.
        self.figure = Figure(figsize=(width, height), dpi=dpi, layout="constrained")
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.setParent(parent)

        # 반응형: 캔버스가 창 크기에 따라 자유롭게 늘어나고 줄어들도록.
        # (기본 FigureCanvas 는 figsize 기반의 큰 최소 크기를 가져 작은 화면에서 넘침)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(120, 90)

        # 호버 툴팁 상태
        self._hover_cid: int | None = None
        self._hover_ann = None
        # 다중 라인 지원: (line_artist, xdata, ydata, name) 튜플 리스트
        self._hover_specs: list = []
        self._hover_xlabel: str = "x"
        self._hover_ylabel: str = "y"

    def _teardown_hover(self) -> None:
        if self._hover_cid is not None:
            try:
                self.mpl_disconnect(self._hover_cid)
            except Exception:
                pass
            self._hover_cid = None
        self._hover_ann = None
        self._hover_specs = []

    def clear(self) -> None:
        self._teardown_hover()
        self.ax.clear()
        self.draw_idle()

    def plot_projection(self, years, carbon, title: str, ylabel: str | None = None,
                        xlabel: str | None = None) -> None:
        # 기본값을 import 시점에 굳히면 언어 설정 전 문자열이 박힌다 → 호출 시 해석.
        ylabel = tr("탄소저장량 (kgC)") if ylabel is None else ylabel
        xlabel = tr("경과 기간 (Years)") if xlabel is None else xlabel
        self._teardown_hover()
        self.ax.clear()
        line, = self.ax.plot(
            years, carbon, marker="o", color="#2E8B57",
            linewidth=2.0, markersize=5, picker=False,
        )
        line.set_pickradius(6)
        self.ax.set_title(title)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.ax.grid(True, alpha=0.4)
        self._install_hover([(line, list(years), list(carbon), "")], xlabel, ylabel)
        self.draw_idle()

    def plot_multi_projection(self, series, title: str,
                              ylabel: str = tr("탄소저장량 (kgC)"),
                              xlabel: str = tr("경과 기간 (Years)"),
                              show_title: bool = True) -> None:
        """
        여러 추정 곡선을 한 그래프에 중첩 표시.

        series: [(label, years, carbon, is_total), ...]
          - is_total=True 인 곡선은 굵은 점선(강조색)으로 그려 "총합"을 시각 구분.
        show_title=False 면 축 제목을 그리지 않는다(호출측이 패널 위 라벨로 제목을 표시할 때).
        """
        self._teardown_hover()
        self.ax.clear()
        if not series:
            self.show_message(tr("표시할 항목이 없습니다."))
            return

        color_cycle = plt.rcParams["axes.prop_cycle"].by_key().get("color", [])
        specs: list = []
        ci = 0
        for label, years, carbon, is_total in series:
            if is_total:
                line, = self.ax.plot(
                    years, carbon, color="#C0392B", linewidth=2.6,
                    linestyle="--", marker="s", markersize=4, label=label, zorder=5,
                )
            else:
                color = color_cycle[ci % len(color_cycle)] if color_cycle else None
                ci += 1
                line, = self.ax.plot(
                    years, carbon, color=color, linewidth=1.8,
                    marker="o", markersize=3.5, label=label,
                )
            line.set_pickradius(6)
            specs.append((line, list(years), list(carbon), label))

        if show_title:
            self.ax.set_title(title)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.ax.grid(True, alpha=0.4)
        # 범례는 그래프 내부를 침범하지 않도록 **축 바깥 오른쪽**에 배치 (constrained_layout 이
        # 가로 자리를 확보). 항목이 많으면 세로로 넘쳐 잘리므로 열 수를 늘려 옆으로 펼친다.
        ncol = 1 + (len(specs) - 1) // 10  # 한 열에 ~10개씩 → 16개 이상이면 2열+
        self.ax.legend(
            fontsize=_fs(10), loc="upper left", bbox_to_anchor=(1.01, 1.0),
            framealpha=0.95, borderaxespad=0.0, ncol=max(1, ncol),
        )
        self._install_hover(specs, xlabel, ylabel)
        self.draw_idle()

    def show_message(self, message: str) -> None:
        self._teardown_hover()
        self.ax.clear()
        self.ax.text(0.5, 0.5, message, ha="center", va="center",
                     transform=self.ax.transAxes, fontsize=_fs(15), color="#777")
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.draw_idle()

    # ----- 호버 툴팁 -----

    def _install_hover(self, specs: list, x_label: str, y_label: str) -> None:
        """라인(들) 위에 마우스 호버 시 (x, y) 라벨 표시 툴팁 설치.

        specs: [(line_artist, xdata, ydata, name), ...] — 여러 곡선을 지원.
        """
        if not specs:
            return
        ann = self.ax.annotate(
            "", xy=(0, 0), xytext=(15, 15), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.4", fc="#FFFFE0", ec="#888", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#888"),
            fontsize=_fs(13),
            # 모든 곡선(총합 곡선 zorder=5 포함)·마커 위에 항상 표시되도록 zorder 를 크게.
            zorder=100,
        )
        # 연결 화살표(arrow_patch)는 별도 zorder 를 가지므로 함께 올려 선 뒤에 가리지 않게 한다.
        if getattr(ann, "arrow_patch", None) is not None:
            ann.arrow_patch.set_zorder(100)
        # constrained_layout 이 호버 박스 크기에 반응해 축을 재배치하며 깜빡이는 것을 방지
        # (박스가 영역을 넘어도 레이아웃에 영향 주지 않음). 방향 뒤집기는 가독성용으로 별도 유지.
        ann.set_in_layout(False)
        ann.set_visible(False)
        self._hover_ann = ann
        self._hover_specs = list(specs)
        self._hover_xlabel = x_label
        self._hover_ylabel = y_label
        self._hover_cid = self.mpl_connect("motion_notify_event", self._on_hover_motion)

    def _on_hover_motion(self, event) -> None:
        ann = self._hover_ann
        specs = self._hover_specs
        if ann is None or not specs:
            return
        was_visible = ann.get_visible()
        if event.inaxes is not self.ax:
            if was_visible:
                ann.set_visible(False)
                self.draw_idle()
            return
        for line, xdata, ydata, name in specs:
            contains, info = line.contains(event)
            if contains and info.get("ind") is not None and len(info["ind"]) > 0:
                idx = int(info["ind"][0])
                x = xdata[idx]
                y = ydata[idx]
                ann.xy = (x, y)
                prefix = f"{name}\n" if name else ""
                ann.set_text(
                    f"{prefix}{self._hover_xlabel}: {x}\n{self._hover_ylabel}: {y:.4g}"
                )
                # 박스가 축 밖으로 나가 레이아웃이 재계산되며 깜빡이는 것을 막기 위해,
                # 실제 박스 크기를 측정해 우측/상단을 넘치면 좌측/하단으로 뒤집어 배치한다.
                self._place_annotation(ann, x, y)
                ann.set_visible(True)
                self.draw_idle()
                return
        if was_visible:
            ann.set_visible(False)
            self.draw_idle()

    def _renderer(self):
        """현재 렌더러(없거나 아직 그려지지 않았으면 None)."""
        try:
            return self.get_renderer()
        except Exception:
            return None

    def _place_annotation(self, ann, x: float, y: float, off: int = 16) -> None:
        """호버 박스를 측정해 그래프 영역을 넘치지 않도록 좌/우·상/하 방향을 정한다.

        텍스트 박스의 폭/높이는 위치(offset)와 무관하므로, 기준 위치에서 한 번 측정한 뒤
        점의 화면 좌표 + 오프셋 + 박스 크기가 축 경계를 넘으면 반대쪽으로 뒤집는다.
        렌더러를 얻지 못하면(최초 그리기 전) 위치 분율 0.5 기준으로 근사한다.
        """
        dx, dy, ha, va = off, off, "left", "bottom"
        renderer = self._renderer()
        measured = False
        # 보이지 않는 아티스트는 일부 matplotlib 버전에서 빈 extent 를 돌려주므로 먼저 표시.
        ann.set_visible(True)
        if renderer is not None:
            try:
                ann.set_position((off, off)); ann.set_ha("left"); ann.set_va("bottom")
                box = ann.get_window_extent(renderer)
                axbox = self.ax.get_window_extent(renderer)
                px, py = self.ax.transData.transform((x, y))
                if px + off + box.width > axbox.x1:   # 우측 넘침 → 왼쪽으로
                    dx, ha = -off, "right"
                if py + off + box.height > axbox.y1:  # 상단 넘침 → 아래로
                    dy, va = -off, "top"
                measured = True
            except Exception:
                measured = False
        if not measured:
            xmin, xmax = self.ax.get_xlim()
            ymin, ymax = self.ax.get_ylim()
            xfrac = (x - xmin) / ((xmax - xmin) or 1.0)
            yfrac = (y - ymin) / ((ymax - ymin) or 1.0)
            dx, ha = (-off, "right") if xfrac > 0.5 else (off, "left")
            dy, va = (-off, "top") if yfrac > 0.5 else (off, "bottom")
        ann.set_position((dx, dy))
        ann.set_ha(ha)
        ann.set_va(va)

    def plot_pie(self, labels: list[str], values: list[float],
                 title: str = tr("수종별 탄소저장량 기여도"), top_n: int = 5,
                 label_fs: float = 17, title_fs: float = 20,
                 show_title: bool = True) -> None:
        """
        Carbon2 의 plotCarbonPieChart 와 동등.
        - 수종별 합산
        - 내림차순 정렬, 상위 top_n + "기타" 그룹화
        - 라벨에 "수종 (퍼센트%)\\n값 kgC" 표시

        label_fs / title_fs: 작은 1/3 패널(Carbon1 기여도)에서 더 작은 글꼴을 쓰기 위한 인자.
        show_title=False 면 차트 제목을 그리지 않는다(호출측이 패널 위 라벨로 제목을 표시할 때).
        """
        self._teardown_hover()
        self.ax.clear()

        agg: dict[str, float] = {}
        for k, v in zip(labels, values):
            agg[k] = agg.get(k, 0.0) + v
        if not agg or sum(agg.values()) <= 0:
            self.show_message(tr("표시할 데이터가 없습니다."))
            return

        sorted_items = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
        if len(sorted_items) > top_n:
            major = sorted_items[:top_n]
            others = sum(v for _, v in sorted_items[top_n:])
            plot_labels = [k for k, _ in major] + [tr("기타")]
            plot_values = [v for _, v in major] + [others]
        else:
            plot_labels = [k for k, _ in sorted_items]
            plot_values = [v for _, v in sorted_items]

        total = sum(plot_values)
        full_labels = [
            f"{lbl} ({val / total * 100:.1f}%)\n{val:.1f} kgC"
            for lbl, val in zip(plot_labels, plot_values)
        ]

        self.ax.pie(
            plot_values, labels=full_labels,
            startangle=90, counterclock=False,
            wedgeprops={"linewidth": 0.6, "edgecolor": "white"},
            textprops={"fontsize": _fs(label_fs)},
        )
        if show_title:
            self.ax.set_title(title, fontsize=_fs(title_fs), fontweight="bold")
        self.draw_idle()

    def plot_region_bars(self, names: list[str], tree_vals: list[float],
                         shrub_vals: list[float],
                         ylabel: str = tr("탄소저장량 (kgC)"), show_title: bool = True,
                         title: str = tr("지역별 탄소저장량 비교")) -> None:
        """지역별 **총** 탄소저장량 비교 막대 차트.

        각 지역(=막대)을 **고유 색상 + 해치 패턴**(/, ., x …)으로 자동 구분하고, 범례를
        **축 바깥 오른쪽**에 두되 **지역명**을 표시한다(교목/관목은 범례로 표시하지 않음).
        교목/관목 세부 내역은 동일 다이얼로그의 표에서 확인.
        """
        self._teardown_hover()
        self.ax.clear()
        if not names:
            self.show_message(tr("비교할 지역이 없습니다."))
            return

        totals = [t + s for t, s in zip(tree_vals, shrub_vals)]
        x = list(range(len(names)))
        cmap = plt.get_cmap("tab10")  # 10색
        # 색상만으로 부족할 때(흑백 인쇄·유사색)도 구분되도록 지역마다 해치 패턴을 함께 배정.
        # 모든 막대가 해치를 갖도록 빈 패턴은 제외하고, 색상 주기(10)와 서로소인 9개를 써서
        # 색·해치 조합이 늦게(최소공배수 90) 반복되게 한다 → 10개 초과 지역도 구분 유지.
        hatches = ["//", "\\\\", "..", "xx", "++", "oo", "--", "**", "||"]  # 9개 (10과 서로소)

        for i, (xi, tot, name) in enumerate(zip(x, totals, names)):
            self.ax.bar(
                xi, tot, width=0.7,
                color=cmap(i % 10), hatch=hatches[i % len(hatches)],
                edgecolor="white", linewidth=0.8, label=name,
            )

        top = max(totals) if totals else 0.0
        for xi, tot in zip(x, totals):
            self.ax.text(xi, tot + (top * 0.01 if top else 0.0), f"{tot:,.1f}",
                         ha="center", va="bottom", fontsize=_fs(11), fontweight="bold")

        # 지역 식별은 우측 범례가 담당 → x축 라벨 중복 제거(긴 지역명 겹침 방지).
        self.ax.set_xticks([])
        self.ax.set_ylabel(ylabel)
        # 막대 위 총합 라벨 공간 확보 (전부 0이면 라벨이 0 위치에 겹치지 않도록 최소 범위 지정)
        self.ax.set_ylim(0, top * 1.15 if top > 0 else 1.0)
        if show_title:
            self.ax.set_title(title, fontweight="bold")
        # 범례: 지역명, 축 바깥 오른쪽. 지역이 많으면 열 수를 늘려 세로 넘침 방지.
        ncol = 1 + (len(names) - 1) // 12
        self.ax.legend(
            title=tr("지역"), loc="upper left", bbox_to_anchor=(1.01, 1.0),
            fontsize=_fs(10), framealpha=0.95, borderaxespad=0.0, ncol=max(1, ncol),
        )
        self.ax.grid(True, axis="y", alpha=0.3)
        self.draw_idle()
