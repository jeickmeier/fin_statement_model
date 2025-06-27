"""Data writer for exporting financial statements to Markdown format.

This module provides the `MarkdownWriter`, a `DataWriter` implementation that
renders a `StatementStructure` into a formatted Markdown table. It is designed
to produce human-readable reports of financial statements.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fin_statement_model.core.nodes.forecast_nodes import ForecastNode
from fin_statement_model.io.config.models import MarkdownWriterConfig
from fin_statement_model.io.core.base_table_writer import BaseTableWriter
from fin_statement_model.io.core.mixins import ConfigurationMixin, handle_write_errors
from fin_statement_model.io.core.registry import register_writer

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable

    from fin_statement_model.core.graph import Graph

# Logger configured after imports for E402 compliance
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Re-implemented generic MarkdownWriter
# ---------------------------------------------------------------------------
# The new implementation leverages `BaseTableWriter` to extract a pandas
# DataFrame representation of the graph and converts it to a markdown table
# using `pandas.DataFrame.to_markdown`.  It supports the following features:
#   * Optional recalculation of the graph prior to export
#   * Inclusion/exclusion of specific nodes
#   * Optional bullet-listed adjustments beneath the statement
#   * Extensible formatting via writer configuration parameters
# ---------------------------------------------------------------------------


def _render_adjustments(
    graph: Graph,
    periods: Iterable[str] | None = None,
    *,
    filter_input: Any = None,
) -> str:
    """Return a bullet-list markdown section of adjustments for *graph*.

    Args:
        graph: Source graph.
        periods: Optional iterable of period identifiers to include. If None,
            all periods appearing in any adjustment are included.
        filter_input: Forwarded to ``AdjustmentManager.get_filtered_adjustments``.

    Returns:
        A markdown string (can be empty) beginning with an empty line and a
        header ``"### Adjustments"`` followed by one bullet per adjustment.
    """
    from fin_statement_model.core.adjustments.models import DEFAULT_SCENARIO

    lines: list[str] = []

    periods_set: set[str] | None = set(periods) if periods is not None else None

    # Collect adjustments
    for adj in graph.list_all_adjustments():
        if periods_set is not None and adj.period not in periods_set:
            continue

        # Apply optional caller-provided filtering via AdjustmentManager helper
        if filter_input is not None:
            matched = graph.adjustment_manager.get_filtered_adjustments(
                adj.node_name,
                adj.period,
                filter_input,
            )
            if adj not in matched:
                continue

        # Compose bullet line
        scenario = "" if adj.scenario == DEFAULT_SCENARIO else f" ({adj.scenario})"
        reason = f" - {adj.reason}" if getattr(adj, "reason", None) else ""
        lines.append(f"* **{adj.node_name}** {adj.period}{scenario}: {adj.value:+,.2f}{reason}")

    # Assemble section only when there are lines
    if not lines:
        return ""

    return "\n\n### Adjustments\n" + "\n".join(lines) + "\n"


@register_writer("markdown", schema=MarkdownWriterConfig)
class MarkdownWriter(BaseTableWriter, ConfigurationMixin):
    """Export a graph as a formatted markdown financial statement.

    The writer converts the graph into a tabular statement (markdown table)
    resembling a standard financial statement layout.  Optionally, a bullet-
    list of adjustments applied to the graph can be appended.
    """

    def __init__(self, cfg: MarkdownWriterConfig | None = None) -> None:
        """Create a new MarkdownWriter instance.

        Args:
            cfg: Optional validated configuration model. When *None*, default
                values defined in :class:`MarkdownWriterConfig` are used.
        """
        super().__init__()
        # When the registry instantiates the class it passes the validated cfg
        self.cfg = cfg or MarkdownWriterConfig(format_type="markdown")

    # ------------------------------------------------------------------
    # Core public API
    # ------------------------------------------------------------------
    @handle_write_errors()
    def write(self, graph: Graph, target: Any = None, **kwargs: Any) -> str | None:
        """Render *graph* to markdown and optionally write it to *target*.

        Positional parameters mirror the :py:meth:`DataWriter.write` contract.

        Runtime overrides (highest precedence) can be supplied via *kwargs*:

        * ``recalculate`` - bool, trigger graph recalculation
        * ``include_nodes`` - list[str], subset of nodes to include
        * ``include_adjustments`` - bool, append adjustments section (default True)
        * ``filter_input`` - optional adjustment filter passed to the helper
        * ``hist_periods`` - list[str], explicit ordered list of historical periods
        * ``forecast_periods`` - list[str], explicit ordered list of forecast periods
        * ``adjustment_filter`` - AdjustmentFilterInput, overrides config value
        * ``include_forecasts`` - bool, append forecast nodes summary (default True)

        Returns:
            The rendered markdown string when *target* is None, otherwise None.
        """
        # ------------------------------------------------------------------
        # Resolve effective parameters (runtime overrides → config → defaults)
        # ------------------------------------------------------------------
        recalc: bool = self._param("recalculate", kwargs, self.cfg, default=True)
        include_nodes: list[str] | None = self._param("include_nodes", kwargs, self.cfg)
        include_adjustments: bool = self._param("include_adjustments", kwargs, self.cfg, default=True)
        hist_periods: list[str] | None = self._param("historical_periods", kwargs, self.cfg)
        forecast_periods: list[str] | None = self._param("forecast_periods", kwargs, self.cfg)
        adjustment_filter = self._param("adjustment_filter", kwargs, self.cfg)
        include_forecasts: bool = self._param("include_forecasts", kwargs, self.cfg, default=True)

        # ------------------------------------------------------------------
        # Build the markdown table from the graph data
        # ------------------------------------------------------------------
        import pandas as pd  # Local import to avoid mandatory dependency at import time

        df = self.to_dataframe(graph, include_nodes=include_nodes, recalc=recalc)

        def _reorder(_df: pd.DataFrame, periods: list[str] | None) -> pd.DataFrame:
            """Return DataFrame with columns reordered to *periods* if provided."""
            if periods is None:
                return _df
            cols = [p for p in periods if p in _df.columns]
            missing = [p for p in periods if p not in _df.columns]
            if missing:
                logger.debug("Periods not found in DataFrame, ignoring: %s", missing)
            return _df[cols]

        df_hist = _reorder(df, hist_periods)
        df_forecast = _reorder(df, forecast_periods)

        if hist_periods and forecast_periods:
            separator = pd.DataFrame({" ": [" "] * len(df)})
            df_combined = pd.concat([df_hist, separator, df_forecast], axis=1)
        else:
            df_combined = df_hist if hist_periods else df_forecast if forecast_periods else df

        md_lines: list[str] = [df_combined.to_markdown(tablefmt="github", floatfmt=",.2f", index=True)]

        if include_adjustments:
            adj_section = _render_adjustments(graph, filter_input=adjustment_filter)
            if adj_section:
                md_lines.append(adj_section)

        # ------------------------------------------------------------------
        # Forecast nodes summary bullets
        # ------------------------------------------------------------------
        if include_forecasts:
            forecast_section = self._render_forecast_summary(graph)
            if forecast_section:
                md_lines.append(forecast_section)

        markdown_output = "\n".join(md_lines)

        # ------------------------------------------------------------------
        # Write to *target* if provided
        # ------------------------------------------------------------------
        effective_target = target or getattr(self.cfg, "target", None)
        if effective_target is not None:
            if isinstance(effective_target, str | Path):
                Path(effective_target).write_text(markdown_output, encoding="utf-8")
            elif hasattr(effective_target, "write") and callable(effective_target.write):
                effective_target.write(markdown_output)
            else:
                raise TypeError(
                    "target must be a str, pathlib.Path, or file-like object with a write() method",
                )
            return None

        return markdown_output

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _render_forecast_summary(graph: Graph) -> str:
        """Return markdown bullet list summarising forecast nodes in *graph*."""
        bullets: list[str] = []

        for node in graph.nodes.values():
            fc_periods: list[str] | None = None
            fc_type: str | None = None
            params = None

            if isinstance(node, ForecastNode):
                fc_periods = getattr(node, "forecast_periods", None)
                fc_type = getattr(node, "forecast_type", None)
                params = getattr(node, "growth_params", None)
            else:
                # Look for metadata injected by StatementForecaster
                fc_periods = getattr(node, "forecast_periods", None)
                fc_type = getattr(node, "forecast_type", None)
                params = getattr(node, "growth_params", None)

            if fc_periods is None:
                continue

            periods_str = ", ".join(fc_periods) if fc_periods else "<unknown>"

            if fc_type is None:
                fc_type = "forecast"

            params_part = "" if params is None else f", params: {params}"

            bullets.append(f"* **{node.name}** ({fc_type}) forecast periods: {periods_str}{params_part}")

        if not bullets:
            return ""

        return "\n\n### Forecasts\n" + "\n".join(bullets) + "\n"
