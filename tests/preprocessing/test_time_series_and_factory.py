from __future__ import annotations

"""Tests for TimeSeriesTransformer plus TransformerFactory registration edge cases."""

import pandas as pd
import pytest

from fin_statement_model.preprocessing.transformers.time_series import (
    TimeSeriesTransformer,
)
from fin_statement_model.preprocessing.transformer_service import (
    TransformerFactory,
    CompositeTransformer,
)
from fin_statement_model.preprocessing.errors import (
    TransformerConfigurationError,
    TransformerRegistrationError,
)
from fin_statement_model.preprocessing.base_transformer import DataTransformer


# ----------------------------------------------------------------------------
# TimeSeriesTransformer basic operations
# ----------------------------------------------------------------------------


def _simple_df():
    return pd.DataFrame({"v": [100, 110, 120, 130]}, index=pd.RangeIndex(4))


def test_growth_rate_and_moving_average() -> None:
    df = _simple_df()

    growth = TimeSeriesTransformer("growth_rate", periods=1)
    out_growth = growth.transform(df)
    # Last computed growth should be ~8.33%
    assert out_growth["v_growth"].iloc[-1] == pytest.approx(8.33, rel=1e-2)

    ma = TimeSeriesTransformer("moving_avg", window_size=2)
    out_ma = ma.transform(df)
    assert out_ma.loc[1, "v_ma2"] == pytest.approx((100 + 110) / 2)

    # CAGR (constant 10% growth across 4 periods)
    cagr_tx = TimeSeriesTransformer("cagr")
    out_cagr = cagr_tx.transform(df)
    assert out_cagr.loc[0, "v_cagr"] == pytest.approx(10.0)


def test_invalid_transformation_type() -> None:
    with pytest.raises(ValueError):
        TimeSeriesTransformer("not_a_type")


# ----------------------------------------------------------------------------
# TransformerFactory registration and duplicate handling
# ----------------------------------------------------------------------------


class DummyTransformer(DataTransformer):
    def _transform_impl(self, data):  # noqa: D401
        return data

    def validate_input(self, data):  # noqa: D401
        return True


def test_factory_register_and_create(monkeypatch):
    name = "dummy_preproc_test"
    TransformerFactory.register_transformer(name, DummyTransformer)
    instance = TransformerFactory.create_transformer(name)
    assert isinstance(instance, DummyTransformer)

    # Duplicate registration with same class allowed (no error)
    TransformerFactory.register_transformer(name, DummyTransformer)

    # Duplicate with different class raises
    class Another(DummyTransformer):
        pass

    with pytest.raises(TransformerRegistrationError):
        TransformerFactory.register_transformer(name, Another)


def test_factory_create_unknown():
    with pytest.raises(TransformerConfigurationError):
        TransformerFactory.create_transformer("nonexistent")


# ----------------------------------------------------------------------------
# CompositeTransformer integration
# ----------------------------------------------------------------------------


def test_composite_transformer_exec():
    df = _simple_df()
    plus_one = DummyTransformer()
    plus_one._transform_impl = lambda d: d + 1  # type: ignore[assignment]
    plus_two = DummyTransformer()
    plus_two._transform_impl = lambda d: d + 2  # type: ignore[assignment]

    comp = CompositeTransformer([plus_one, plus_two])
    out = comp.execute(df)
    assert out.iloc[0, 0] == 103  # 100 +1 +2
