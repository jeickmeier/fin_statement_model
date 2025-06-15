"""Builder for markdown notes sections (forecast and adjustment notes)."""

import logging
from typing import Any, Optional

from fin_statement_model.core.adjustments.models import (
    DEFAULT_SCENARIO,
    Adjustment,
    AdjustmentFilter,
)
from fin_statement_model.core.graph import Graph

logger = logging.getLogger(__name__)


class MarkdownNotesBuilder:
    """Builds notes sections for markdown output.

    This class handles the creation of forecast notes and adjustment notes
    that are appended to the main statement table.
    """

    def build_notes(
        self,
        graph: Graph,
        forecast_configs: Optional[dict[str, Any]] = None,
        adjustment_filter: Optional[Any] = None,
    ) -> list[str]:
        """Build forecast and adjustment notes.

        Args:
            graph: The Graph object containing financial data.
            forecast_configs: Dictionary mapping node IDs to forecast configurations.
            adjustment_filter: Filter for adjustments to include.

        Returns:
            List of strings representing the notes sections.
        """
        lines = []

        # Add forecast notes
        if forecast_configs:
            forecast_lines = self._build_forecast_notes(forecast_configs)
            if forecast_lines:
                lines.extend(forecast_lines)

        # Add adjustment notes
        adjustment_lines = self._build_adjustment_notes(graph, adjustment_filter)
        if adjustment_lines:
            lines.extend(adjustment_lines)

        return lines

    def _build_forecast_notes(self, forecast_configs: dict[str, Any]) -> list[str]:
        """Build forecast notes section.

        Args:
            forecast_configs: Dictionary mapping node IDs to forecast configurations.

        Returns:
            List of strings for the forecast notes section.
        """
        if not forecast_configs:
            return []

        notes = ["", "## Forecast Notes"]  # Add blank line before header

        for node_id, config in forecast_configs.items():
            method = config.get("method", "N/A")
            cfg_details = config.get("config")
            desc = f"- **{node_id}**: Forecasted using method '{method}'"

            # Add method-specific details
            if method == "simple" and cfg_details is not None:
                desc += f" (e.g., simple growth rate: {cfg_details:.1%})."
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
                desc += (
                    f" (using '{dist_name}' distribution with params: {params_str})."
                )
            else:
                desc += "."

            notes.append(desc)

        return notes

    def _build_adjustment_notes(
        self, graph: Graph, adjustment_filter: Optional[Any] = None
    ) -> list[str]:
        """Build adjustment notes section.

        Args:
            graph: The Graph object containing adjustments.
            adjustment_filter: Filter for adjustments to include.

        Returns:
            List of strings for the adjustment notes section.
        """
        all_adjustments: list[Adjustment] = graph.list_all_adjustments()
        if not all_adjustments:
            return []

        # Apply filter to adjustments
        filtered_adjustments = self._filter_adjustments(
            all_adjustments, adjustment_filter
        )
        if not filtered_adjustments:
            return []

        lines = [
            "",
            "## Adjustment Notes (Matching Filter)",
        ]  # Add blank line before header

        # Sort adjustments for consistent output
        sorted_adjustments = sorted(
            filtered_adjustments,
            key=lambda x: (x.node_name, x.period, x.priority, x.timestamp),
        )

        for adj in sorted_adjustments:
            tags_str = ", ".join(sorted(adj.tags)) if adj.tags else "None"
            details = (
                f"- **{adj.node_name}** ({adj.period}, Scenario: {adj.scenario}, "
                f"Prio: {adj.priority}): {adj.type.name.capitalize()} adjustment of {adj.value:.2f}. "
                f"Reason: {adj.reason}. Tags: [{tags_str}]. (ID: {adj.id})"
            )
            lines.append(details)

        return lines

    def _filter_adjustments(
        self, all_adjustments: list[Adjustment], adjustment_filter: Optional[Any]
    ) -> list[Adjustment]:
        """Filter adjustments based on the provided filter.

        Args:
            all_adjustments: List of all adjustments.
            adjustment_filter: Filter to apply.

        Returns:
            List of filtered adjustments.
        """
        # Create a filter instance based on the input
        filt: AdjustmentFilter

        if isinstance(adjustment_filter, AdjustmentFilter):
            filt = adjustment_filter.model_copy(
                update={"period": None}
            )  # Ignore period context
        elif isinstance(adjustment_filter, set):
            filt = AdjustmentFilter(
                include_tags=adjustment_filter,
                include_scenarios={
                    DEFAULT_SCENARIO
                },  # Assume default scenario for tag shorthand
                period=None,
            )
        else:  # Includes None or other types
            filt = AdjustmentFilter(include_scenarios={DEFAULT_SCENARIO}, period=None)

        # Apply the filter
        return [adj for adj in all_adjustments if filt.matches(adj)]
