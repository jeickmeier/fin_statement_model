from fin_statement_model.core.graph.graph import Graph
from fin_statement_model.core.adjustments.models import AdjustmentType


def test_adjustment_application() -> None:
    """Ensure a simple additive adjustment is applied to the base node value."""
    graph = Graph(periods=["2023"])
    graph.add_financial_statement_item("Revenue", {"2023": 100.0})

    graph.add_adjustment(
        "Revenue",
        "2023",
        value=10.0,
        reason="Manual adjustment",
        scenario="default",
        adj_type=AdjustmentType.ADDITIVE,
    )

    adjusted_value = graph.get_adjusted_value("Revenue", "2023")
    assert adjusted_value == 110.0
