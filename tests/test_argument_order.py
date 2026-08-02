"""Regression tests for issue #18: series-key code order and period bounds."""

from __future__ import annotations

import pandas as pd
import pytest

from imfp.data import _codes_in_parameter_order, _transform_period_for_frequency


def test_codes_in_parameter_order_reorders_caller_freq_list():
    """Caller list order A,Q,M must become codebook order A,M,Q."""
    codebook = pd.DataFrame(
        {
            "input_code": ["A", "D", "M", "Q", "S", "W"],
            "description": [
                "Annual",
                "Daily",
                "Monthly",
                "Quarterly",
                "Half-yearly, semester",
                "Weekly",
            ],
        }
    )
    assert _codes_in_parameter_order(["A", "Q", "M"], codebook) == ["A", "M", "Q"]
    assert _codes_in_parameter_order(["Q", "A", "M"], codebook) == ["A", "M", "Q"]


def test_codes_in_parameter_order_preserves_indicator_codebook_order():
    codebook = pd.DataFrame(
        {
            "input_code": ["TTT_IX", "GGX_G01_GDP_PT"],
            "description": ["Terms of trade", "Government expenditure"],
        }
    )
    assert _codes_in_parameter_order(["GGX_G01_GDP_PT", "TTT_IX"], codebook) == [
        "TTT_IX",
        "GGX_G01_GDP_PT",
    ]


def test_codes_in_parameter_order_empty_selection_or_codebook():
    codebook = pd.DataFrame({"input_code": ["A"], "description": ["Annual"]})
    assert _codes_in_parameter_order([], codebook) == []
    assert (
        _codes_in_parameter_order(
            ["A"], pd.DataFrame({"input_code": [], "description": []})
        )
        == []
    )


@pytest.mark.parametrize(
    ("period", "frequency", "bound", "expected"),
    [
        ("2019", ["A"], "start", "2019-A1"),
        ("2019", ["A"], "end", "2019-A1"),
        ("2019", ["Q"], "start", "2019-Q1"),
        ("2019", ["Q"], "end", "2019-Q4"),
        ("2019", ["M"], "start", "2019-M01"),
        ("2019", ["M"], "end", "2019-M12"),
        ("2019", ["A", "Q", "M"], "start", "2019-A1"),
        ("2019", ["A", "Q", "M"], "end", "2019-W99"),
        ("2019", None, "start", "2019-A1"),
        ("2019", None, "end", "2019-W99"),
        ("2019", [], "start", "2019-A1"),
        ("2019", [], "end", "2019-W99"),
        ("2019-03", ["M"], "start", "2019-M03"),
        ("2019-Q2", ["Q"], "end", "2019-Q2"),
    ],
)
def test_transform_period_for_frequency_bounds(period, frequency, bound, expected):
    assert _transform_period_for_frequency(period, frequency, bound=bound) == expected


def test_multi_freq_end_bound_includes_quarterly_and_monthly():
    """le:YYYY-A1 excludes Q/M periods; omitted/multi freq must use a high sentinel."""
    end = _transform_period_for_frequency("2019", None, bound="end")
    assert end is not None
    assert "2019-Q4" <= end
    assert "2019-M12" <= end
