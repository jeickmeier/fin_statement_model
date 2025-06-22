"""csv_basic_usage.py
Example demonstrating how to use the I/O facade helpers to read data from a CSV
file into a ``Graph`` object and then export the data back to a pandas
``DataFrame`` (via the ``dataframe`` writer).

The CSV reader expects the data to be in a *long* layout where each row
represents a single item/period observation.  At minimum the file must contain
three columns: item name, period identifier, and numeric value.

This script creates a temporary CSV file on-the-fly for demonstration purposes
so it can run out-of-the-box without any additional data files.

Run it directly with::

    python examples/scripts/io/csv_basic_usage.py

or import the ``create_sample_csv`` and ``read_csv_to_graph`` helpers in your
own notebooks/scripts.

"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from fin_statement_model.io import read_data, write_data
from fin_statement_model.core.graph import Graph

# -----------------------------------------------------------------------------
# Constants & helpers
# -----------------------------------------------------------------------------

# Path to the bundled sample CSV (same directory as this script)
SAMPLE_CSV_PATH = Path(__file__).with_suffix("").parent / "sample_data_long_format.csv"


def read_csv_to_graph(csv_path: str | Path) -> Graph:
    """Read the CSV file into a ``Graph`` using ``fin_statement_model.io``.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        A populated ``Graph`` instance.
    """
    if not SAMPLE_CSV_PATH.exists():
        raise FileNotFoundError(
            f"Sample CSV not found at {SAMPLE_CSV_PATH}. Ensure the file exists."
        )

    print(f"Using sample CSV located at: {SAMPLE_CSV_PATH}\n")

    graph = read_data(
        format_type="csv",
        source=str(csv_path),
        config={
            "item_col": "item",
            "period_col": "period",
            "value_col": "value",
            # Optional: explicitly set delimiter or header row here if needed.
        },
    )
    return graph


# -----------------------------------------------------------------------------
# Script entry-point
# -----------------------------------------------------------------------------


def main(_: list[str] | None = None) -> None:  # noqa: D401 – CLI helper signature
    """Run the CSV I/O example end-to-end."""
    # ------------------------------------------------------------------
    # 1) Read CSV → Graph
    # ------------------------------------------------------------------
    graph = read_csv_to_graph(SAMPLE_CSV_PATH)
    print("Graph periods:", graph.periods)
    print("Graph nodes:")
    for node_name in sorted(graph.nodes):
        node = graph.nodes[node_name]
        print(f"  - {node.name}: {node.values}")

    # ------------------------------------------------------------------
    # 2) Write Graph → pandas.DataFrame (in-memory)
    # ------------------------------------------------------------------
    df_out: pd.DataFrame = write_data(
        format_type="dataframe", graph=graph, target=None
    )  # type: ignore[assignment]
    print("\nExported DataFrame:\n", df_out)


if __name__ == "__main__":  # pragma: no cover – script entry point
    import sys

    main(sys.argv[1:])
