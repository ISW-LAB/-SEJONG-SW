# -*- coding: utf-8 -*-
"""
탄소량 계산 핵심 로직.

원본 MATLAB의 calculateTreeCarbon / calculateShrubCarbon / plotTreeGraph / plotShrubGraph
와 동일한 수식을 보존한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .data import SpeciesData
from .i18n import species_name, tr


class RangeViolation(Exception):
    """입력 직경이 수종별 유효 범위를 벗어났을 때 발생."""
    def __init__(self, species: str, value: float, vmin: float, vmax: float, unit: str):
        self.species = species
        self.value = value
        self.vmin = vmin
        self.vmax = vmax
        self.unit = unit
        super().__init__(
            tr("{species}의 유효 직경 범위는 {vmin:g}{unit} ~ {vmax:g}{unit} 입니다.")
            .format(species=species_name(species), vmin=vmin, vmax=vmax, unit=unit)
        )


@dataclass
class CarbonRow:
    species: str
    diameter: float
    quantity: int
    carbon_kg: float

    def as_table_row(self) -> list:
        return [self.species, self.diameter, self.quantity, round(self.carbon_kg, 2)]


def calculate_carbon(species_name: str,
                     species_data: SpeciesData,
                     diameter: float,
                     quantity: int,
                     unit: str = "cm") -> CarbonRow | None:
    """
    한 입력 슬롯에 대한 탄소량 계산.
    수량이 0이면 None (계산에서 제외).
    유효 범위 위반 시 RangeViolation 예외.
    """
    if quantity <= 0:
        return None

    if diameter < species_data.diameter_min or diameter > species_data.diameter_max:
        raise RangeViolation(
            species_name, diameter,
            species_data.diameter_min, species_data.diameter_max, unit,
        )

    biomass = species_data.a * (diameter ** species_data.b)
    carbon_per_individual = biomass * species_data.cf
    total_carbon = carbon_per_individual * quantity
    return CarbonRow(species_name, diameter, quantity, total_carbon)


def weighted_average_diameter(rows: Iterable[CarbonRow]) -> float:
    """결과 행들의 수량 가중평균 직경. 합이 0이면 0 반환."""
    rows = list(rows)
    total_qty = sum(r.quantity for r in rows)
    if total_qty == 0:
        return 0.0
    return sum(r.diameter * r.quantity for r in rows) / total_qty


def project_future_carbon(species_data: SpeciesData,
                          starting_diameter: float,
                          total_quantity: int,
                          years: int = 50,
                          mm_scale: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """
    starting_diameter 부터 매년 성장률만큼 증가시키며 N년간 총 탄소량 변동 계산.

    Returns:
        years_arr (0..N), carbon_arr (각 연도의 총 탄소량 kgC)

    mm_scale=True 면 관목 (RCD mm) 모드. 성장률 cm/yr → mm/yr 변환.
    """
    scale = 10.0 if mm_scale else 1.0
    years_arr = np.arange(0, years + 1)
    diameter_arr = np.zeros(years + 1, dtype=float)
    diameter_arr[0] = starting_diameter

    for i in range(1, years + 1):
        growth = species_data.growth_at_year(i) * scale
        diameter_arr[i] = diameter_arr[i - 1] + growth

    carbon_per = species_data.a * (diameter_arr ** species_data.b) * species_data.cf
    return years_arr, carbon_per * total_quantity
