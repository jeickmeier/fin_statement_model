from __future__ import annotations

"""Additional tests for in-memory IO readers and writers.

These tests cover the DictReader/Writer and DataFrameReader/Writer which
operate entirely in-memory and therefore do not require any file system
interactions.  The goal is to exercise both the happy-path and common
error scenarios to boost statement coverage for the *fin_statement_model.io*
subpackage.
"""

import pandas as pd
import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io import read_data, write_data
from fin_statement_model.io.exceptions import ReadError, FormatNotSupportedError


# -----------------------------------------------------------------------------
# Helper fixtures
# -----------------------------------------------------------------------------


@pytest.fixture()
def sample_graph() -> Graph:
    """Return a tiny graph containing two historical periods."""
    g = Graph(periods=["2023", "2024"])
    g.add_node(
        FinancialStatementItemNode(
            name="Revenue", values={"2023": 100.0, "2024": 110.0}
        )
    )
    g.add_node(
        FinancialStatementItemNode(name="COGS", values={"2023": 60.0, "2024": 70.0})
    )
    return g


# -----------------------------------------------------------------------------
# DictReader / DictWriter
# -----------------------------------------------------------------------------


def test_dict_reader_writer_roundtrip(sample_graph: Graph) -> None:
    """Ensure that writing and subsequently reading via the *dict* format
    produces an equivalent graph (node values preserved)."""
    # 1. Export to dict ----------------------------------------------------------------
    exported: dict[str, dict[str, float]] = write_data(
        format_type="dict", graph=sample_graph, target=None  # type: ignore[arg-type]
    )

    # Basic sanity - writer should return a nested dict structure
    assert isinstance(exported, dict)
    assert exported["Revenue"]["2023"] == 100.0

    # 2. Re-import dict back into a new Graph ------------------------------------------
    imported_graph = read_data(format_type="dict", source=exported)

    # Compare a couple of values to ensure data survived the round-trip
    for node_name, period in (("Revenue", "2024"), ("COGS", "2023")):
        assert imported_graph.get_node(node_name).calculate(
            period
        ) == sample_graph.get_node(node_name).calculate(period)


def test_dict_reader_invalid_source_raises() -> None:
    """Passing a non-dict *source* should raise a *ReadError*."""
    with pytest.raises(ReadError):
        read_data(format_type="dict", source=[1, 2, 3])  # type: ignore[arg-type]


# -----------------------------------------------------------------------------
# DataFrameReader / DataFrameWriter
# -----------------------------------------------------------------------------


def test_dataframe_reader_writer_roundtrip(sample_graph: Graph) -> None:
    """Verify DataFrameWriter followed by DataFrameReader retains values."""
    # 1. Export graph → DataFrame
    df = write_data(format_type="dataframe", graph=sample_graph, target=None)
    assert isinstance(df, pd.DataFrame)
    assert "Revenue" in df.index
    assert "2023" in df.columns

    # 2. Re-import DataFrame → Graph
    graph_from_df = read_data(format_type="dataframe", source=df.copy())

    # Validate a couple of numbers
    assert graph_from_df.get_node("COGS").calculate("2024") == 70.0


# -----------------------------------------------------------------------------
# Registry / facade negative paths
# -----------------------------------------------------------------------------


def test_unknown_format_raises() -> None:
    """Requesting an unregistered IO format must raise *FormatNotSupportedError*."""
    with pytest.raises(FormatNotSupportedError):
        read_data(format_type="not-a-format", source="irrelevant")
