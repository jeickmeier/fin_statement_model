"""Utility helpers for consistent numeric formatting across the library.

The module groups small, reusable functions that handle common string / number
formatting tasks shared by CLI reporters, statement formatters and higher-level
analysis helpers.  Keeping them here avoids duplicating logic (and associated
edge-cases) in multiple call-sites.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from pandas.api.types import is_numeric_dtype

__all__ = [
    "apply_sign_convention",
    "format_numbers",
    "render_values",
]

# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def apply_sign_convention(df: pd.DataFrame, period_columns: list[str]) -> pd.DataFrame:
    """Apply *sign_convention* column values (+1 or -1) to numeric period columns.

    This helper is agnostic of financial-statement specifics - it simply multiplies
    each numeric cell in *period_columns* by the corresponding row's
    ``sign_convention`` (if present).  Missing conventions default to ``1`` (no
    change).

    Args:
        df: Source DataFrame.
        period_columns: Column names that contain numeric statement values.

    Returns:
        A *copy* of *df* with adjusted sign for contra-style rows.
    """
    result = df.copy()
    if "sign_convention" not in result.columns:
        return result

    for col in period_columns:
        if col in result.columns and is_numeric_dtype(result[col]):
            mask = result[col].notna()
            # Convert sign column to numeric to guard against accidental strings.
            sign_col = pd.to_numeric(result.loc[mask, "sign_convention"], errors="coerce").fillna(1)
            result.loc[mask, col] = result.loc[mask, col] * sign_col
    return result


def format_numbers(
    df: pd.DataFrame,
    default_formats: dict[str, Any],
    *,
    number_format: str | None = None,
    period_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Format numeric values as strings according to *number_format* or defaults.

    If *number_format* is omitted, the helper falls back to values contained in
    *default_formats* (typically provided by config):

    * ``precision`` - number of decimal places (int, default ``2``)
    * ``use_thousands_separator`` - comma-separate thousands if *True*

    Non-numeric columns are left untouched, as are DataFrame-level metadata
    columns such as ``sign_convention`` or ``depth``.

    Args:
        df: DataFrame whose numeric cells will be string-formatted.
        default_formats: Library-wide default formatting options.
        number_format: Explicit Python format specifier (e.g. ``',.1f'``).  Takes
            precedence over defaults.
        period_columns: Sub-selection of columns to format.  If *None*, all
            numeric, non-metadata columns are considered.

    Returns:
        A *copy* of the DataFrame with formatted **string** values in the chosen
        columns.  Unaffected columns preserve their original dtype.
    """
    result = df.copy()

    # Determine columns that should be formatted.
    if period_columns is not None:
        numeric_cols = [col for col in period_columns if col in result.columns and is_numeric_dtype(result[col])]
    else:
        # Fallback: any numeric column except explicit metadata helpers.
        numeric_cols = [
            col
            for col in result.columns
            if is_numeric_dtype(result[col])
            and col not in {"sign_convention", "depth", "ID"}
            and not col.startswith("meta_")
            and col != "Line Item"
        ]

    if not numeric_cols:
        return result

    # Resolve precision & thousand-separator defaults if *number_format* omitted.
    precision = default_formats.get("precision", 2)
    use_thousands = default_formats.get("use_thousands_separator", True)

    if number_format is not None:
        # Apply explicit Python format specifier.
        for col in numeric_cols:
            if col in result.columns:
                result[col] = result[col].apply(lambda x: f"{x:{number_format}}" if pd.notna(x) else "")
    else:
        # Derive basic format string from defaults.
        fmt = f",.{precision}f" if use_thousands else f".{precision}f"
        for col in numeric_cols:
            if col in result.columns:
                result[col] = result[col].apply(lambda x: f"{x:{fmt}}" if pd.notna(x) else "")

    return result


def render_values(
    df: pd.DataFrame,
    period_columns: list[str],
    default_formats: dict[str, Any],
    *,
    number_format: str | None = None,
    contra_display_style: str | None = "parentheses",
) -> pd.DataFrame:
    """High-level helper that combines *sign*, *number*, and contra formatting.

    The rendering pipeline is:

    1. Apply sign convention (positive / negative) to raw numeric values.
    2. Convert numbers to strings via :pyfunc:`format_numbers`.
    3. Apply contra-item styling (parentheses, minus sign, brackets).

    Args:
        df: Source DataFrame.
        period_columns: Names of period/value columns to transform.
        default_formats: Project-level default number formatting options.
        number_format: Optional explicit Python format specifier.
        contra_display_style: How contra numbers are displayed.

    Returns:
        A *new* DataFrame object with formatted string values.
    """
    # 1) Apply sign conventions.
    signed_df = apply_sign_convention(df, period_columns)

    # 2) Number → string conversion.
    formatted_df = format_numbers(
        signed_df,
        default_formats,
        number_format=number_format,
        period_columns=period_columns,
    )

    # 3) Contra display tweaks.
    if "is_contra" in df.columns:
        contra_mask = df["is_contra"].fillna(False)
        for col in period_columns:
            mask = contra_mask & formatted_df[col].astype(bool)
            if contra_display_style == "parentheses":
                formatted_df.loc[mask, col] = "(" + formatted_df.loc[mask, col] + ")"
            elif contra_display_style == "negative_sign":
                formatted_df.loc[mask, col] = "-" + formatted_df.loc[mask, col]
            elif contra_display_style == "brackets":
                formatted_df.loc[mask, col] = "[" + formatted_df.loc[mask, col] + "]"
            else:
                # Default fallback.
                formatted_df.loc[mask, col] = "(" + formatted_df.loc[mask, col] + ")"

    # 4) Assign back (& cast to object dtype so mixed string/float doesn't break).
    result = df.copy()
    result[period_columns] = formatted_df[period_columns].astype("object")
    return result
