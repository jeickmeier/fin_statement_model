"""Forecaster sub-package entry-point.

This file simply re-exports the public `StatementForecaster` class so that
end-users can continue importing it from
`fin_statement_model.forecasting` *or* from the new
`fin_statement_model.forecasting.forecaster` namespace.
"""

from __future__ import annotations

from .controller import StatementForecaster  # noqa: F401
