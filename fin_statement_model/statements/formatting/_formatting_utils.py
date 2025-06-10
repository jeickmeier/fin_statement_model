"""Utility functions for formatting statement DataFrames."""

import pandas as pd
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


def render_values(
    df: pd.DataFrame,
    period_columns: list[str],
    default_formats: dict[str, Any],
    number_format: Optional[str] = None,
    contra_display_style: Optional[str] = "parentheses",
) -> pd.DataFrame:
    """Render values by applying sign conventions, number formatting, and contra styling."""
    # 1. Apply sign conventions to numeric data
    signed_df = apply_sign_convention(df, period_columns)

    # 2. Format numbers to strings
    formatted_df = format_numbers(
        signed_df,
        default_formats,
        number_format=number_format,
        period_columns=period_columns,
    )

    # 3. Apply contra formatting to formatted strings
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
                formatted_df.loc[mask, col] = "(" + formatted_df.loc[mask, col] + ")"

    # 4. Assign formatted strings back to DataFrame
    result = df.copy()
    result[period_columns] = formatted_df[period_columns].astype("object")
    return result
