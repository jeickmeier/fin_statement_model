"""Builder for markdown notes sections (forecast and adjustment notes).

Moved from `io.formats.markdown.notes`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fin_statement_model.core.adjustments.models import (
    DEFAULT_SCENARIO,
    Adjustment,
    AdjustmentFilter,
)

if TYPE_CHECKING:
    from fin_statement_model.core.graph import Graph

logger = logging.getLogger(__name__)


class MarkdownNotesBuilder:
    """Builds notes sections for markdown output."""

    def build_notes(
        self,
        graph: Graph,
        forecast_configs: dict[str, Any] | None = None,
        adjustment_filter: Any | None = None,
    ) -> list[str]:
        """Compile forecast and adjustment notes for Markdown output.

        Args:
            graph: The graph providing adjustments and, indirectly, periods.
            forecast_configs: Mapping ``node_id -> forecast_config`` as produced
                by the forecasting service.
            adjustment_filter: Filter object or tag set limiting which
                adjustments are included.

        Returns:
            List of Markdown-formatted strings (one per line).  The list is
            empty when neither forecasts nor relevant adjustments are present.
        """
        lines: list[str] = []
        if forecast_configs:
            lines.extend(self._build_forecast_notes(forecast_configs))
        lines.extend(self._build_adjustment_notes(graph, adjustment_filter))
        return lines

    def _build_forecast_notes(self, forecast_configs: dict[str, Any]) -> list[str]:
        if not forecast_configs:
            return []
        notes = ["", "## Forecast Notes"]
        for node_id, cfg in forecast_configs.items():
            method = cfg.get("method", "N/A")
            details = cfg.get("config")
            desc = f"- **{node_id}**: Forecasted using method '{method}'"
            if method == "simple" and details is not None:
                desc += f" (e.g., simple growth rate: {details:.1%})."
            elif method == "curve" and details:
                rates = ", ".join(f"{r:.1%}" for r in details)
                desc += f" (e.g., specific growth rates: [{rates}])."
            elif method == "historical_growth":
                desc += " (based on average historical growth)."
            elif method == "average":
                desc += " (based on historical average value)."
            elif method == "statistical":
                dist = details.get("distribution", "unknown")
                params = details.get("params", {})
                params_str = ", ".join(
                    f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}" for k, v in params.items()
                )
                desc += f" (using '{dist}' distribution with params: {params_str})."
            else:
                desc += "."
            notes.append(desc)
        return notes

    def _build_adjustment_notes(self, graph: Graph, adjustment_filter: Any | None = None) -> list[str]:
        adjustments = graph.list_all_adjustments()
        if not adjustments:
            return []
        filt = self._build_filter(adjustment_filter)
        filtered = [a for a in adjustments if filt.matches(a)]
        if not filtered:
            return []
        lines = ["", "## Adjustment Notes (Matching Filter)"]
        sorted_adj = sorted(filtered, key=lambda a: (a.node_name, a.period, a.priority, a.timestamp))
        for adj in sorted_adj:
            tags = ", ".join(sorted(adj.tags)) if adj.tags else "None"
            detail = (
                f"- **{adj.node_name}** ({adj.period}, Scenario: {adj.scenario}, "
                f"Prio: {adj.priority}): {adj.type.name.capitalize()} adjustment of {adj.value:.2f}. "
                f"Reason: {adj.reason}. Tags: [{tags}]. (ID: {adj.id})"
            )
            lines.append(detail)
        return lines

    def _build_filter(self, adjustment_filter: Any | None) -> AdjustmentFilter:
        if isinstance(adjustment_filter, AdjustmentFilter):
            return adjustment_filter.model_copy(update={"period": None})
        if isinstance(adjustment_filter, set):
            return AdjustmentFilter(
                include_tags=adjustment_filter,
                include_scenarios={DEFAULT_SCENARIO},
                period=None,
            )
        return AdjustmentFilter(include_scenarios={DEFAULT_SCENARIO}, period=None)

    # Maintain backward-compat private helper used in tests
    def _filter_adjustments(self, all_adjustments: list[Adjustment], adjustment_filter: Any | None) -> list[Adjustment]:
        return [a for a in all_adjustments if self._build_filter(adjustment_filter).matches(a)]
