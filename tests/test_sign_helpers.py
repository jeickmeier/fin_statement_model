from fin_statement_model.core.graph import Graph
from fin_statement_model.statements.population.item_processors import (
    CalculatedItemProcessor,
)
from fin_statement_model.statements.structure.items import CalculatedLineItem
from typing import Any, Optional


def test_ensure_signed_nodes_idempotent() -> None:
    graph = Graph()
    # Add base node
    graph.add_financial_statement_item("Revenue", {"2023": 100.0})
    # First call creates signed node
    created_first = graph.ensure_signed_nodes(["Revenue"])
    assert created_first == ["Revenue_signed"]
    assert graph.has_node("Revenue_signed")
    # Second call is idempotent: no new nodes
    created_second = graph.ensure_signed_nodes(["Revenue"])
    assert created_second == []
    # Signed node still present
    assert graph.has_node("Revenue_signed")


def test_resolve_inputs_pure_no_mutation() -> None:
    graph = Graph()
    # Add base node
    graph.add_financial_statement_item("COGS", {"2023": 0.0})

    # Stub resolver that returns raw id
    class DummyResolver:
        def resolve(self, item_id: str, graph_arg: Graph) -> str:
            return item_id

    # Stub statement that marks COGS as negative
    class DummyStatement:
        def find_item_by_id(self, item_id: str) -> Optional[Any]:
            # Negative sign for COGS
            class It:
                sign_convention = -1

            return It() if item_id == "COGS" else None

    proc = CalculatedItemProcessor(DummyResolver(), graph, DummyStatement())  # type: ignore[arg-type,arg-type]

    # Create dummy CalculatedLineItem-like object
    class DummyItem:
        input_ids = ["COGS"]

    # Record node count before
    before_count = len(graph.nodes)
    resolved, missing = proc._resolve_inputs(DummyItem())  # type: ignore[arg-type]
    # Since signed node not created, resolved should be empty, missing reports signed id
    assert resolved == []
    assert missing == [("COGS", "COGS_signed")]
    # Graph mutation count unchanged
    assert len(graph.nodes) == before_count


def test_calculated_item_processor_flow_positive_and_negative() -> None:
    graph = Graph()
    # Add two base nodes
    graph.add_financial_statement_item("A", {"2023": 10.0})
    graph.add_financial_statement_item("B", {"2023": 20.0})

    # Stub resolver returns id
    class DummyResolver:
        def resolve(self, item_id: str, graph_arg: Graph) -> str:
            return item_id

    # Statement stub: marks B negative, A positive
    class DummyStatement:
        def find_item_by_id(self, item_id: str) -> Any:
            class It:
                sign_convention = -1 if item_id == "B" else 1

            return It()

    proc = CalculatedItemProcessor(DummyResolver(), graph, DummyStatement())  # type: ignore[arg-type,arg-type]
    # Positive-only calculation
    calc_pos = CalculatedLineItem(
        id="sum_ab",
        name="sum_ab",
        calculation={"type": "addition", "inputs": ["A", "A"], "parameters": {}},
        sign_convention=1,
    )
    res1 = proc.process(calc_pos)
    assert res1.success and res1.node_added
    assert graph.has_node("sum_ab")
    # Negative-including calculation: should create B_signed
    calc_neg = CalculatedLineItem(
        id="neg_b_calc",
        name="neg_b_calc",
        calculation={"type": "addition", "inputs": ["B"], "parameters": {}},
        sign_convention=1,
    )
    res2 = proc.process(calc_neg)
    assert res2.success and res2.node_added
    # Signed node must exist
    assert graph.has_node("B_signed")
    # Output node created
    assert graph.has_node("neg_b_calc")

    # Re-running should not add new nodes
    before = set(graph.nodes.keys())
    res3 = proc.process(calc_neg)
    assert res3.success and not res3.node_added
    assert set(graph.nodes.keys()) == before
