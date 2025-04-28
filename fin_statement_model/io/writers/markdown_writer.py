"""Writes a financial statement graph to a Markdown table."""

import logging
import yaml  # Added for parsing statement config
from typing import Any, Optional, TypedDict, Union
from collections.abc import Iterable

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.adjustments.models import (
    Adjustment,
    AdjustmentFilter,
    DEFAULT_SCENARIO,
)
from fin_statement_model.io.base import DataWriter
from fin_statement_model.io.config.models import BaseWriterConfig
from fin_statement_model.io.exceptions import WriteError
from fin_statement_model.io.registry import register_writer

logger = logging.getLogger(__name__)


class MarkdownWriterConfig(BaseWriterConfig):
    """Configuration specific to the Markdown writer."""

    indent_spaces: int = 4  # Number of spaces per indentation level
    # Add other Markdown-specific config options here if needed


# Define a structure for the items to be written
class StatementItem(TypedDict):
    """Represents a line item with its values for Markdown output."""

    name: str
    # value: Union[float, int, str, None] # Replaced single value
    values: dict[str, Union[float, int, str, None]]  # Values per period
    level: int
    is_subtotal: bool  # Indicates if the row is a subtotal or section header


@register_writer("markdown")
class MarkdownWriter(DataWriter):
    """Writes a financial statement structure to a Markdown table."""

    def __init__(self, config: Optional[MarkdownWriterConfig] = None):
        """Initializes the MarkdownWriter."""
        self.config = config or MarkdownWriterConfig(format_type="markdown")
        logger.debug(f"Initialized MarkdownWriter with config: {self.config}")

    def _format_value(self, value: Union[float, int, str, None]) -> str:
        """Formats the value for display in the table."""
        if value is None:
            return ""
        if isinstance(value, float | int):
            # Basic number formatting, could be enhanced (e.g., commas)
            return f"{value:,.2f}" if isinstance(value, float) else str(value)
        return str(value)

    def _get_statement_items(
        self, graph: Graph, statement_config_path: str
    ) -> Iterable[StatementItem]:
        """Dynamically extracts and orders statement items based on YAML config and graph data.

        Args:
            graph: The financial statement graph containing node values.
            statement_config_path: Path to the statement definition YAML file.

        Returns:
            An iterable of StatementItem dictionaries.

        Raises:
            WriteError: If the config file is not found, invalid, or nodes are missing.
        """
        try:
            with open(statement_config_path) as f:
                config_data = yaml.safe_load(f)
            if not config_data or not isinstance(config_data, dict):
                raise WriteError(f"Invalid or empty YAML structure in {statement_config_path}")

        except FileNotFoundError:
            logger.exception(f"Statement configuration file not found: {statement_config_path}")
            raise WriteError(
                f"Statement configuration file not found: {statement_config_path}"
            ) from None
        except yaml.YAMLError as e:
            logger.exception(
                f"Error parsing statement configuration YAML '{statement_config_path}'"
            )
            raise WriteError(f"Error parsing statement configuration YAML: {e}") from e

        periods = sorted(list(graph.periods))
        logger.debug(
            f"Extracting statement items for periods: {periods} using config: {statement_config_path}"
        )

        # Define the recursive processing function within the scope
        def process_level(items_or_sections: list, level: int):
            for config_item in items_or_sections:
                # Check if this dictionary represents a section container
                # by seeing if it has an 'items' list.
                inner_items = config_item.get("items")
                if isinstance(inner_items, list):
                    # It's a section-like structure. Process its inner items.
                    # Optionally, yield a header for the section here if needed
                    # section_name = config_item.get("name", "Unnamed Section")
                    # yield StatementItem(name=f"**{section_name}**", values={p: "" for p in periods}, level=level, is_subtotal=True) # Treat as subtotal for bolding?

                    yield from process_level(inner_items, level + 1) # Process items within the section

                    # Also process any nested subsections
                    subsections = config_item.get("subsections")
                    if isinstance(subsections, list):
                         yield from process_level(subsections, level + 1)

                    # Process subtotal for this section if it exists
                    section_subtotal_config = config_item.get("subtotal")
                    if section_subtotal_config:
                         # Ensure subtotal has correct type and id before processing
                         if section_subtotal_config.get("id") and section_subtotal_config.get("type"):
                             subtotal_item = process_item(
                                 section_subtotal_config, level + 1 # Indent subtotal
                             )
                             if subtotal_item:
                                 yield subtotal_item
                         else:
                             logger.warning(f"Skipping section subtotal due to missing 'id' or 'type': {section_subtotal_config}")

                else:
                    # This is likely a direct item (line_item, metric, etc.)
                    # Check for required fields before processing
                    item_id = config_item.get("id")
                    item_type = config_item.get("type")
                    if not item_id or not item_type:
                         logger.warning(
                            f"Skipping item due to missing 'id' or 'type' in config: {config_item}"
                         )
                         continue # Skip this malformed item

                    # Process the item using the existing function
                    item_data = process_item(config_item, level)
                    if item_data:
                        yield item_data

        # Define the process_item function (handles non-section items)
        def process_item(item_config: dict, level: int) -> Union[StatementItem, None]:
            item_id = item_config.get("id")
            item_name = item_config.get("name", "Unknown Item")
            item_type = item_config.get("type")
            sign_convention = item_config.get("sign_convention", 1)

            # No need for the redundant check here as it's done in process_level now
            # if not item_id or not item_type:
            #     logger.warning(
            #         f"Skipping item due to missing 'id' or 'type' in config: {item_config}"
            #     )
            #     return None

            values = {}
            is_subtotal = item_type == "subtotal"
            node_id = None

            if item_type == "line_item":
                node_id = item_config.get("node_id")
                if not node_id:
                    logger.warning(
                        f"Skipping line_item '{item_name}' (ID: {item_id}) - missing 'node_id' in config."
                    )
                    return None
            elif item_type in ["calculated", "subtotal", "metric"]:
                node_id = item_id
            else:
                logger.warning(
                    f"Unsupported item type '{item_type}' for item '{item_name}'. Skipping."
                )
                return None

            # Check if node_id could be determined (might be None if type wasn't handled)
            if node_id is None:
                logger.warning(
                    f"Could not determine node ID for item '{item_name}' (Type: {item_type}). Skipping value fetch."
                )
                for period in periods:
                    values[period] = None
                # Still return the item structure but with None values
                return StatementItem(
                    name=item_name, values=values, level=level, is_subtotal=is_subtotal
                )

            # Fetch values from the graph node
            try:
                node = graph.get_node(node_id)
                for period in periods:
                    raw_value = None
                    if item_type == "line_item":
                        # For line items, get the stored value directly
                        raw_value = node.get_value(period)
                    elif item_type in ["calculated", "subtotal", "metric"]:
                        # For calculated/subtotal/metric items, use the graph's calculation engine
                        try:
                            raw_value = graph.calculate(node_id, period)
                        except Exception:  # Catch potential calculation errors
                            logger.exception(
                                f"Calculation failed for node '{node_id}' period '{period}'"
                            )
                            raw_value = "CALC_ERR"
                    else:
                        # Should not happen based on earlier check, but as a safeguard
                        logger.warning(
                            f"Unexpected item type '{item_type}' during value fetch for '{item_name}'."
                        )
                        raw_value = None

                    # Apply sign convention
                    # Handle potential string values from errors
                    if isinstance(raw_value, int | float):
                        values[period] = raw_value * sign_convention
                    elif raw_value is None:
                        values[period] = None
                    else:  # Keep error strings as is
                        values[period] = raw_value

            except KeyError:
                logger.warning(
                    f"Node '{node_id}' for item '{item_name}' (Type: {item_type}) not found in graph. Values will be missing."
                )
                for period in periods:
                    values[period] = None  # Fill with None if node is missing
            except Exception as e:
                logger.error(
                    f"Error fetching value for node '{node_id}' (Item: '{item_name}'): {e}",
                    exc_info=True,
                )
                for period in periods:
                    values[period] = "ERROR"  # Indicate error in output

            return StatementItem(
                name=item_name, values=values, level=level, is_subtotal=is_subtotal
            )

        # Start processing from the top-level sections
        yield from process_level(config_data.get("sections", []), level=0)

    def write(self, graph: Graph, target: Any = None, **kwargs: Any) -> str:
        """Writes the financial statement graph to a Markdown table string.

        Args:
            graph: The Graph object containing the financial data.
            target: Ignored by this writer, as it returns a string.
            **kwargs: Additional options. Expected args:
                statement_config_path (str): Path to the statement definition YAML.
                historical_periods (list[str], optional): List of historical period names.
                forecast_periods (list[str], optional): List of forecast period names.
                forecast_configs (dict, optional): Maps node IDs to forecast methods/configs for notes.

        Returns:
            A string containing the formatted statement in Markdown.

        Raises:
            WriteError: If statement_config_path is missing/invalid or an error occurs during writing.
        """
        logger.info(
            f"Writing graph to Markdown format (target ignored: {target}) using kwargs: {kwargs.keys()}"
        )

        statement_config_path = kwargs.get("statement_config_path")
        if not statement_config_path or not isinstance(statement_config_path, str):
            raise WriteError(
                "Missing or invalid 'statement_config_path' keyword argument for MarkdownWriter."
            )

        try:
            items = list(self._get_statement_items(graph, statement_config_path))
            if not items:
                logger.warning("No statement items generated from config and graph.")
                return ""  # Return empty string

            # --- Get periods and determine historical/forecast ---
            # Get periods from graph, ensuring order
            periods = sorted(list(graph.periods))
            # Default historical/forecast periods if not provided - attempt to infer or use all
            all_periods = set(periods)
            historical_periods = set(
                kwargs.get("historical_periods", [])
            )  # Get from kwargs if provided
            forecast_periods = set(
                kwargs.get("forecast_periods", [])
            )  # Get from kwargs if provided

            # Simple inference if not provided fully
            if not historical_periods and not forecast_periods:
                # Assume all periods are historical if no forecast info given (basic fallback)
                logger.warning(
                    "No historical/forecast period info provided; assuming all periods are historical for formatting."
                )
                historical_periods = all_periods
            elif not historical_periods:
                historical_periods = all_periods - forecast_periods
            elif not forecast_periods:
                forecast_periods = all_periods - historical_periods

            # --- Calculate dynamic padding ---
            max_desc_width = 0
            period_max_value_widths: dict[str, int] = {p: 0 for p in periods}
            formatted_lines = []

            # First pass: format data and calculate max widths
            for item in items:
                indent = " " * (item["level"] * self.config.indent_spaces)
                name = f"{indent}{item['name']}"
                is_subtotal = item["is_subtotal"]
                values_formatted: dict[str, str] = {}

                if is_subtotal:
                    name = f"**{name}**"

                max_desc_width = max(max_desc_width, len(name))

                for period in periods:
                    raw_value = item["values"].get(period)
                    value_str = self._format_value(raw_value)
                    if is_subtotal:
                        value_str = f"**{value_str}**"
                    values_formatted[period] = value_str
                    period_max_value_widths[period] = max(
                        period_max_value_widths[period], len(value_str)
                    )

                formatted_lines.append(
                    {"name": name, "values": values_formatted, "is_subtotal": is_subtotal}
                )

            # Add some spacing between columns

            # --- Build the final string ---
            output_lines = []

            # Build header row
            header_parts = ["Description".ljust(max_desc_width)]
            for period in periods:
                period_label = period
                if period in historical_periods:
                    period_label += " (H)"
                elif period in forecast_periods:
                    period_label += " (F)"
                header_parts.append(period_label.rjust(period_max_value_widths[period]))
            # Join with | and add start/end |
            output_lines.append(f"| {(' | ').join(header_parts)} |")

            # Add separator line
            separator_parts = ["-" * max_desc_width]
            separator_parts.extend("-" * period_max_value_widths[period] for period in periods)
            output_lines.append(f"| {(' | ').join(separator_parts)} |")

            # Build data rows
            for line_data in formatted_lines:
                row_parts = [line_data["name"].ljust(max_desc_width)]
                for period in periods:
                    value = line_data["values"].get(period, "")  # Get value or empty string
                    row_parts.append(value.rjust(period_max_value_widths[period]))
                # Join with | and add start/end |
                output_lines.append(f"| {(' | ').join(row_parts)} |")

            # --- Add Forecast Notes ---
            forecast_configs = kwargs.get("forecast_configs")
            if forecast_configs:
                notes = ["", "## Forecast Notes"]  # Add blank line before header
                for node_id, config in forecast_configs.items():
                    method = config.get("method", "N/A")
                    cfg_details = config.get("config")
                    desc = f"- **{node_id}**: Forecasted using method '{method}'"
                    if method == "simple" and cfg_details is not None:
                        desc += f" (e.g., fixed growth rate: {cfg_details:.1%})."
                    elif method == "curve" and cfg_details:
                        rates_str = ", ".join([f"{r:.1%}" for r in cfg_details])
                        desc += f" (e.g., specific growth rates: [{rates_str}])."
                    elif method == "historical_growth":
                        desc += " (based on average historical growth)."
                    elif method == "average":
                        desc += " (based on historical average value)."
                    elif method == "statistical":
                        dist_name = cfg_details.get("distribution", "unknown")
                        params_dict = cfg_details.get("params", {})
                        params_str = ", ".join(
                            [
                                f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}"
                                for k, v in params_dict.items()
                            ]
                        )
                        desc += f" (using '{dist_name}' distribution with params: {params_str})."
                    else:
                        desc += "."
                    notes.append(desc)
                # Append notes if any were generated
                if len(notes) > 2:  # Header + at least one note
                    output_lines.extend(notes)

            # --- Add Adjustment Notes --- #
            adj_filter_input = kwargs.get("adjustment_filter")
            all_adjustments: list[Adjustment] = graph.list_all_adjustments()
            filtered_adjustments: list[Adjustment] = []

            if all_adjustments:
                # Create a filter instance based on the input
                filt: AdjustmentFilter
                if isinstance(adj_filter_input, AdjustmentFilter):
                    filt = adj_filter_input.model_copy(update={"period": None}) # Ignore period context
                elif isinstance(adj_filter_input, set):
                    filt = AdjustmentFilter(
                        include_tags=adj_filter_input,
                        include_scenarios={DEFAULT_SCENARIO}, # Assume default scenario for tag shorthand
                        period=None
                    )
                else: # Includes None or other types
                    filt = AdjustmentFilter(include_scenarios={DEFAULT_SCENARIO}, period=None)

                # Apply the filter
                filtered_adjustments = [adj for adj in all_adjustments if filt.matches(adj)]

            if filtered_adjustments:
                output_lines.append("") # Blank line
                output_lines.append("## Adjustment Notes (Matching Filter)")
                for adj in sorted(filtered_adjustments, key=lambda x: (x.node_name, x.period, x.priority, x.timestamp)):
                    tags_str = ", ".join(sorted(adj.tags)) if adj.tags else "None"
                    details = (
                        f"- **{adj.node_name}** ({adj.period}, Scenario: {adj.scenario}, Prio: {adj.priority}): "
                        f"{adj.type.name.capitalize()} adjustment of {adj.value:.2f}. "
                        f"Reason: {adj.reason}. Tags: [{tags_str}]. (ID: {adj.id})"
                    )
                    output_lines.append(details)
            # --- End Adjustment Notes --- #

            return "\n".join(output_lines)

        except NotImplementedError as nie:
            logger.exception("Markdown write failed")
            raise WriteError(
                message=f"Markdown writer requires graph traversal logic: {nie}",
                target=target,
                writer_type="markdown",
                original_error=nie,
            ) from nie
        except Exception as e:
            logger.exception("Error writing Markdown for graph", exc_info=True)
            raise WriteError(
                message=f"Failed to generate Markdown table: {e}",
                target=target,
                writer_type="markdown",
                original_error=e,
            ) from e
