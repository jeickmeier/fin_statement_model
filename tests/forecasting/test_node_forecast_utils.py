from __future__ import annotations

import math
import types

import pytest

from fin_statement_model.forecasting.forecaster import node_forecast as nf


def test_clamp_logic():
    bad = -999.0
    # NaN and Inf replaced
    assert nf._clamp(math.nan, True, bad) == bad
    assert nf._clamp(math.inf, True, bad) == bad
    # Negative not allowed
    assert nf._clamp(-1.0, False, bad) == bad
    # Value preserved when allowed
    assert nf._clamp(5.0, True, bad) == 5.0


def test_calc_bad_value_with_default(monkeypatch):
    # cfg returns default value 0.0 when key not found
    monkeypatch.setattr(nf, "cfg", lambda path, *_, **__: 123.0, raising=True)
    assert nf._calc_bad_value() == 123.0
