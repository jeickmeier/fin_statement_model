"""Regression tests ensuring :class:`GraphFacade` behaves like the legacy Graph.

These tests provide a *very thin* verification layer that the newly
introduced façade delegates all behaviour to the underlying implementation
without breaking public semantics.
"""

from __future__ import annotations


from fin_statement_model.core.graph import GraphFacade, Graph


def test_facade_basic_calculation():
    """`GraphFacade` should calculate values identically to the legacy alias."""

    facade = GraphFacade(periods=["2023"])
    _ = facade.add_financial_statement_item("Revenue", {"2023": 150})

    assert facade.calculate("Revenue", "2023") == 150


def test_facade_repr_snapshot():
    """The string representation of the façade matches the legacy class."""

    facade = GraphFacade()
    legacy = Graph()

    assert repr(facade) == repr(legacy)
