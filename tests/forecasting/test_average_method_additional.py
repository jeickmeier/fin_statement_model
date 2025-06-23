from __future__ import annotations

import math
import pytest

from fin_statement_model.forecasting.methods.average import AverageForecastMethod
from fin_statement_model.core.nodes.base import Node


class _SimpleNode(Node):
    """Minimal concrete Node implementation for testing."""

    def __init__(self, name: str, values: dict[str, float]):
        super().__init__(name)
        self.values = values  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Required abstract implementations
    # ------------------------------------------------------------------
    def calculate(self, period: str) -> float:  # noqa: D401 - simple example
        """Return the stored value for *period* (or ``nan`` if missing)."""
        return self.values.get(period, math.nan)

    def to_dict(self) -> dict[str, str]:
        """Serialize by returning the name only (sufficient for test purposes)."""
        return {"name": self.name}

    @classmethod
    def from_dict(
        cls, data: dict[str, str], context: dict[str, Node] | None = None
    ) -> "_SimpleNode":
        return cls(data["name"], {})


@pytest.fixture()
def average_method() -> AverageForecastMethod:  # noqa: D401 - fixture
    """Return a fresh AverageForecastMethod instance."""
    return AverageForecastMethod()


def test_normalize_params_returns_expected_dict(
    average_method: AverageForecastMethod,
) -> None:
    """``normalize_params`` should return the correct mapping regardless of input config."""
    result = average_method.normalize_params(
        config=None, forecast_periods=["2024", "2025"]
    )
    assert result == {"forecast_type": "average", "growth_params": None}


def test_prepare_historical_data_success(average_method: AverageForecastMethod) -> None:
    """``prepare_historical_data`` should return valid historical values when present."""
    node = _SimpleNode("Revenue", {"2022": 100.0, "2023": 110.0})
    hist_values = average_method.prepare_historical_data(node, ["2022", "2023"])
    assert hist_values == [100.0, 110.0]


def test_prepare_historical_data_raises_for_no_valid_data(
    average_method: AverageForecastMethod,
) -> None:
    """When no historical data is available, a ``ValueError`` should be raised."""
    node = _SimpleNode("Revenue", {"2020": 50.0})
    with pytest.raises(ValueError):
        average_method.prepare_historical_data(node, ["2022", "2023"])
