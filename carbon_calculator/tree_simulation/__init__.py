"""지역별 3D 식생 생장 시각화 패키지.

이 패키지의 수고·수관 값은 렌더링 전용이며 Carbon1 탄소 계산에 사용되지 않는다.
"""

from .models import RegionVisualizationSnapshot

__all__ = ["RegionVisualizationSnapshot"]
