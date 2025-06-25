import tempfile

import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.templates import TemplateRegistry


def _build_simple_graph():
    g = Graph(periods=["2023", "2024"])
    _ = g.add_financial_statement_item("Revenue", {"2023": 100.0, "2024": 120.0})
    _ = g.add_financial_statement_item("COGS", {"2023": 50.0, "2024": 60.0})
    g.add_calculation(
        name="GrossProfit",
        input_names=["Revenue", "COGS"],
        operation_type="formula",
        formula="input_0 - input_1",
        formula_variable_names=["input_0", "input_1"],
    )
    return g


@pytest.fixture(scope="function")
def tmp_registry_path(monkeypatch):
    """Provide isolated registry directory via env var for each test."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        monkeypatch.setenv("FSM_TEMPLATES_PATH", tmp_dir)
        yield tmp_dir  # tests run inside context – directory is cleaned afterwards


def test_graph_clone_deep(tmp_registry_path):  # noqa: WPS442 – fixture used for env setup
    g = _build_simple_graph()
    clone = g.clone(deep=True)

    # Mutate clone and ensure original unaffected
    clone.set_value("Revenue", "2023", 999.0)
    assert g.calculate("Revenue", "2023") == 100.0

    # Ensure node objects differ
    assert id(clone.get_node("Revenue")) != id(g.get_node("Revenue"))


def test_instantiate_with_periods_and_rename(tmp_registry_path):  # noqa: WPS442
    g = _build_simple_graph()
    template_id = TemplateRegistry.register_graph(g, name="simple.model", meta={"category": "demo"})

    new_periods = ["2025"]
    rename_map = {"GrossProfit": "GP"}
    instantiated = TemplateRegistry.instantiate(template_id, periods=new_periods, rename_map=rename_map)

    # New period present
    for p in new_periods:
        assert p in instantiated.periods

    # Renamed node exists and computes correctly
    assert instantiated.calculate("GP", "2023") == 50.0
    assert not instantiated.has_node("GrossProfit") 