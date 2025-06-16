from __future__ import annotations

from fin_statement_model.core.graph.domain import Period as DomainPeriod
from fin_statement_model.core.time.period import Period as TimePeriod
from fin_statement_model.core.time.period import PeriodIndex


def test_period_class_singleton() -> None:
    """The *Period* class should be a single canonical object across layers."""

    # Classes are identical ------------------------------------------------
    assert TimePeriod is DomainPeriod

    # Behaviour is consistent ---------------------------------------------
    p1 = TimePeriod.parse("2023Q1")
    p2 = DomainPeriod.parse("2023Q1")
    assert p1 == p2

    # Shared PeriodIndex works with instances from either import path ------
    idx = PeriodIndex([p1])
    assert p2 in idx
