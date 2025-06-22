import pytest

from fin_statement_model.core.metrics import (
    calculate_metric,
    interpret_metric,
    metric_registry,
)
from fin_statement_model.core.nodes.base import Node


class DummyNode(Node):
    """Simple value-bearing node for metric calculation tests."""

    def __init__(self, name: str, value: float):
        super().__init__(name)
        self.values = {"2023": float(value)}

    def calculate(self, period: str) -> float:  # noqa: D401
        return float(self.values[period])

    def to_dict(self):  # noqa: D401
        return {}

    @classmethod
    def from_dict(cls, data, context=None):  # noqa: D401
        return cls(data["name"], 0.0)


# Ensure metric registry is populated (auto-loaded on import). If not, load manually.
if "current_ratio" not in metric_registry:
    from fin_statement_model.core.metrics.metric_defn import load_organized_metrics

    load_organized_metrics()


# ---------------------------------------------------------------------------
# Happy-path calculation + interpretation
# ---------------------------------------------------------------------------


def test_calculate_and_interpret_current_ratio() -> None:
    assets = DummyNode("current_assets", 200)
    liabilities = DummyNode("current_liabilities", 100)

    value = calculate_metric(
        "current_ratio", {n.name: n for n in (assets, liabilities)}, period="2023"
    )
    assert value == pytest.approx(2.0)

    metric_def = metric_registry.get("current_ratio")
    analysis = interpret_metric(metric_def, value)
    # According to YAML good_range 1.5-3.0, rating should be "good"
    assert analysis["rating"] in {"good", "excellent"}
    assert analysis["value"] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Error branches
# ---------------------------------------------------------------------------


def test_calculate_metric_unknown_metric() -> None:
    with pytest.raises(KeyError):
        calculate_metric("nonexistent_metric", {}, period="2023")


def test_calculate_metric_missing_inputs() -> None:
    # Provide only assets, missing liabilities
    assets = DummyNode("current_assets", 50)
    with pytest.raises(ValueError):
        calculate_metric("current_ratio", {"current_assets": assets}, period="2023")


# ---------------------------------------------------------------------------
# Registry list / contains behaviour (simple smoke test)
# ---------------------------------------------------------------------------


def test_metric_registry_contains() -> None:
    assert "current_ratio" in metric_registry
    assert "definitely_not_metric" not in metric_registry

    listed = metric_registry.list_metrics()
    assert "current_ratio" in listed
