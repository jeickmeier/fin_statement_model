"""Utility functions for formatting statement DataFrames."""

import pandas as pd
import numpy as np  # Added for vectorized formatting
from typing import Optional, Any  # Keep necessary imports
from pandas.api.types import is_numeric_dtype


def apply_sign_convention(df: pd.DataFrame, period_columns: list[str]) -> pd.DataFrame:
    """Apply sign conventions to the statement values across periods."""
    result = df.copy()
    if "sign_convention" in result.columns:
        for col in period_columns:
            if col in result.columns and is_numeric_dtype(result[col]):
                mask = result[col].notna()
                # Ensure sign_convention is treated as numeric if needed
                sign_col = pd.to_numeric(
                    result.loc[mask, "sign_convention"], errors="coerce"
                ).fillna(1)
                result.loc[mask, col] = result.loc[mask, col] * sign_col
    return result


def format_numbers(
    df: pd.DataFrame,
    default_formats: dict[str, Any],  # Pass defaults needed
    number_format: Optional[str] = None,
    period_columns: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Format numeric values in the statement.

    Args:
        df: DataFrame to format numbers in
        default_formats: Dictionary containing default formatting options
                         (e.g., 'precision', 'use_thousands_separator').
        number_format: Optional format string
        period_columns: List of columns containing period data to format.
                        If None, attempts to format all numeric columns
                        except metadata/indicators.

    Returns:
        pd.DataFrame: DataFrame with formatted numbers
    """
    result = df.copy()

    if period_columns:
        numeric_cols = [
            col
            for col in period_columns
            if col in result.columns and is_numeric_dtype(result[col])
        ]
    else:
        # Original logic if period_columns not specified
        numeric_cols = [
            col
            for col in result.columns
            if is_numeric_dtype(result[col])
            and col not in ("sign_convention", "depth", "ID")  # Added ID
            and not col.startswith("meta_")
            and col != "Line Item"  # Ensure Line Item name is not formatted
        ]

    # Get defaults from the passed dictionary
    precision = default_formats.get("precision", 2)  # Provide fallback default
    use_thousands = default_formats.get("use_thousands_separator", True)

    if number_format:
        # Use provided format string
        for col in numeric_cols:
            # Check if column exists before applying format
            if col in result.columns:
                result[col] = result[col].apply(
                    lambda x: f"{x:{number_format}}" if pd.notna(x) else ""
                )
    else:
        # Use default formatting based on passed defaults
        for col in numeric_cols:
            # Check if column exists before applying format
            if col in result.columns:
                result[col] = result[col].apply(
                    lambda x: (
                        (f"{x:,.{precision}f}" if pd.notna(x) else "")
                        if use_thousands
                        else (f"{x:.{precision}f}" if pd.notna(x) else "")
                    )
                )

    return result


# Consolidated formatting utility
def render_values(
    df: pd.DataFrame,
    period_columns: list[str],
    default_formats: dict[str, Any],
    number_format: Optional[str] = None,
    contra_display_style: str = "parentheses",
) -> pd.DataFrame:
    """Render values by applying sign conventions, contra formatting, and number formatting in a single vectorized pass.

    Args:
        df: DataFrame with period columns, 'sign_convention', and 'is_contra'.
        period_columns: List of DataFrame columns with period data to format.
        default_formats: Defaults containing 'precision' and 'use_thousands_separator'.
        number_format: Optional Python format string to override default formatting.
        contra_display_style: Style for contra items ('parentheses', 'negative_sign', 'brackets').

    Returns:
        pd.DataFrame: New DataFrame with formatted string values in period columns.
    """
    result = df.copy()

    # 1. Apply sign conventions vectorized
    if "sign_convention" in result.columns:
        signs = result["sign_convention"].fillna(1).to_numpy(dtype=float)
    else:
        signs = np.ones(len(result), dtype=float)
    vals = result.loc[:, period_columns].to_numpy(dtype=float)
    vals = vals * signs[:, None]

    # 2. Prepare format string
    if number_format:
        fmt = "{:" + number_format + "}"
    else:
        precision = default_formats.get("precision", 2)
        use_thousands = default_formats.get("use_thousands_separator", True)
        sep = "," if use_thousands else ""
        fmt = f"{{:{sep}.{precision}f}}"

    # 3. Vectorized formatting
    mask_valid = ~np.isnan(vals)
    base = np.full(vals.shape, "", dtype=object)
    base[mask_valid] = np.char.mod(fmt, vals[mask_valid])

    # 4. Contra formatting
    if "is_contra" in result.columns:
        contra_mask = result["is_contra"].fillna(False).to_numpy(dtype=bool)
    else:
        contra_mask = np.zeros(len(result), dtype=bool)
    contra2d = contra_mask[:, None] & mask_valid
    abs_vals = np.abs(vals)
    abs_fmt = np.full(vals.shape, "", dtype=object)
    abs_fmt[mask_valid] = np.char.mod(fmt, abs_vals[mask_valid])

    if contra_display_style == "parentheses":
        styled = np.char.add("(", np.char.add(abs_fmt, ")"))
    elif contra_display_style == "negative_sign":
        styled = np.char.add("-", abs_fmt)
    elif contra_display_style == "brackets":
        styled = np.char.add("[", np.char.add(abs_fmt, "]"))
    else:
        styled = np.char.add("(", np.char.add(abs_fmt, ")"))

    rendered = np.where(contra2d, styled, base)

    # 5. Assign back to DataFrame
    formatted_df = pd.DataFrame(rendered, index=result.index, columns=period_columns)
    result.loc[:, period_columns] = formatted_df

    return result
