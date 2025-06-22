"""dataframe_basic_usage.py
Example demonstrating how to ingest data from an in-memory ``pandas.DataFrame``
using the *dataframe* IO format and then export the resulting graph back to an
Excel file (via the *excel* writer).

Unlike the CSV examples, no external files are required – the DataFrame is
created directly in the script.

Steps:
1. Build a wide-layout DataFrame where rows are items and columns are periods.
2. Call ``read_data(format_type="dataframe")`` to convert the DataFrame into a
   :class:`fin_statement_model.core.graph.Graph`.
3. Inspect a few node values.
4. Export the graph to a temporary Excel file using ``write_data`` with the
   ``excel`` writer.

Run the script with::

    python examples/scripts/io/dataframe/dataframe_basic_usage.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

from fin_statement_model.io import read_data, write_data
from fin_statement_model.core.graph import Graph


# -----------------------------------------------------------------------------
# Build sample DataFrame (wide layout)
# -----------------------------------------------------------------------------


def create_sample_dataframe() -> pd.DataFrame:  # noqa: D401
    """Return a simple wide-format DataFrame for demonstration."""
    df = pd.DataFrame(
        {
            "2023": [1500, -600],
            "2024": [1650, -660],
        },
        index=["revenue", "cost_of_goods_sold"],
    )
    return df


# -----------------------------------------------------------------------------
# Helper to convert DF → Graph
# -----------------------------------------------------------------------------


def dataframe_to_graph(df: pd.DataFrame) -> Graph:  # noqa: D401
    """Convert DataFrame to Graph via IO facade."""
    graph = read_data(format_type="dataframe", source=df)
    return graph


# -----------------------------------------------------------------------------
# Main demo
# -----------------------------------------------------------------------------


def main(_: list[str] | None = None) -> None:  # noqa: D401
    """End-to-end example using DataFrame reader & Excel writer."""
    df = create_sample_dataframe()
    print("Input DataFrame:\n", df, "\n")

    graph = dataframe_to_graph(df)

    print("Graph periods:", graph.periods)
    for node_name in sorted(graph.nodes):
        node = graph.nodes[node_name]
        print(f"  - {node.name}: {node.values}")

    # Export to Excel in a temp file just to demonstrate writer usage
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    write_data(
        format_type="excel",
        graph=graph,
        target=str(tmp_path),
        config={"sheet_name": "DemoExport"},
    )
    print(f"\nGraph exported to Excel file: {tmp_path}")


if __name__ == "__main__":  # pragma: no cover
    import sys

    main(sys.argv[1:])
