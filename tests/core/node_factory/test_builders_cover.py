import pytest

from fin_statement_model.core.node_factory.builders import (
    create_financial_statement_item,
    create_calculation_node,
    create_forecast_node,
)
from fin_statement_model.core.errors import ConfigurationError
from fin_statement_model.io.core.mixins.value_extraction import ValueExtractionMixin


class DummyExtractor(ValueExtractionMixin):
    """Concrete helper exposing :py:meth:`extract_node_value` for testing."""


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------

def test_create_financial_statement_item():
    """Basic sanity check that an item node is instantiated and stores values."""
    item = create_financial_statement_item("Revenue", {"2022": 100, "2023": 120})

    assert item.name == "Revenue"
    assert item.values == {"2022": 100, "2023": 120}


def test_create_calculation_node_addition():
    """Verify the *addition* calculation alias produces the expected sum."""
    node_a = create_financial_statement_item("A", {"2022": 30})
    node_b = create_financial_statement_item("B", {"2022": 70})

    sum_node = create_calculation_node(
        name="sum_ab",
        inputs=[node_a, node_b],
        calculation_type="addition",
    )

    assert sum_node.calculate("2022") == pytest.approx(100.0)


def test_create_calculation_node_invalid_input_type():
    """Passing non-Node objects to *inputs* should raise :class:`TypeError`."""
    with pytest.raises(TypeError):
        create_calculation_node(
            name="bad_node",
            inputs=[object()],  # not a Node instance
            calculation_type="addition",
        )


def test_create_forecast_node_simple_growth():
    """Fixed growth forecast should apply the supplied constant rate."""
    base_node = create_financial_statement_item("Base", {"2022": 100})

    forecast_node = create_forecast_node(
        forecast_type="simple",
        input_node=base_node,
        base_period="2022",
        forecast_periods=["2023", "2024"],
        growth_params=0.10,  # 10 % growth each period
    )

    assert forecast_node.calculate("2023") == pytest.approx(110.0)
    assert forecast_node.calculate("2024") == pytest.approx(121.0)


def test_create_forecast_node_missing_required():
    """Omitting required arguments must raise :class:`ConfigurationError`."""
    base_node = create_financial_statement_item("Base", {"2022": 100})

    with pytest.raises(ConfigurationError):
        create_forecast_node(
            forecast_type=None,  # type: ignore[arg-type]
            input_node=base_node,
            base_period="2022",
            forecast_periods=["2023"],
        )


# ---------------------------------------------------------------------------
# ValueExtractionMixin helpers
# ---------------------------------------------------------------------------

def test_value_extraction_direct_values():
    """extract_node_value should return the value if present in *values* dict."""

    class DummyNode:
        def __init__(self):
            self.values = {"2022": 42}

    extractor = DummyExtractor()
    assert extractor.extract_node_value(DummyNode(), "2022") == 42.0


def test_value_extraction_via_calculate():
    """When *values* is missing the period, fallback to *calculate()*."""

    class DummyNode:
        values: dict[str, float] = {}

        @staticmethod
        def calculate(period: str) -> float:  # noqa: D401  # simple stub
            assert period == "2022"
            return 3.14

    extractor = DummyExtractor()
    assert extractor.extract_node_value(DummyNode(), "2022") == pytest.approx(3.14)


def test_value_extraction_error_handling():
    """Exceptions from *calculate()* should be caught and *None* returned."""

    class FailingNode:
        values: dict[str, float] = {}

        @staticmethod
        def calculate(_period: str) -> float:  # noqa: D401
            raise ValueError("Boom")

    extractor = DummyExtractor()
    assert extractor.extract_node_value(FailingNode(), "2022") is None 