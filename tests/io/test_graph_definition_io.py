"""Tests for GraphDefinitionReader & Writer registry integration."""

from __future__ import annotations

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.core import get_reader, get_writer
from fin_statement_model.io.graph.definition_io import (
    GraphDefinitionReader,
    GraphDefinitionWriter,
)


def _make_simple_graph() -> Graph:
    g = Graph(periods=["2023"])
    g.add_financial_statement_item("Revenue", {"2023": 100.0})
    return g


def test_registry_instantiation() -> None:
    """Reader/Writer should be retrievable via registry with minimal config."""
    reader = get_reader("graph_definition_dict", source={})
    writer = get_writer("graph_definition_dict", target=None)

    assert isinstance(reader, GraphDefinitionReader)
    assert isinstance(writer, GraphDefinitionWriter)


def test_round_trip() -> None:
    """Verify writer→reader round-trip reproduces the same node values."""
    graph = _make_simple_graph()
    definition = GraphDefinitionWriter().write(graph, target=None)

    reconstructed = GraphDefinitionReader().read(definition)

    # Ensure node and value are preserved
    assert "Revenue" in reconstructed.nodes
    assert reconstructed.nodes["Revenue"].values == {"2023": 100.0}
