"""excel_basic_usage.py
Example demonstrating how to import data from an Excel worksheet using the
*excel* IO format.

This example assumes a sample workbook (``sample_data.xlsx``) shipped alongside
the script with the following *wide* layout::

    item | 2023 | 2024
    ------------------
    revenue | 1500 | 1650
    cost_of_goods_sold | -600 | -660

Workflow
--------
1. Import the worksheet into a `Graph` by calling ``read_data`` with
   ``format_type="excel"``.
2. Display node values.
3. Export the graph back to a DataFrame (in-memory) just to demonstrate writer
   interoperability.

Run the script with::

    python examples/scripts/io/excel/excel_basic_usage.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from fin_statement_model.io import read_data, write_data
from fin_statement_model.core.graph import Graph

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

BASE_DIR = Path(__file__).with_suffix("").parent
SAMPLE_XLSX = BASE_DIR / "sample_data.xlsx"
SHEET_NAME = "Sheet1"


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def excel_to_graph(xlsx_path: Path) -> Graph:  # noqa: D401
    """Import Excel into Graph using the IO facade."""
    graph = read_data(
        format_type="excel",
        source=str(xlsx_path),
        config={
            "sheet_name": SHEET_NAME,
            # items_col=1 and periods_row=1 are defaults matching our layout
        },
    )
    return graph


# -----------------------------------------------------------------------------
# Main demo
# -----------------------------------------------------------------------------


def main(_: list[str] | None = None) -> None:  # noqa: D401
    """End-to-end import example for Excel reader."""
    if not SAMPLE_XLSX.exists():
        raise FileNotFoundError(
            f"Expected sample workbook not found at {SAMPLE_XLSX}. "
            "Please ensure 'sample_data.xlsx' is present in the same directory."
        )

    print(f"Using sample workbook: {SAMPLE_XLSX}\n")

    graph = excel_to_graph(SAMPLE_XLSX)

    print("Graph periods:", graph.periods)
    print("Graph nodes and values:")
    for name, node in graph.nodes.items():
        print(f"  - {name}: {node.values}")

    # Demonstrate round-trip by exporting to DataFrame
    df_out: pd.DataFrame = write_data(
        format_type="dataframe", graph=graph, target=None
    )  # type: ignore[assignment]

    print("\nExported DataFrame representation:\n", df_out)


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
