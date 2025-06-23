"""dict_json_basic_usage.py.

Demonstration of reading financial data from a JSON file via the *dict* IO
format and writing it back out.

The JSON file (``sample_data_dict.json``) represents the graph as a nested
dictionary::

    {
      "revenue": {"2023": 1500, "2024": 1650},
      "cost_of_goods_sold": {"2023": -600, "2024": -660}
    }

This maps directly to the structure expected by the *dict* reader: each top-level
key is a node and its value is a period→number mapping.

Steps performed:
1. Load the JSON into a Python ``dict``.
2. Convert it to a ``Graph`` using ``read_data(format_type="dict")``.
3. Display some information from the graph.
4. Export the graph back to a dictionary via ``write_data(format_type="dict")``.
5. Dump the exported dictionary to *stdout* as nicely-formatted JSON.

Run the script with::

    python examples/scripts/io/dict/dict_json_basic_usage.py
"""

from __future__ import annotations

import json
from pathlib import Path

from fin_statement_model.io import read_data, write_data
from fin_statement_model.core.graph import Graph

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

BASE_DIR = Path(__file__).with_suffix("").parent
SAMPLE_JSON = BASE_DIR / "sample_data_dict.json"


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def load_json_to_dict(path: Path) -> dict[str, dict[str, float]]:
    """Read JSON file into nested dict structure."""
    with path.open("r", encoding="utf-8") as fh:
        data: dict[str, dict[str, float]] = json.load(fh)
    return data


def dict_to_graph(data: dict[str, dict[str, float]]) -> Graph:
    """Convert nested dict to Graph using the IO facade."""
    graph = read_data(format_type="dict", source=data)
    return graph


# -----------------------------------------------------------------------------
# Main script
# -----------------------------------------------------------------------------


def main(_: list[str] | None = None) -> None:
    """End-to-end example using dict reader/writer with JSON input/output."""
    if not SAMPLE_JSON.exists():
        raise FileNotFoundError(f"Sample JSON not found: {SAMPLE_JSON}")

    data_in = load_json_to_dict(SAMPLE_JSON)

    graph = dict_to_graph(data_in)

    for name, node in graph.nodes.items():
        pass

    # Export graph back to dict
    write_data(format_type="dict", graph=graph, target=None)  # type: ignore[assignment]


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
