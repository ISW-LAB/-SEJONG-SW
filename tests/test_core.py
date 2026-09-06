# SPDX-License-Identifier: MIT
"""Regression tests for the scientific core and bundled equation library."""

from __future__ import annotations

import json
import math
from pathlib import Path
import unittest

import numpy as np

from carbon_calculator.calculations import (
    RangeViolation,
    calculate_carbon,
    project_future_carbon,
)
from carbon_calculator.data import (
    RESTORATION_ENVIRONMENTS,
    SHRUB_SPECIES,
    TREE_SPECIES,
    tree_species_for_env,
)
from carbon_calculator.data2 import DOMESTIC_SPECIES, FOREIGN_SPECIES
from carbon_calculator.equation_eval import EvaluationError, evaluate


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class LibraryTests(unittest.TestCase):
    def test_release_library_counts(self) -> None:
        self.assertEqual(len(TREE_SPECIES), 7)
        self.assertEqual(len(SHRUB_SPECIES), 15)
        self.assertEqual(len(DOMESTIC_SPECIES), 30)
        self.assertEqual(len(FOREIGN_SPECIES), 25)

    def test_bundled_json_is_parseable_and_licensed(self) -> None:
        payload = json.loads((REPOSITORY_ROOT / "species_data.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["_schema"]["license"], "KOGL Type 1 (Attribution)")
        self.assertEqual(len(payload["TREE_BASE"]), 7)
        self.assertEqual(len(payload["SHRUB_SPECIES"]), 15)

    def test_site_category_does_not_select_coefficients(self) -> None:
        baseline = tree_species_for_env(RESTORATION_ENVIRONMENTS[0])
        for category in RESTORATION_ENVIRONMENTS[1:]:
            self.assertEqual(tree_species_for_env(category), baseline)


class CalculationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pine = TREE_SPECIES["소나무"]

    def test_allometric_formula_and_exact_count_scaling(self) -> None:
        one = calculate_carbon("소나무", self.pine, 5.0, 1)
        hundred = calculate_carbon("소나무", self.pine, 5.0, 100)
        expected = self.pine.a * 5.0 ** self.pine.b * self.pine.cf
        self.assertIsNotNone(one)
        self.assertIsNotNone(hundred)
        self.assertAlmostEqual(one.carbon_kg, expected, places=12)
        self.assertAlmostEqual(hundred.carbon_kg, one.carbon_kg * 100, places=12)

    def test_zero_quantity_is_excluded(self) -> None:
        self.assertIsNone(calculate_carbon("소나무", self.pine, 5.0, 0))

    def test_diameter_boundaries_are_enforced(self) -> None:
        calculate_carbon("소나무", self.pine, self.pine.diameter_min, 1)
        calculate_carbon("소나무", self.pine, self.pine.diameter_max, 1)
        with self.assertRaises(RangeViolation):
            calculate_carbon("소나무", self.pine, self.pine.diameter_min - 0.1, 1)
        with self.assertRaises(RangeViolation):
            calculate_carbon("소나무", self.pine, self.pine.diameter_max + 0.1, 1)

    def test_projection_is_deterministic_and_matches_year_zero(self) -> None:
        current = calculate_carbon("소나무", self.pine, 5.0, 100)
        years_a, carbon_a = project_future_carbon(self.pine, 5.0, 100, years=50)
        years_b, carbon_b = project_future_carbon(self.pine, 5.0, 100, years=50)
        np.testing.assert_array_equal(years_a, years_b)
        np.testing.assert_array_equal(carbon_a, carbon_b)
        self.assertAlmostEqual(carbon_a[0], current.carbon_kg, places=12)

    def test_shrub_growth_is_converted_from_cm_to_mm(self) -> None:
        shrub = SHRUB_SPECIES["사철나무"]
        _, carbon = project_future_carbon(shrub, 10.0, 1, years=1, mm_scale=True)
        expected_diameter = 10.0 + shrub.growth_y10 * 10.0
        expected = shrub.a * expected_diameter ** shrub.b * shrub.cf
        self.assertAlmostEqual(carbon[1], expected, places=12)


class EquationEvaluatorTests(unittest.TestCase):
    def test_supported_equation_forms(self) -> None:
        self.assertAlmostEqual(evaluate("Y=0.063*X^2.578", 10), 0.063 * 10 ** 2.578)
        self.assertAlmostEqual(
            evaluate("ln(Y)=2.43*ln(X)-2.28", 10),
            math.exp(2.43 * math.log(10) - 2.28),
        )
        self.assertAlmostEqual(
            evaluate("Y=exp(-4.7483+1.7395*ln(X*H))", 10, 12),
            math.exp(-4.7483 + 1.7395 * math.log(120)),
        )

    def test_entire_compatibility_library_executes(self) -> None:
        for name, record in {**DOMESTIC_SPECIES, **FOREIGN_SPECIES}.items():
            if record.has_range:
                x = (record.diameter_min + record.diameter_max) / 2
            else:
                x = 10.0
            h = record.var2_default if record.is_multivar else None
            with self.subTest(name=name):
                self.assertTrue(math.isfinite(evaluate(record.equation, x, h)))

    def test_unsafe_or_unknown_syntax_is_rejected(self) -> None:
        unsafe = (
            "Y=__import__('os').system('echo unsafe')",
            "Y=(1).__class__",
            "Y=[X][0]",
            "Y=UNKNOWN(X)",
        )
        for equation in unsafe:
            with self.subTest(equation=equation), self.assertRaises(EvaluationError):
                evaluate(equation, 10)


if __name__ == "__main__":
    unittest.main()

