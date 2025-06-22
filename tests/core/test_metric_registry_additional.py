from __future__ import annotations

from fin_statement_model.core.metrics.registry import MetricRegistry
from fin_statement_model.core.metrics.models import MetricDefinition


def _sample_definition(id_: str) -> MetricDefinition:
    return MetricDefinition(
        name=id_.replace("_", " ").title(),
        description="desc",
        inputs=["a"],
        formula="a",
        tags=[],
    )


def test_metric_registry_register_and_get() -> None:
    reg = MetricRegistry()
    reg.register_definition(_sample_definition("gross_profit"))

    assert len(reg) == 1
    assert "gross_profit" in reg
    assert reg.list_metrics() == ["gross_profit"]

    definition = reg.get("gross_profit")
    assert definition.formula == "a"


import pytest


def test_metric_registry_get_missing_raises() -> None:
    reg = MetricRegistry()
    with pytest.raises(KeyError):
        reg.get("nonexistent")
