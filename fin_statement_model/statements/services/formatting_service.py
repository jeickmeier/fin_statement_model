"""Formatting service for financial statements.

Provides classes to generate pandas DataFrame or HTML outputs from statement data.
"""

import pandas as pd
from typing import Optional

from fin_statement_model.statements.formatter import StatementFormatter
from fin_statement_model.statements.structure import StatementStructure

__all__ = ["DataFrameFormatter", "HtmlFormatter"]


class DataFrameFormatter:
    """Formatter for generating pandas DataFrame from statement data."""

    def __init__(self, structure: StatementStructure):
        """Initialize the DataFrameFormatter.

        Args:
            structure: The StatementStructure defining items and hierarchy.
        """
        self._formatter = StatementFormatter(structure)

    def generate(
        self,
        data: dict[str, dict[str, float]],
        apply_sign_convention: bool = True,
        include_empty_items: bool = False,
    ) -> pd.DataFrame:
        """Generate a formatted DataFrame of the statement.

        Args:
            data: Mapping of node IDs to period-value dicts.
            apply_sign_convention: Whether to apply sign conventions.
            include_empty_items: Whether to include items with no data.

        Returns:
            pd.DataFrame: Formatted statement DataFrame.
        """
        return self._formatter.generate_dataframe(
            data, apply_sign_convention, include_empty_items
        )


class HtmlFormatter:
    """Formatter for generating HTML representation of statement data."""

    def __init__(self, structure: StatementStructure):
        """Initialize the HtmlFormatter.

        Args:
            structure: The StatementStructure defining items and hierarchy.
        """
        self._formatter = StatementFormatter(structure)

    def generate(
        self,
        data: dict[str, dict[str, float]],
        apply_sign_convention: bool = True,
        include_empty_items: bool = False,
        css_styles: Optional[dict[str, str]] = None,
    ) -> str:
        """Generate an HTML table of the statement.

        Args:
            data: Mapping of node IDs to period-value dicts.
            apply_sign_convention: Whether to apply sign conventions.
            include_empty_items: Whether to include empty items.
            css_styles: Optional dict of CSS styles for the HTML.

        Returns:
            str: HTML string representing the statement.
        """
        return self._formatter.format_html(
            data, apply_sign_convention, include_empty_items, css_styles
        )
