"""Formatter for financial statements.

This module provides functionality for formatting financial statements
for display or reporting, including applying formatting rules, adding subtotals,
and applying sign conventions with enhanced display control.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
import logging
import re
from typing import Any, cast

import numpy as np  # Added numpy for NaN handling
import pandas as pd

# Import adjustment types for filtering
from fin_statement_model.core.adjustments.models import AdjustmentFilterInput

# Add core Graph and errors
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import standard_node_registry

# Import the data fetcher
from fin_statement_model.statements.formatting.data_fetcher import DataFetcher

# Import the ID resolver
from fin_statement_model.statements.population.id_resolver import IDResolver
from fin_statement_model.statements.structure import (
    Section as _LegacySection,
    StatementItem as _LegacyStatementItem,
    StatementStructure as _LegacyStatementStructure,
)
from fin_statement_model.statements.structure.models_v2 import (
    CalculatedLineItem as _V2CalculatedLineItem,
    LineItem as _V2LineItem,  # for StatementItem aliasing
    MetricLineItem as _V2MetricLineItem,
    Section as _V2Section,
    StatementStructure as _V2StatementStructure,
    SubtotalLineItem as _V2SubtotalLineItem,
)

# Import formatting utilities
from fin_statement_model.utils.formatting import render_values

# Configure logging
logger = logging.getLogger(__name__)

# Type aliases for typing only—do NOT override runtime classes used in isinstance
type SectionT = _LegacySection | _V2Section
type StatementItemT = (
    _LegacyStatementItem | _V2LineItem | _V2CalculatedLineItem | _V2MetricLineItem | _V2SubtotalLineItem
)

type StatementStructureLike = _LegacyStatementStructure | _V2StatementStructure

_SECTION_CLASSES = (_LegacySection, _V2Section)
_ITEM_CLASSES = (
    _LegacySection,
    _LegacyStatementItem,
    _V2LineItem,
    _V2CalculatedLineItem,
    _V2MetricLineItem,
    _V2SubtotalLineItem,
)


@dataclass
class FormattingContext:
    """Encapsulates all formatting configuration and state for statement generation.

    This dataclass holds all the configuration options and runtime state needed
    for formatting financial statements, providing a clean interface for passing
    formatting parameters between methods.
    """

    # Core formatting options
    should_apply_signs: bool = True
    include_empty_items: bool = False
    number_format: str | None = None
    include_metadata_cols: bool = False

    # Adjustment options
    adjustment_filter: AdjustmentFilterInput | None = None
    add_is_adjusted_column: bool = False

    # Enhanced display options
    include_units_column: bool = False
    include_css_classes: bool = False
    include_notes_column: bool = False
    apply_item_scaling: bool = True
    apply_item_formatting: bool = True
    respect_hide_flags: bool | None = None

    # Contra item options
    contra_display_style: str | None = None
    apply_contra_formatting: bool = True
    add_contra_indicator_column: bool = False

    # Runtime state (populated during processing)
    all_periods: list[str] = field(default_factory=list)
    items_to_hide: set[str] = field(default_factory=set)
    default_formats: dict[str, Any] = field(default_factory=dict)

    # Derived flags (computed after initialization)
    should_include_enhanced_metadata: bool = field(init=False)

    def __post_init__(self) -> None:
        """Compute derived flags after initialization."""
        self.should_include_enhanced_metadata = any([
            self.include_units_column,
            self.include_css_classes,
            self.include_notes_column,
            self.add_contra_indicator_column,
        ])


class StatementFormatter:
    """Formats financial statements for display or reporting.

    This class provides methods to transform raw financial data into
    formatted financial statements with proper headers, indentation,
    subtotals, sign conventions, and enhanced display control.
    """

    def __init__(self, statement: StatementStructureLike):
        """Initialize a statement formatter.

        Args:
            statement: The statement structure to format
        """
        self.statement = statement

        # --- Build default display formats from global config ---
        from fin_statement_model import get_config  # Local import to avoid circular dep

        cfg_display = get_config().display
        num_format = cfg_display.default_number_format or ",.2f"
        # Detect precision from format string like ',.2f' or '.3f'
        precision_match = re.search(r"\.([0-9]+)f$", num_format)
        precision = int(precision_match.group(1)) if precision_match else 2
        use_thousands_sep = "," in num_format.split(".")[0]

        self.default_formats = {
            "precision": precision,
            "use_thousands_separator": use_thousands_sep,
            "show_zero_values": not cfg_display.hide_zero_rows,
            "show_negative_sign": cfg_display.show_negative_sign,
            "indent_character": cfg_display.indent_character,
            "subtotal_style": cfg_display.subtotal_style,
            "total_style": cfg_display.total_style,
            "header_style": cfg_display.header_style,
            # Contra item display options
            "contra_display_style": cfg_display.contra_display_style,
            "contra_css_class": cfg_display.contra_css_class,
        }

    def _resolve_hierarchical_attribute(
        self,
        item: StatementItemT | SectionT,
        attribute_name: str,
        default_value: Any = None,
        config_path: str | None = None,
        skip_default_check: Callable[[Any], bool] | None = None,
    ) -> Any:
        """Resolve an attribute value using hierarchical lookup.

        Precedence: Item > Parent Section > Statement > Config/Default

        Args:
            item: The item or section to resolve the attribute for
            attribute_name: Name of the attribute to look up
            default_value: Default value if not found anywhere
            config_path: Optional config path to check before using default_value
            skip_default_check: Optional function to determine if a value should be
                              considered "default" and skipped (e.g., scale_factor == 1.0)

        Returns:
            The resolved attribute value
        """
        # Check item-specific attribute
        if hasattr(item, attribute_name):
            item_value = getattr(item, attribute_name)
            if skip_default_check is None or not skip_default_check(item_value):
                return item_value

        # Check if item is part of a section with the attribute
        if isinstance(item, _ITEM_CLASSES):
            parent_section = self._find_parent_section_for_item(item)
            if parent_section and hasattr(parent_section, attribute_name):
                section_value = getattr(parent_section, attribute_name)
                if skip_default_check is None or not skip_default_check(section_value):
                    return section_value

        # Check statement-level attribute
        if hasattr(self.statement, attribute_name):
            statement_value = getattr(self.statement, attribute_name)
            if skip_default_check is None or not skip_default_check(statement_value):
                return statement_value

        # Check config if path provided
        if config_path:
            from fin_statement_model.config.access import cfg

            return cfg(config_path, default_value)

        # Return default value
        return default_value

    def _resolve_display_scale_factor(self, item: StatementItemT | SectionT) -> float:
        """Resolve the display scale factor for an item, considering hierarchy.

        Precedence: Item > Section > Statement > Default (from config)

        Args:
            item: The item or section to get the scale factor for

        Returns:
            The resolved scale factor
        """
        result = self._resolve_hierarchical_attribute(
            item=item,
            attribute_name="display_scale_factor",
            default_value=1.0,
            config_path="display.scale_factor",
            skip_default_check=lambda x: x == 1.0,
        )
        return float(result)

    def _resolve_units(self, item: StatementItemT | SectionT) -> str | None:
        """Resolve the unit description for an item, considering hierarchy.

        Precedence: Item > Section > Statement > None

        Args:
            item: The item or section to get the units for

        Returns:
            The resolved unit description or None
        """
        result = self._resolve_hierarchical_attribute(
            item=item,
            attribute_name="units",
            default_value=None,
            skip_default_check=lambda x: not x,  # Skip empty strings/None
        )
        return result if result is not None else None

    def _find_parent_section_for_item(self, target_item: StatementItemT | SectionT) -> object | None:
        """Find the parent section that contains the given item.

        Args:
            target_item: The item to find the parent section for.

        Returns:
            The parent Section object, or None if not found.
        """

        def _is_section(obj: Any) -> bool:
            return isinstance(obj, _SECTION_CLASSES) or getattr(obj, "item_type", None) == "section"

        def search_in_section(section: Any) -> Any | None:
            # Check direct items
            for item in section.items:
                if item is target_item or (
                    hasattr(item, "id") and hasattr(target_item, "id") and item.id == target_item.id
                ):
                    return section
                # Check nested sections
                if _is_section(item):
                    result = search_in_section(item)
                    if result:
                        return result

            # Check subtotal
            if getattr(section, "subtotal", None) is target_item:
                return section

            return None

        # Search through all top-level sections
        for sec in self.statement.sections:
            result = search_in_section(sec)
            if result is not None:
                return cast("SectionT | object", result)

        return None

    def _should_hide_item(self, item: StatementItemT | SectionT, values: dict[str, float]) -> bool:
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

    def _apply_item_scaling(self, values: dict[str, float], scale_factor: float) -> dict[str, float]:
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
        item: StatementItemT | SectionT,
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
                            "Invalid display format '%s' for item '%s', using default",
                            item_format,
                            getattr(item, "id", "unknown"),
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

        # For contra items, we typically want to show the absolute value with special formatting
        # regardless of the underlying sign, since sign_convention handles calculation logic
        from fin_statement_model.config.access import cfg

        style = display_style or self.default_formats.get(
            "contra_display_style", cfg("display.contra_display_style", "parentheses")
        )
        abs_value = abs(value)

        # Use dictionary for style formatting
        style_formats = {
            "parentheses": f"({abs_value:,.2f})",
            "negative_sign": f"-{abs_value:,.2f}",
            "brackets": f"[{abs_value:,.2f}]",
        }

        if style and isinstance(style, str) and style in style_formats:
            return style_formats[style]
        return f"({abs_value:,.2f})"  # Default fallback

    def _apply_contra_formatting(
        self,
        item: StatementItemT | SectionT,
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
        _ = item  # Parameter intentionally unused in current implementation
        contra_formatted = {}
        for period in period_columns:
            value = values.get(period, np.nan)
            contra_formatted[period] = self._format_contra_value(value, display_style)

        return contra_formatted

    def _prepare_formatting_context(self, **kwargs: Any) -> FormattingContext:
        """Prepare formatting context with config defaults.

        Args:
            **kwargs: All formatting parameters passed to generate_dataframe (overrides config)

        Returns:
            FormattingContext: Configured context object
        """
        from fin_statement_model import get_config

        config = get_config()

        # Create context with provided kwargs
        context = FormattingContext(
            should_apply_signs=kwargs.get("should_apply_signs", config.display.apply_sign_conventions),
            include_empty_items=kwargs.get("include_empty_items", config.display.include_empty_items),
            number_format=kwargs.get("number_format"),
            include_metadata_cols=kwargs.get("include_metadata_cols", config.display.include_metadata_cols),
            adjustment_filter=kwargs.get("adjustment_filter"),
            add_is_adjusted_column=kwargs.get("add_is_adjusted_column", config.display.add_is_adjusted_column),
            include_units_column=kwargs.get("include_units_column", config.display.include_units_column),
            include_css_classes=kwargs.get("include_css_classes", config.display.include_css_classes),
            include_notes_column=kwargs.get("include_notes_column", config.display.include_notes_column),
            apply_item_scaling=kwargs.get("apply_item_scaling", config.display.apply_item_scaling),
            apply_item_formatting=kwargs.get("apply_item_formatting", config.display.apply_item_formatting),
            respect_hide_flags=kwargs.get("respect_hide_flags"),
            contra_display_style=kwargs.get("contra_display_style"),
            apply_contra_formatting=kwargs.get("apply_contra_formatting", config.display.apply_contra_formatting),
            add_contra_indicator_column=kwargs.get(
                "add_contra_indicator_column",
                config.display.add_contra_indicator_column,
            ),
        )

        # Apply config defaults for None values
        if context.should_apply_signs is None:
            context.should_apply_signs = True  # This is a calculation default, not display
        if context.include_empty_items is None:
            context.include_empty_items = False  # Preserve historical default
        if context.respect_hide_flags is None:
            context.respect_hide_flags = config.display.hide_zero_rows
        if context.contra_display_style is None:
            context.contra_display_style = config.display.contra_display_style
        if context.number_format is None:
            context.number_format = config.display.default_number_format

        # Set default formats
        context.default_formats = self.default_formats

        return context

    def _fetch_statement_data(
        self, graph: Graph, context: FormattingContext
    ) -> tuple[dict[str, dict[str, float]], Any]:
        """Fetch data from graph using DataFetcher.

        Args:
            graph: The core.graph.Graph instance containing the data
            context: Formatting context with fetch parameters

        Returns:
            Tuple of (data dictionary, fetch errors)
        """
        data_fetcher = DataFetcher(self.statement, graph)
        fetch_result = data_fetcher.fetch_all_data(
            adjustment_filter=context.adjustment_filter,
            include_missing=context.include_empty_items,
        )

        # Log any warnings/errors
        if fetch_result.errors.has_warnings() or fetch_result.errors.has_errors():
            fetch_result.errors.log_all(prefix=f"Statement '{self.statement.id}' data fetch: ")

        # Update context with periods from graph
        context.all_periods = graph.periods

        return fetch_result.data, fetch_result.errors

    def _create_empty_dataframe(self, context: FormattingContext) -> pd.DataFrame:
        """Create an empty DataFrame with appropriate columns.

        Args:
            context: Formatting context with column configuration

        Returns:
            Empty DataFrame with proper column structure
        """
        base_cols = ["Line Item", "ID", *context.all_periods]
        if context.include_units_column:
            base_cols.append("units")
        return pd.DataFrame(columns=base_cols)

    def _build_row_data(
        self,
        graph: Graph,
        data: dict[str, dict[str, float]],
        context: FormattingContext,
    ) -> list[dict[str, Any]]:
        """Build row data recursively from statement structure.

        Args:
            graph: The core.graph.Graph instance
            data: Fetched data dictionary
            context: Formatting context

        Returns:
            List of row dictionaries
        """
        rows: list[dict[str, Any]] = []
        id_resolver = IDResolver(self.statement, standard_node_registry)

        # Process all sections
        self._process_items_recursive(
            items=list(self.statement.sections),
            depth=0,
            data=data,
            rows=rows,
            context=context,
            id_resolver=id_resolver,
            graph=graph,
        )

        # Filter hidden items if needed
        if context.respect_hide_flags:
            rows = [row for row in rows if row["ID"] not in context.items_to_hide]

        return rows

    def _process_items_recursive(
        self,
        items: list[SectionT | StatementItemT],
        depth: int,
        data: dict[str, dict[str, float]],
        rows: list[dict[str, Any]],
        context: FormattingContext,
        id_resolver: IDResolver,
        graph: Graph,
    ) -> None:
        """Recursively process items and sections.

        Args:
            items: List of items or sections to process
            depth: Current indentation depth
            data: Fetched data dictionary
            rows: List to append row data to
            context: Formatting context
            id_resolver: ID resolver instance
            graph: Graph instance
        """
        for item in items:
            if isinstance(item, _SECTION_CLASSES) or getattr(item, "item_type", None) == "section":
                self._process_section(item, depth, data, rows, context, id_resolver, graph)
            elif getattr(item, "item_type", None) != "section":
                self._process_item(item, depth, data, rows, context, id_resolver, graph)

    def _process_section(
        self,
        section: Any,
        depth: int,
        data: dict[str, dict[str, float]],
        rows: list[dict[str, Any]],
        context: FormattingContext,
        id_resolver: IDResolver,
        graph: Graph,
    ) -> None:
        """Process a section (or section-like object) and its items.

        Args:
            section: Section to process
            depth: Current indentation depth
            data: Fetched data dictionary
            rows: List to append row data to
            context: Formatting context
            id_resolver: ID resolver instance
            graph: Graph instance
        """
        # Process nested items first to collect data for hide check
        self._process_items_recursive(section.items, depth + 1, data, rows, context, id_resolver, graph)

        # Process subtotal if it exists
        if getattr(section, "subtotal", None):
            self._process_items_recursive([section.subtotal], depth + 1, data, rows, context, id_resolver, graph)

        # Check if section should be hidden
        if context.respect_hide_flags and getattr(section, "hide_if_all_zero", False):
            # For sections, check if all contained items are hidden or zero
            section_has_data = False
            for section_item in section.items:
                node_id = id_resolver.resolve(section_item.id, graph)
                if node_id and node_id in data:
                    item_data = data[node_id]
                    if any(pd.notna(v) and v != 0 for v in item_data.values()):
                        section_has_data = True
                        break
            if not section_has_data:
                context.items_to_hide.add(section.id)

    def _process_item(
        self,
        item: StatementItemT,
        depth: int,
        data: dict[str, dict[str, float]],
        rows: list[dict[str, Any]],
        context: FormattingContext,
        id_resolver: IDResolver,
        graph: Graph,
    ) -> None:
        """Process a single statement item.

        Args:
            item: Statement item to process
            depth: Current indentation depth
            data: Fetched data dictionary
            rows: List to append row data to
            context: Formatting context
            id_resolver: ID resolver instance
            graph: Graph instance
        """
        # Use ID resolver to get the correct node ID
        node_id = id_resolver.resolve(item.id, graph)
        if not node_id:
            return

        item_data = data.get(node_id, {})
        numeric_values: dict[str, float] = {p: item_data.get(p, np.nan) for p in context.all_periods}

        # Apply item-specific scaling if enabled
        if context.apply_item_scaling:
            numeric_values = self._apply_scaling(numeric_values, context, item)

        # Check if item should be hidden
        if context.respect_hide_flags and self._should_hide_item(item, numeric_values):
            context.items_to_hide.add(item.id)
            return

        # Start with numeric values and add formatted strings as needed
        row_values: dict[str, float | str] = dict(numeric_values)

        # Apply item-specific formatting if enabled (but only if not using global format)
        if context.apply_item_formatting and not context.number_format:
            formatted_values = self._format_item_values(item, numeric_values, context.all_periods)
            # Only apply if we got actual formatted strings
            if any(isinstance(v, str) for v in formatted_values.values()):
                for period in context.all_periods:
                    if period in formatted_values and isinstance(formatted_values[period], str):
                        # Keep numeric value for calculations, store formatted for display
                        row_values[f"{period}_formatted"] = formatted_values[period]

        # Apply contra formatting if enabled and item is marked as contra
        if context.apply_contra_formatting and getattr(item, "is_contra", False):
            contra_formatted = self._apply_contra_formatting(
                item, numeric_values, context.all_periods, context.contra_display_style
            )
            # Store contra formatted values for later use
            for period in context.all_periods:
                if contra_formatted.get(period):
                    row_values[f"{period}_contra"] = contra_formatted[period]

        if context.include_empty_items or any(pd.notna(v) for v in row_values.values()):
            row = self._create_row_dict(item, node_id, row_values, depth, context)
            rows.append(row)

    def _create_row_dict(
        self,
        item: StatementItemT,
        node_id: str,
        row_values: dict[str, float | str],
        depth: int,
        context: FormattingContext,
    ) -> dict[str, Any]:
        """Create a row dictionary for a statement item.

        Args:
            item: Statement item
            node_id: Resolved node ID
            row_values: Period values for the item
            depth: Indentation depth
            context: Formatting context

        Returns:
            Row dictionary
        """
        indent_char = context.default_formats["indent_character"]

        row = {
            "Line Item": indent_char * depth + item.name,
            "ID": item.id,
            **row_values,
            # Metadata
            "line_type": self._get_item_type(item),
            "node_id": node_id,
            "sign_convention": getattr(item, "sign_convention", 1),
            "is_subtotal": getattr(item, "item_type", None) == "subtotal",
            "is_calculated": getattr(item, "item_type", None) == "calculated",
            "is_contra": getattr(item, "is_contra", False),
        }

        # Add enhanced metadata columns if requested
        if context.include_units_column:
            row["units"] = self._resolve_units(item)

        if context.include_css_classes:
            # Get item's CSS class and add contra class if applicable
            item_css_class = getattr(item, "css_class", None)
            if getattr(item, "is_contra", False):
                contra_css = context.default_formats.get("contra_css_class", "contra-item")
                if item_css_class:
                    row["css_class"] = f"{item_css_class} {contra_css}"
                else:
                    row["css_class"] = contra_css
            else:
                row["css_class"] = item_css_class

        if context.include_notes_column:
            notes = getattr(item, "notes_references", [])
            row["notes"] = "; ".join(notes) if notes else ""

        return row

    def _apply_scaling(
        self, values: dict[str, float], context: FormattingContext, item: StatementItemT
    ) -> dict[str, float]:
        """Apply item-specific scaling if enabled.

        Args:
            values: Dictionary of period values
            context: Formatting context
            item: Statement item

        Returns:
            Dictionary of scaled values
        """
        if not context.apply_item_scaling:
            return values

        scale_factor = self._resolve_display_scale_factor(item)
        return self._apply_item_scaling(values, scale_factor)

    def _organize_dataframe_columns(self, df: pd.DataFrame, context: FormattingContext) -> pd.DataFrame:
        """Organize DataFrame columns in the correct order.

        Args:
            df: DataFrame to organize
            context: Formatting context

        Returns:
            DataFrame with organized columns
        """
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
        if context.include_units_column:
            enhanced_cols.append("units")
        if context.include_css_classes:
            enhanced_cols.append("css_class")
        if context.include_notes_column:
            enhanced_cols.append("notes")
        if context.add_contra_indicator_column:
            enhanced_cols.append("is_contra")

        # Add adjustment columns if they exist
        adjusted_flag_cols = []
        if context.add_is_adjusted_column:
            adjusted_flag_cols = [f"{period}_is_adjusted" for period in context.all_periods]

        final_cols = base_cols + context.all_periods
        if adjusted_flag_cols:
            final_cols += adjusted_flag_cols
        if enhanced_cols:
            final_cols += enhanced_cols
        if context.include_metadata_cols:
            # Add metadata cols (excluding adjustment flags if they are already added)
            final_cols += [m_col for m_col in metadata_cols if m_col not in adjusted_flag_cols]

        # Ensure contra formatting columns are available temporarily (will be removed later)
        all_available_cols = final_cols.copy()
        if context.apply_contra_formatting:
            contra_formatted_cols = [f"{period}_contra" for period in context.all_periods]
            all_available_cols += contra_formatted_cols

        for col in all_available_cols:
            if col not in df.columns:
                df[col] = np.nan if col in context.all_periods else ("" if col == "Line Item" else None)

        return df[all_available_cols]

    def _add_adjustment_columns(self, df: pd.DataFrame, graph: Graph, context: FormattingContext) -> pd.DataFrame:
        """Add adjustment status columns to the DataFrame.

        Args:
            df: DataFrame to add columns to
            graph: Graph instance
            context: Formatting context

        Returns:
            DataFrame with adjustment columns added
        """
        if not context.add_is_adjusted_column or not context.all_periods:
            return df

        # Get node IDs from the dataframe
        node_ids_to_check = []
        for _, row in df.iterrows():
            node_id = row.get("node_id")
            is_calc_or_subtotal = row.get("is_calculated", False) or row.get("is_subtotal", False)
            if node_id and not is_calc_or_subtotal:
                node_ids_to_check.append(node_id)

        # Use DataFetcher to check adjustments
        if node_ids_to_check:
            data_fetcher = DataFetcher(self.statement, graph)
            adjustment_status = data_fetcher.check_adjustments(
                node_ids_to_check, context.all_periods, context.adjustment_filter
            )
        else:
            adjustment_status = {}

        # Build adjustment columns
        is_adjusted_data = []
        for _, row in df.iterrows():
            node_id = row.get("node_id")
            is_calc_or_subtotal = row.get("is_calculated", False) or row.get("is_subtotal", False)

            if node_id and not is_calc_or_subtotal and node_id in adjustment_status:
                row_adj_flags = {
                    f"{period}_is_adjusted": adjustment_status[node_id].get(period, False)
                    for period in context.all_periods
                }
            else:
                # For calculated/subtotal items or missing nodes, flags are False
                row_adj_flags = {f"{period}_is_adjusted": False for period in context.all_periods}
            is_adjusted_data.append(row_adj_flags)

        if is_adjusted_data:
            adj_df = pd.DataFrame(is_adjusted_data, index=df.index)
            df = pd.concat([df, adj_df], axis=1)

        return df

    def _cleanup_temporary_columns(self, df: pd.DataFrame, context: FormattingContext) -> pd.DataFrame:
        """Clean up temporary columns from the dataframe.

        Args:
            df: DataFrame to clean up
            context: Formatting context

        Returns:
            DataFrame with temporary columns removed
        """
        # Remove the contra formatting columns from the final output
        if context.apply_contra_formatting:
            contra_cols_to_remove = [f"{period}_contra" for period in context.all_periods]
            df = df.drop(columns=[col for col in contra_cols_to_remove if col in df.columns])

        # Build final column list
        base_cols = ["Line Item", "ID"]
        metadata_cols = [
            "line_type",
            "node_id",
            "sign_convention",
            "is_subtotal",
            "is_calculated",
            "is_contra",
        ]

        enhanced_cols = []
        if context.include_units_column:
            enhanced_cols.append("units")
        if context.include_css_classes:
            enhanced_cols.append("css_class")
        if context.include_notes_column:
            enhanced_cols.append("notes")
        if context.add_contra_indicator_column:
            enhanced_cols.append("is_contra")

        adjusted_flag_cols = []
        if context.add_is_adjusted_column:
            adjusted_flag_cols = [f"{period}_is_adjusted" for period in context.all_periods]

        final_cols = base_cols + context.all_periods
        if context.add_is_adjusted_column:
            final_cols += adjusted_flag_cols
        if enhanced_cols:
            final_cols += enhanced_cols
        if context.include_metadata_cols:
            # Add metadata cols (excluding adjustment flags if they are already added)
            final_cols += [m_col for m_col in metadata_cols if m_col not in adjusted_flag_cols]

        # Select only the final columns for output
        return df[final_cols]

    def _apply_all_formatting(self, df: pd.DataFrame, context: FormattingContext) -> pd.DataFrame:
        """Apply consolidated formatting in a single vectorized pass."""
        # Combined sign, contra, and number formatting
        df = render_values(
            df=df,
            period_columns=context.all_periods,
            default_formats=context.default_formats,
            number_format=context.number_format,
            contra_display_style=context.contra_display_style,
        )
        # Clean up temporary columns
        df = self._cleanup_temporary_columns(df, context)
        return df

    def generate_dataframe(
        self,
        graph: Graph,
        context: FormattingContext | None = None,
    ) -> pd.DataFrame:
        """Generate a formatted DataFrame for the statement.

        Args:
            graph: Graph instance containing the data to render.
            context: FormattingContext object containing all display / formatting
                configuration. If *None*, a context will be created from project
                configuration.

        Returns:
            A fully-formatted ``pandas.DataFrame`` representing the statement.
        """
        if context is None:
            # Build context purely from project defaults (no legacy kwargs path).
            context = self._prepare_formatting_context()

        # 2. Fetch statement data -------------------------------------------------------------------
        data, _ = self._fetch_statement_data(graph, context)

        # 3. Build row dictionaries -----------------------------------------------------------------
        rows = self._build_row_data(graph, data, context)

        # 4. Assemble DataFrame ---------------------------------------------------------------------
        if not rows:
            return self._create_empty_dataframe(context)

        df = pd.DataFrame(rows)

        # 5. Adjustment columns (must precede column organisation)
        if context.add_is_adjusted_column:
            df = self._add_adjustment_columns(df, graph, context)

        # 6. Column ordering / injection ------------------------------------------------------------
        df = self._organize_dataframe_columns(df, context)

        # 7. Post-processing formatting -------------------------------------------------------------
        df = self._apply_all_formatting(df, context)

        return df

    def _get_item_type(self, item: StatementItemT) -> str:
        """Get the type of a statement item.

        Args:
            item: Statement item to get type for

        Returns:
            str: Item type identifier
        """
        # Legacy *Section* objects are not derived from StatementItem and need
        # an explicit check.
        if isinstance(item, _SECTION_CLASSES) or getattr(item, "item_type", None) == "section":
            return "section"

        itype = getattr(item, "item_type", None)

        from enum import Enum

        # Handle Enum values from the legacy model safely.
        if isinstance(itype, Enum):
            return str(itype.value)

        return str(itype) if itype is not None else "item"

    def format_html(
        self,
        graph: Graph,
        should_apply_signs: bool | None = None,
        include_empty_items: bool | None = None,
        css_styles: dict[str, str] | None = None,
        use_item_css_classes: bool | None = None,
        **kwargs: Any,
    ) -> str:
        """Format the statement data as HTML with enhanced styling support.

        Args:
            graph: The core.graph.Graph instance containing the data.
            should_apply_signs: Whether to apply sign conventions (override config).
            include_empty_items: Whether to include items with no data (override config).
            css_styles: Optional dict of CSS styles for the HTML.
            use_item_css_classes: Whether to use item-specific CSS classes (override config).
            **kwargs: Additional arguments passed to generate_dataframe.

        Returns:
            str: HTML string representing the statement with enhanced styling.
        """
        # Determine defaults for unspecified parameters -------------------------------------------
        from fin_statement_model import get_config

        cfg = get_config()

        should_apply_signs = (
            should_apply_signs if should_apply_signs is not None else cfg.display.apply_sign_conventions
        )
        include_empty_items = (
            include_empty_items if include_empty_items is not None else cfg.display.include_empty_items
        )
        use_item_css_classes = (
            use_item_css_classes if use_item_css_classes is not None else cfg.display.include_css_classes
        )

        # Ensure the correct flag for CSS class inclusion is propagated
        if use_item_css_classes:
            kwargs["include_css_classes"] = True

        # Build a FormattingContext with the specified overrides and any additional
        # keyword arguments provided by the caller.
        context = self._prepare_formatting_context(
            should_apply_signs=should_apply_signs,
            include_empty_items=include_empty_items,
            **kwargs,
        )

        df = self.generate_dataframe(graph=graph, context=context)

        html: str = df.to_html(index=False, classes="statement-table", table_id="financial-statement")

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
