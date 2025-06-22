from __future__ import annotations

import pytest

from fin_statement_model.forecasting.strategies import (
    forecast_registry,
    get_forecast_method,
    register_forecast_method,
)
from fin_statement_model.forecasting.methods.simple import SimpleForecastMethod


class _DummyMethod(SimpleForecastMethod):
    @property
    def name(self) -> str:  # override
        return "dummy_simple"


def test_registry_basic_operations():
    # Existing built-in method
    simple = get_forecast_method("simple")
    assert simple.name == "simple"

    # Register new method
    new_method = _DummyMethod()
    register_forecast_method(new_method)
    assert forecast_registry.has_method("dummy_simple")

    # Info retrieval
    info = forecast_registry.get_method_info("dummy_simple")
    assert info["name"] == "dummy_simple"

    # Unregister and expect failure
    forecast_registry.unregister("dummy_simple")
    with pytest.raises(ValueError):
        forecast_registry.get_method("dummy_simple")
