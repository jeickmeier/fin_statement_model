"""markdown_writer_basic_usage.py.

End-to-end demonstration of exporting a simple financial statement graph to a
Markdown file using the *markdown* I/O writer.

Run the script directly::

    python examples/scripts/io/markdown/markdown_writer_basic_usage.py
"""

from __future__ import annotations

import logging
from pathlib import Path

from fin_statement_model.core.adjustments import AdjustmentType
from fin_statement_model.core.graph import Graph
from fin_statement_model.forecasting import StatementForecaster
from fin_statement_model.io.core.registry import get_writer

# -----------------------------------------------------------------------------
# Build a minimal Graph --------------------------------------------------------
# -----------------------------------------------------------------------------

graph = Graph(periods=["2023", "2024"])

# Add two data nodes (financial statement items)
graph.add_financial_statement_item(
    "Revenue",
    {"2023": 1_200_000.0, "2024": 1_350_000.0},
)

graph.add_financial_statement_item(
    "Expenses",
    {"2023": 800_000.0, "2024": 900_000.0},
)

# Add a simple calculation node: NetIncome = Revenue - Expenses
graph.add_calculation(
    name="NetIncome",
    input_names=["Revenue", "Expenses"],
    operation_type="subtraction",
)

# Add a sample adjustment (shows as bullet list in markdown)

graph.add_adjustment(
    node_name="Revenue",
    period="2023",
    value=50_000.0,
    adj_type=AdjustmentType.ADDITIVE,
    reason="Audit adjustment - revenue recognition",
)

# -----------------------------------------------------------------------------
# Add a simple forecast node ---------------------------------------------------
# -----------------------------------------------------------------------------

# Project Revenue forward one period (2025) with a 5% growth rate
forecaster = StatementForecaster(graph)

forecast_periods = ["2025", "2026"]
node_configs = {
    "Revenue": {
        "method": "historical_growth",
        "config": {"aggregation": "mean"},  # Use mean of historical growth rates
    },
    "Expenses": {"method": "simple", "config": 0.05},  # 5% growth
}
forecaster.create_forecast(
    forecast_periods=forecast_periods, node_configs=node_configs
)

# -----------------------------------------------------------------------------
# Obtain the MarkdownWriter ----------------------------------------------------
# -----------------------------------------------------------------------------

writer = get_writer("markdown")  # Registry returns an initialised MarkdownWriter

# -----------------------------------------------------------------------------
# Export to a Markdown file ----------------------------------------------------
# -----------------------------------------------------------------------------

OUTPUT_MD = Path(__file__).with_suffix(".md")

writer.write(graph, target=OUTPUT_MD)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("Markdown statement saved to: %s", OUTPUT_MD.resolve())
