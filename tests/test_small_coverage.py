from __future__ import annotations

import pandas as pd
import pytest

from fin_statement_model.utils.formatting import format_numbers, render_values
from fin_statement_model.config import helpers as cfg_helpers


def test_format_numbers_fallback_and_thousands_separator_off():
    df = pd.DataFrame({"val1": [1000, 2000], "sign_convention": [1, 1]})
    # use_thousands_separator False path
    formatted = format_numbers(
        df,
        default_formats={"precision": 0, "use_thousands_separator": False},
        period_columns=["val1"],
    )
    # Expect no comma separator
    assert formatted.loc[0, "val1"] == "1000"

    # pass period_columns=None path and rely on default detection
    formatted2 = format_numbers(
        df,
        default_formats={"precision": 0},
        period_columns=None,
    )
    assert formatted2.loc[1, "val1"] == "2,000"


def test_render_values_unknown_contra_style():
    df = pd.DataFrame({"is_contra": [True], "2023": [-50.0]})
    rendered = render_values(
        df,
        period_columns=["2023"],
        default_formats={"precision": 0},
        contra_display_style="unsupported_style",
    )
    # Fallback expected to use parentheses
    assert rendered.loc[0, "2023"].startswith("(")


def test_cfg_errors_and_edge_cases():
    # Empty path should raise error
    with pytest.raises(cfg_helpers.ConfigurationAccessError):
        cfg_helpers.cfg("")

    # Path as list input and strict=False returns default
    assert cfg_helpers.cfg(["non", "existent"], default="foo") == "foo"
