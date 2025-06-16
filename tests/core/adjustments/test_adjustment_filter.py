from fin_statement_model.core.graph.domain.adjustment import (
    Adjustment,
    AdjustmentFilter,
    AdjustmentType,
)


def _make_adj(**kwargs):
    return Adjustment(
        node="N",
        period="2023",
        value=1.0,
        reason="test",
        tags={"A/B", "X"},
        **kwargs,
    )


def test_filter_include_tags_and_scenario():
    adj = _make_adj(scenario="base")
    # include tag prefix A/B and scenario base -> match
    f = AdjustmentFilter(include_tags={"A/B"}, include_scenarios={"base"})
    assert f.matches(adj)


def test_filter_exclude_tags():
    adj = _make_adj()
    f = AdjustmentFilter(exclude_tags={"A"})
    assert not f.matches(adj)


def test_filter_include_type():
    adj = _make_adj(type=AdjustmentType.REPLACEMENT)
    f = AdjustmentFilter(include_types={AdjustmentType.REPLACEMENT})
    assert f.matches(adj)
