import pandas as pd
import pytest

from fin_statement_model.utils.formatting import (
    apply_sign_convention,
    format_numbers,
    render_values,
)


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Provide a small DataFrame for formatting tests."""
    return pd.DataFrame(
        {
            "sign_convention": [1, -1],
            "is_contra": [False, True],
            "2023": [100, 200],
            "2024": [110, 210],
        }
    )


def test_apply_sign_convention(sample_df: pd.DataFrame) -> None:
    adjusted = apply_sign_convention(sample_df, ["2023", "2024"])

    # Row 0 keeps positive sign
    assert adjusted.loc[0, "2023"] == 100
    # Row 1 is multiplied by -1 due to sign_convention = -1
    assert adjusted.loc[1, "2023"] == -200


def test_format_numbers_default_and_explicit(sample_df: pd.DataFrame) -> None:
    default_formats = {"precision": 0, "use_thousands_separator": True}

    # Default formatting (derived from defaults)
    formatted = format_numbers(sample_df, default_formats, period_columns=["2023"])
    assert formatted.loc[0, "2023"] == "100"  # No thousands separator required

    # Explicit format specifier overrides defaults
    explicit = format_numbers(
        sample_df, default_formats, number_format=",.1f", period_columns=["2023"]
    )
    assert explicit.loc[0, "2023"] == "100.0"


def test_render_values_parentheses(sample_df: pd.DataFrame) -> None:
    default_formats = {"precision": 0, "use_thousands_separator": False}

    rendered = render_values(
        sample_df, ["2023"], default_formats, contra_display_style="parentheses"
    )

    # Row 0 unaffected (not contra)
    assert rendered.loc[0, "2023"] == "100"  # simple formatting

    # Row 1 should show parentheses around the negative value
    assert rendered.loc[1, "2023"] == "(-200)"
