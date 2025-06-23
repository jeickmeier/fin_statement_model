"""adjustments_basic_usage.py.

Demonstration of the specialised *adjustments* I/O helpers.

This example shows how to:
1. Create a few `Adjustment` objects and add them to a `Graph`.
2. Export all adjustments to an Excel workbook with
   `export_adjustments_to_excel`.
3. Clear the graph's adjustments and re-import them from the workbook using
   `load_adjustments_from_excel`.

No sample file is required - the script writes to a temporary ``.xlsx`` file so
it can run anywhere without touching the repository.

Run with::

    python examples/scripts/io/adjustments/adjustments_basic_usage.py
"""

from __future__ import annotations

from pathlib import Path

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.core.adjustments.models import Adjustment
from fin_statement_model.io.adjustments.excel_io import (
    export_adjustments_to_excel,
    load_adjustments_from_excel,
)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

BASE_DIR = Path(__file__).with_suffix("").parent
EXPORT_XLSX = BASE_DIR / "exported_adjustments.xlsx"


# -----------------------------------------------------------------------------
# Build demo graph + adjustments
# -----------------------------------------------------------------------------


def build_graph_with_adjustments() -> Graph:
    """Return a Graph pre-populated with sample adjustments."""
    graph = Graph(periods=["2023", "2024"])

    # Add a simple data node - required because adjustments reference node names
    graph.add_node(FinancialStatementItemNode(name="revenue", values={}))

    # Create two adjustments
    adj1 = Adjustment(
        node_name="revenue",
        period="2023",
        value=+100,
        reason="Audit adjustment",
    )
    adj2 = Adjustment(
        node_name="revenue",
        period="2024",
        value=-50,
        reason="Correction",
        tags={"Scenario/Bullish"},
    )

    graph.adjustment_manager.add_adjustment(adj1)
    graph.adjustment_manager.add_adjustment(adj2)
    return graph


# -----------------------------------------------------------------------------
# Main demo
# -----------------------------------------------------------------------------


def main(_: list[str] | None = None) -> None:
    """Show export + import cycle for adjustments Excel helpers."""
    graph = build_graph_with_adjustments()

    for adj in graph.list_all_adjustments():
        pass

    # Export to workbook in the same directory as this script
    export_adjustments_to_excel(graph, EXPORT_XLSX)

    # Clear adjustments then reload from the Excel file
    graph.adjustment_manager.clear_all()

    load_adjustments_from_excel(graph, EXPORT_XLSX)

    for adj in graph.list_all_adjustments():
        pass


if __name__ == "__main__":  # pragma: no cover
    import sys

    main(sys.argv[1:])
