"""Formatter for financial statements.

This module provides functionality for formatting financial statements
for display or reporting, including applying formatting rules, adding subtotals,
and applying sign conventions with enhanced display control.
"""

import pandas as pd
import numpy as np  # Added numpy for NaN handling
import warnings  # Added for suppressing dtype warnings
from typing import Optional, Any, Union
import logging

from fin_statement_model.statements.structure import StatementStructure
from fin_statement_model.statements.structure import (
    Section,
    CalculatedLineItem,
    SubtotalLineItem,
    StatementItem,
)

# Add core Graph and errors
from fin_statement_model.core.graph import Graph

# Import adjustment types for filtering
from fin_statement_model.core.adjustments.models import AdjustmentFilterInput

# Import the ID resolver
from fin_statement_model.statements.population.id_resolver import IDResolver

# Import the data fetcher
from fin_statement_model.statements.formatting.data_fetcher import DataFetcher

# Import the new formatting utils
from ._formatting_utils import format_numbers
from ._formatting_utils import apply_sign_convention as apply_sign_convention_func

# Configure logging
logger = logging.getLogger(__name__)


class StatementFormatter:
    """Formats financial statements for display or reporting.

    This class provides methods to transform raw financial data into
    formatted financial statements with proper headers, indentation,
    subtotals, sign conventions, and enhanced display control.
    """

    def __init__(self, statement: StatementStructure):
        """Initialize a statement formatter.

        Args:
            statement: The statement structure to format
        """
        self.statement = statement
        self.config = {}  # TODO: Consider how config is passed/used
        self.default_formats = {
            "precision": 2,
            "use_thousands_separator": True,
            "show_zero_values": True,  # TODO: Check if used
            "show_negative_sign": True,  # TODO: Check if used
            "indent_character": "  ",
            "subtotal_style": "bold",  # TODO: Check if used
            "total_style": "bold",  # TODO: Check if used
            "header_style": "bold",  # TODO: Check if used
            # Contra item display options
            "contra_display_style": "parentheses",  # Options: "parentheses", "negative_sign", "brackets"
            "contra_css_class": "contra-item",  # CSS class for contra items
        }

    def _resolve_display_scale_factor(self, item: Union[StatementItem, Section]) -> float:
        """Resolve the display scale factor for an item, considering hierarchy.

        Precedence: Item > Section > Statement > Default (1.0)

        Args:
            item: The item or section to get the scale factor for

        Returns:
            The resolved scale factor
        """
        # Check item-specific scale factor
        if hasattr(item, "display_scale_factor") and item.display_scale_factor != 1.0:
            return item.display_scale_factor

        # Check if item is part of a section with a scale factor
        if isinstance(item, StatementItem):
            parent_section = self._find_parent_section_for_item(item)
            if (
                parent_section
                and hasattr(parent_section, "display_scale_factor")
                and parent_section.display_scale_factor != 1.0
            ):
                return parent_section.display_scale_factor

        # Check statement-level scale factor
        if (
            hasattr(self.statement, "display_scale_factor")
            and self.statement.display_scale_factor != 1.0
        ):
            return self.statement.display_scale_factor

        # Default
        return 1.0

    def _resolve_units(self, item: Union[StatementItem, Section]) -> Optional[str]:
        """Resolve the unit description for an item, considering hierarchy.

        Precedence: Item > Section > Statement > None

        Args:
            item: The item or section to get the units for

        Returns:
            The resolved unit description or None
        """
        # Check item-specific units
        if hasattr(item, "units") and item.units:
            return item.units

        # Check if item is part of a section with units
        if isinstance(item, StatementItem):
            parent_section = self._find_parent_section_for_item(item)
            if parent_section and hasattr(parent_section, "units") and parent_section.units:
                return parent_section.units

        # Check statement-level units
        if hasattr(self.statement, "units") and self.statement.units:
            return self.statement.units

        return None

    def _find_parent_section_for_item(self, target_item: StatementItem) -> Optional[Section]:
        """Find the parent section that contains the given item.

        Args:
            target_item: The item to find the parent section for.

        Returns:
            The parent Section object, or None if not found.
        """

        def search_in_section(section: Section) -> Optional[Section]:
            # Check direct items
            for item in section.items:
                if item is target_item or (
                    hasattr(item, "id") and hasattr(target_item, "id") and item.id == target_item.id
                ):
                    return section
                # Check nested sections
                if isinstance(item, Section):
                    result = search_in_section(item)
                    if result:
                        return result

            # Check subtotal
            if hasattr(section, "subtotal") and section.subtotal is target_item:
                return section

            return None

        # Search through all top-level sections
        for section in self.statement.sections:
            result = search_in_section(section)
            if result:
                return result

        return None

    def _should_hide_item(
        self, item: Union[StatementItem, Section], values: dict[str, float]
    ) -> bool:
        """Check if an item should be hidden based on hide_if_all_zero setting.

        Args:
            item: The item to check
            values: Dictionary of period values for the item

        Returns:
            True if the item should be hidden
        """
        # Check if the item has hide_if_all_zero enabled
        hide_if_zero = getattr(item, "hide_if_all_zero", False)
        if not hide_if_zero:
            return False

        # Check if all values are zero or NaN
        return all(not (pd.notna(value) and value != 0) for value in values.values())

    def _apply_item_scaling(
        self, values: dict[str, float], scale_factor: float
    ) -> dict[str, float]:
        """Apply scaling to item values.

        Args:
            values: Dictionary of period values
            scale_factor: Factor to scale by

        Returns:
            Dictionary of scaled values
        """
        if scale_factor == 1.0:
            return values

        scaled_values = {}
        for period, value in values.items():
            if pd.notna(value):
                scaled_values[period] = value * scale_factor
            else:
                scaled_values[period] = value

        return scaled_values

    def _format_item_values(
        self,
        item: Union[StatementItem, Section],
        values: dict[str, float],
        period_columns: list[str],
    ) -> dict[str, str]:
        """Format values for an item using its specific display format if available.

        Args:
            item: The item to format values for
            values: Dictionary of period values
            period_columns: List of period column names

        Returns:
            Dictionary of formatted values
        """
        # Get item-specific display format
        item_format = getattr(item, "display_format", None)

        formatted_values = {}
        for period in period_columns:
            value = values.get(period, np.nan)

            if pd.notna(value):
                if item_format:
                    try:
                        formatted_values[period] = f"{value:{item_format}}"
                    except (ValueError, TypeError):
                        # Fall back to default if format is invalid
                        logger.warning(
                            f"Invalid display format '{item_format}' for item '{getattr(item, 'id', 'unknown')}', using default"
                        )
                        formatted_values[period] = str(value)  # Convert to string for consistency
                else:
                    formatted_values[period] = str(value)  # Convert to string for consistency
            else:
                formatted_values[period] = ""

        return formatted_values

    def _format_contra_value(self, value: float, display_style: str | None = None) -> str:
        """Format a contra item value according to the specified display style.

        Args:
            value: The numeric value to format
            display_style: Style for contra display ("parentheses", "negative_sign", "brackets")

        Returns:
            Formatted string representation of the contra value
        """
        if pd.isna(value) or value == 0:
            return ""

        style = display_style or self.default_formats.get("contra_display_style", "parentheses")

        # For contra items, we typically want to show the absolute value with special formatting
        # regardless of the underlying sign, since sign_convention handles calculation logic
        abs_value = abs(value)

        # Use dictionary for style formatting
        style_formats = {
            "parentheses": f"({abs_value:,.2f})",
            "negative_sign": f"-{abs_value:,.2f}",
            "brackets": f"[{abs_value:,.2f}]",
        }

        return style_formats.get(style, f"({abs_value:,.2f})")  # Default fallback

    def _apply_contra_formatting(
        self,
        item: Union[StatementItem, Section],
        values: dict[str, float],
        period_columns: list[str],
        display_style: str | None = None,
    ) -> dict[str, str]:
        """Apply contra-specific formatting to item values.

        Args:
            item: The item to format
            values: Dictionary of period values
            period_columns: List of period column names
            display_style: Optional override for contra display style

        Returns:
            Dictionary of formatted contra values
        """
        contra_formatted = {}
        for period in period_columns:
            value = values.get(period, np.nan)
            contra_formatted[period] = self._format_contra_value(value, display_style)

        return contra_formatted

    def generate_dataframe(
        self,
        graph: Graph,
        should_apply_signs: bool = True,  # Renamed arg
        include_empty_items: bool = False,
        number_format: Optional[str] = None,
        include_metadata_cols: bool = False,
        # --- Adjustment Integration ---
        adjustment_filter: AdjustmentFilterInput = None,
        add_is_adjusted_column: bool = False,
        # --- End Adjustment Integration ---
        # --- Enhanced Display Control ---
        include_units_column: bool = True,
        include_css_classes: bool = False,
        include_notes_column: bool = False,
        apply_item_scaling: bool = True,
        apply_item_formatting: bool = True,
        respect_hide_flags: bool = True,
        # --- Contra Item Support ---
        contra_display_style: Optional[str] = None,
        apply_contra_formatting: bool = True,
        add_contra_indicator_column: bool = False,
        # --- End Contra Item Support ---
        # --- End Enhanced Display Control ---
    ) -> pd.DataFrame:
        """Generate a formatted DataFrame of the statement including subtotals.

        Queries the graph for data based on the statement structure,
        calculates subtotals, and formats the result with enhanced display control.

        Args:
            graph: The core.graph.Graph instance containing the data.
            should_apply_signs: Whether to apply sign conventions after calculation.
            include_empty_items: Whether to include items with no data rows.
            number_format: Optional Python format string for numbers (e.g., ',.2f').
            include_metadata_cols: If True, includes hidden metadata columns
                                   (like sign_convention, node_id) in the output.
            adjustment_filter: Optional filter for applying adjustments during data fetch.
            add_is_adjusted_column: If True, adds a boolean column indicating if the
                                    value for a node/period was adjusted.
            include_units_column: If True, includes a column showing units for each item.
            include_css_classes: If True, includes CSS class information in metadata.
            include_notes_column: If True, includes a column with note references.
            apply_item_scaling: If True, applies item-specific scaling factors.
            apply_item_formatting: If True, applies item-specific number formats.
            respect_hide_flags: If True, respects hide_if_all_zero flags.
            contra_display_style: Optional contra display style for items
            apply_contra_formatting: If True, applies contra-specific formatting
            add_contra_indicator_column: If True, adds a column indicating contra items

        Returns:
            pd.DataFrame: Formatted statement DataFrame with subtotals and enhanced display control.
        """
        # Use DataFetcher to get data
        data_fetcher = DataFetcher(self.statement, graph)
        fetch_result = data_fetcher.fetch_all_data(
            adjustment_filter=adjustment_filter,
            include_missing=include_empty_items,
        )

        # Log any warnings/errors from fetching
        if fetch_result.errors.has_warnings() or fetch_result.errors.has_errors():
            fetch_result.errors.log_all(prefix=f"Statement '{self.statement.id}' data fetch: ")

        data = fetch_result.data
        all_periods = graph.periods

        # Initialize ID resolver for consistent node ID resolution
        id_resolver = IDResolver(self.statement)

        # --- Build Rows Recursively --- #
        rows: list[dict[str, Any]] = []
        indent_char = self.default_formats["indent_character"]
        items_to_hide = set()  # Track items that should be hidden

        def process_recursive(
            items_or_sections: list[Union[Section, StatementItem]], current_depth: int
        ) -> None:
            for item in items_or_sections:
                if isinstance(item, Section):
                    # Process section items first to collect data for hide check
                    process_recursive(item.items, current_depth + 1)
                    if hasattr(item, "subtotal") and item.subtotal:
                        process_recursive(
                            [item.subtotal], current_depth + 1
                        )  # Process subtotal like other items

                    # Check if section should be hidden
                    if respect_hide_flags and getattr(item, "hide_if_all_zero", False):
                        # For sections, check if all contained items are hidden or zero
                        section_has_data = False
                        for section_item in item.items:
                            node_id = id_resolver.resolve(section_item.id, graph)
                            if node_id and node_id in data:
                                item_data = data[node_id]
                                if any(pd.notna(v) and v != 0 for v in item_data.values()):
                                    section_has_data = True
                                    break
                        if not section_has_data:
                            items_to_hide.add(item.id)

                elif isinstance(item, StatementItem):
                    # Use ID resolver to get the correct node ID
                    node_id = id_resolver.resolve(item.id, graph)
                    if node_id:
                        item_data = data.get(node_id, {})
                        row_values = {p: item_data.get(p, np.nan) for p in all_periods}

                        # Apply item-specific scaling if enabled
                        if apply_item_scaling:
                            scale_factor = self._resolve_display_scale_factor(item)
                            row_values = self._apply_item_scaling(row_values, scale_factor)

                        # Check if item should be hidden
                        if respect_hide_flags and self._should_hide_item(item, row_values):
                            items_to_hide.add(item.id)
                            return

                        # Apply item-specific formatting if enabled (but only if not using global format)
                        if apply_item_formatting and not number_format:
                            formatted_values = self._format_item_values(
                                item, row_values, all_periods
                            )
                            # Only apply if we got actual formatted strings
                            if any(isinstance(v, str) for v in formatted_values.values()):
                                for period in all_periods:
                                    if period in formatted_values and isinstance(
                                        formatted_values[period], str
                                    ):
                                        # Keep numeric value for calculations, store formatted for display
                                        row_values[f"{period}_formatted"] = formatted_values[period]

                        # Apply contra formatting if enabled and item is marked as contra
                        if apply_contra_formatting and getattr(item, "is_contra", False):
                            contra_formatted = self._apply_contra_formatting(
                                item, row_values, all_periods, contra_display_style
                            )
                            # Store contra formatted values for later use
                            for period in all_periods:
                                if contra_formatted.get(period):
                                    row_values[f"{period}_contra"] = contra_formatted[period]

                        if include_empty_items or any(pd.notna(v) for v in row_values.values()):
                            row = {
                                "Line Item": indent_char * current_depth + item.name,
                                "ID": item.id,
                                **row_values,
                                # Metadata
                                "line_type": self._get_item_type(item),
                                "node_id": node_id,
                                "sign_convention": getattr(item, "sign_convention", 1),
                                "is_subtotal": isinstance(item, SubtotalLineItem),
                                "is_calculated": isinstance(item, CalculatedLineItem),
                                "is_contra": getattr(item, "is_contra", False),
                            }

                            # Add enhanced metadata columns if requested
                            if include_units_column:
                                row["units"] = self._resolve_units(item)

                            if include_css_classes:
                                # Get item's CSS class and add contra class if applicable
                                item_css_class = getattr(item, "css_class", None)
                                if getattr(item, "is_contra", False):
                                    contra_css = self.default_formats.get(
                                        "contra_css_class", "contra-item"
                                    )
                                    if item_css_class:
                                        row["css_class"] = f"{item_css_class} {contra_css}"
                                    else:
                                        row["css_class"] = contra_css
                                else:
                                    row["css_class"] = item_css_class

                            if include_notes_column:
                                notes = getattr(item, "notes_references", [])
                                row["notes"] = "; ".join(notes) if notes else ""

                            rows.append(row)

        process_recursive(self.statement.sections, 0)

        # Filter out hidden items if respect_hide_flags is enabled
        if respect_hide_flags:
            rows = [row for row in rows if row["ID"] not in items_to_hide]
        # --- End Build Rows --- #

        if not rows:
            base_cols = ["Line Item", "ID", *all_periods]
            if include_units_column:
                base_cols.append("units")
            return pd.DataFrame(columns=base_cols)

        df = pd.DataFrame(rows)

        base_cols = ["Line Item", "ID"]
        metadata_cols = [
            "line_type",
            "node_id",
            "sign_convention",
            "is_subtotal",
            "is_calculated",
            "is_contra",
        ]

        # Enhanced metadata columns
        enhanced_cols = []
        if include_units_column:
            enhanced_cols.append("units")
        if include_css_classes:
            enhanced_cols.append("css_class")
        if include_notes_column:
            enhanced_cols.append("notes")
        if add_contra_indicator_column:
            enhanced_cols.append("is_contra")

        # --- Adjustment Integration: Add 'is_adjusted' column if requested ---
        adjusted_flag_cols = []
        if add_is_adjusted_column and all_periods:
            # Get node IDs from the dataframe
            node_ids_to_check = []
            for _, row in df.iterrows():
                node_id = row.get("node_id")
                is_calc_or_subtotal = row.get("is_calculated", False) or row.get(
                    "is_subtotal", False
                )
                if node_id and not is_calc_or_subtotal:
                    node_ids_to_check.append(node_id)

            # Use DataFetcher to check adjustments
            if node_ids_to_check:
                adjustment_status = data_fetcher.check_adjustments(
                    node_ids_to_check, all_periods, adjustment_filter
                )
            else:
                adjustment_status = {}

            # Build adjustment columns
            is_adjusted_data = []
            for _, row in df.iterrows():
                node_id = row.get("node_id")
                is_calc_or_subtotal = row.get("is_calculated", False) or row.get(
                    "is_subtotal", False
                )

                if node_id and not is_calc_or_subtotal and node_id in adjustment_status:
                    row_adj_flags = {
                        f"{period}_is_adjusted": adjustment_status[node_id].get(period, False)
                        for period in all_periods
                    }
                else:
                    # For calculated/subtotal items or missing nodes, flags are False
                    row_adj_flags = {f"{period}_is_adjusted": False for period in all_periods}
                is_adjusted_data.append(row_adj_flags)

            if is_adjusted_data:
                adj_df = pd.DataFrame(is_adjusted_data, index=df.index)
                df = pd.concat([df, adj_df], axis=1)
                adjusted_flag_cols = list(adj_df.columns)
        # --- End Adjustment Integration ---

        final_cols = base_cols + all_periods
        if add_is_adjusted_column:
            final_cols += adjusted_flag_cols  # Add adjustment flag columns here
        if enhanced_cols:
            final_cols += enhanced_cols
        if include_metadata_cols:
            # Add metadata cols (excluding adjustment flags if they are already added)
            final_cols += [m_col for m_col in metadata_cols if m_col not in adjusted_flag_cols]

        # Ensure contra formatting columns are available temporarily (will be removed later)
        all_available_cols = final_cols.copy()
        if apply_contra_formatting:
            contra_formatted_cols = [f"{period}_contra" for period in all_periods]
            all_available_cols += contra_formatted_cols

        for col in all_available_cols:
            if col not in df.columns:
                df[col] = np.nan if col in all_periods else ("" if col == "Line Item" else None)

        df = df[all_available_cols]

        # Use imported function and renamed argument
        if should_apply_signs:  # Check the renamed argument
            # Call the imported function
            df = apply_sign_convention_func(df, all_periods)

        # Apply contra formatting for contra items (after sign conventions, before number formatting)
        if apply_contra_formatting:
            for index, row in df.iterrows():
                if row.get("is_contra", False):
                    for period in all_periods:
                        contra_col = f"{period}_contra"
                        if contra_col in row and pd.notna(row[contra_col]) and row[contra_col]:
                            # Suppress dtype warnings since we're intentionally converting float to string
                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore", FutureWarning)
                                df.at[index, period] = row[contra_col]
            
            # Remove the contra formatting columns from the final output
            contra_cols_to_remove = [f"{period}_contra" for period in all_periods]
            df = df.drop(columns=[col for col in contra_cols_to_remove if col in df.columns])
            
            # Select only the final columns for output
            df = df[final_cols]

        # Use imported function for number formatting (only if no item-specific formatting applied)
        if not apply_item_formatting or number_format:
            df = format_numbers(
                df,
                default_formats=self.default_formats,
                number_format=number_format,
                period_columns=all_periods,
            )

        return df

    def _get_item_type(self, item: StatementItem) -> str:
        """Get the type of a statement item.

        Args:
            item: Statement item to get type for

        Returns:
            str: Item type identifier
        """
        if isinstance(item, Section):
            return "section"
        elif isinstance(item, SubtotalLineItem):
            return "subtotal"
        elif isinstance(item, CalculatedLineItem):
            return "calculated"
        else:
            return "item"

    def format_html(
        self,
        graph: Graph,
        should_apply_signs: bool = True,  # Use consistent arg name
        include_empty_items: bool = False,
        css_styles: Optional[dict[str, str]] = None,
        use_item_css_classes: bool = True,
        **kwargs: Any,
    ) -> str:
        """Format the statement data as HTML with enhanced styling support.

        Args:
            graph: The core.graph.Graph instance containing the data.
            should_apply_signs: Whether to apply sign conventions.
            include_empty_items: Whether to include items with no data.
            css_styles: Optional dict of CSS styles for the HTML.
            use_item_css_classes: Whether to use item-specific CSS classes.
            **kwargs: Additional arguments passed to generate_dataframe.

        Returns:
            str: HTML string representing the statement with enhanced styling.
        """
        # Enable CSS classes if requested
        if use_item_css_classes:
            kwargs["include_css_classes"] = True

        df = self.generate_dataframe(
            graph=graph,
            should_apply_signs=should_apply_signs,
            include_empty_items=include_empty_items,
            # number_format is applied internally by generate_dataframe
            **kwargs,
        )

        html = df.to_html(index=False, classes="statement-table", table_id="financial-statement")

        if css_styles or use_item_css_classes:
            style_str = "<style>\n"

            # Add default styles for statement tables
            style_str += """
            .statement-table { border-collapse: collapse; width: 100%; }
            .statement-table th, .statement-table td { padding: 8px; text-align: right; border: 1px solid #ddd; }
            .statement-table th { background-color: #f2f2f2; font-weight: bold; }
            .statement-table .Line.Item { text-align: left; }
            .contra-item { font-style: italic; color: #666; }
            """

            # Add custom styles
            if css_styles:
                for selector, style in css_styles.items():
                    style_str += f"{selector} {{ {style} }}\n"

            style_str += "</style>\n"
            html = style_str + html

        return html
