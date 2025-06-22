from __future__ import annotations

import pandas as pd

from fin_statement_model.utils import formatting as fmt
from fin_statement_model.config.helpers import parse_env_value


def test_apply_sign_convention_basic() -> None:
    df = pd.DataFrame(
        {
            "sign_convention": [1, -1, None],
            "2023": [100, 50, 20],
        }
    )
    adjusted = fmt.apply_sign_convention(df, ["2023"])
    assert adjusted.loc[0, "2023"] == 100
    assert adjusted.loc[1, "2023"] == -50  # sign flipped
    assert adjusted.loc[2, "2023"] == 20  # missing sign -> unchanged


def test_format_numbers_and_render_values() -> None:
    df = pd.DataFrame(
        {
            "is_contra": [False, True],
            "2022": [1234.5, -99.9],
        }
    )
    # Default: thousands separator + 2 decimals
    formatted = fmt.render_values(
        df,
        period_columns=["2022"],
        default_formats={"precision": 1, "use_thousands_separator": True},
        contra_display_style="parentheses",
    )
    # First row: positive number with comma and 1 decimal
    assert formatted.loc[0, "2022"] == "1,234.5"
    # Second row: contra item wrapped in parentheses (absolute value formatted)
    assert formatted.loc[1, "2022"] == "(-99.9)"

    # Custom explicit format should override defaults
    explicit = fmt.format_numbers(
        df,
        default_formats={"precision": 3},
        number_format=".0f",
        period_columns=["2022"],
    )
    assert explicit.loc[0, "2022"] == "1234"  # Rounded by Python formatting (.0f)

    # Further contra display styles
    for style, expected_prefix in [("negative_sign", "-"), ("brackets", "[")]:
        styled = fmt.render_values(
            df,
            period_columns=["2022"],
            default_formats={"precision": 1},
            contra_display_style=style,
        )
        assert styled.loc[1, "2022"].startswith(expected_prefix)


def test_parse_env_value_various() -> None:
    assert parse_env_value("true") is True
    assert parse_env_value("FALSE") is False
    assert parse_env_value("42") == 42
    assert parse_env_value("-3.14") == -3.14
    assert parse_env_value("[1, 2, 3]") == [1, 2, 3]
    assert parse_env_value("foo") == "foo"
