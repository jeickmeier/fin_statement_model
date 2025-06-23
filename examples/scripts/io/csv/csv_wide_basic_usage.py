"""csv_wide_basic_usage.py.

Example showing how to use the DataFrame-based reader to ingest *wide*-layout
financial data.

In wide layout each row represents a single financial statement item and each
column represents a period.

The sample CSV bundled alongside this script (``sample_data_wide_format.csv``)
looks like::

    item,2023,2024
    revenue,1500,1650
    cost_of_goods_sold,-600,-660

The script loads that CSV into a :class:`pandas.DataFrame`, feeds it to the
``dataframe`` reader, and then demonstrates exporting the resulting
:class:`fin_statement_model.core.graph.Graph` back to a nested ``dict`` via the
``dict`` writer.

Run directly with::

    python examples/scripts/io/csv/csv_wide_basic_usage.py
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
SAMPLE_CSV_WIDE = BASE_DIR / "sample_data_wide_format.csv"


# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------


def read_wide_csv_to_graph(csv_path: str | Path) -> Graph:
    """Read a *wide* CSV into a Graph using the DataFrame reader."""
    if not Path(csv_path).exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Load CSV → DataFrame, set the first column (item) as index so periods are columns
    df_raw = pd.read_csv(csv_path, index_col=0)

    graph = read_data(
        format_type="dataframe",
        source=df_raw,
    )
    return graph


# -----------------------------------------------------------------------------
# Script entry-point
# -----------------------------------------------------------------------------


def main(_: list[str] | None = None) -> None:
    """End-to-end demonstration of the wide-format workflow."""
    graph = read_wide_csv_to_graph(SAMPLE_CSV_WIDE)

    for name, node in graph.nodes.items():
        pass

    # Export graph → nested dict using the DictWriter
    write_data(format_type="dict", graph=graph, target=None)  # type: ignore[assignment]


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
