from fin_statement_model.core.adjustments.analytics import list_by_tag, summary
from fin_statement_model.core.adjustments.manager import AdjustmentManager
from fin_statement_model.core.adjustments.models import Adjustment


def _make_adj(**kwargs):
    """Helper to create Adjustment with sensible defaults."""
    base = dict(node_name="Revenue", period="2023", value=10.0, reason="manual")
    base.update(kwargs)
    return Adjustment(**base)


def test_summary_basic() -> None:
    mgr = AdjustmentManager()

    # Two adjustments for Revenue (sum 8.0), one for COGS
    adj1 = _make_adj(value=10.0, tags={"Scenario/Base"})
    adj2 = _make_adj(value=-2.0, tags={"Scenario/Base"})
    adj3 = _make_adj(node_name="COGS", value=5.0, tags={"Scenario/Bullish"})

    for adj in (adj1, adj2, adj3):
        mgr.add_adjustment(adj)

    df = summary(mgr)

    # MultiIndex [period, node_name]
    assert ("2023", "Revenue") in df.index
    assert df.loc[("2023", "Revenue"), "sum_value"] == 8.0
    assert df.loc[("2023", "Revenue"), "count"] == 2


def test_summary_tag_filter() -> None:
    mgr = AdjustmentManager()
    adj1 = _make_adj(value=1.0, tags={"Scenario/Bullish"})
    adj2 = _make_adj(value=2.0, tags={"Scenario/Base"})
    for adj in (adj1, adj2):
        mgr.add_adjustment(adj)

    df = summary(mgr, filter_input={"Scenario/Bullish"})
    # Only bullish
    assert list(df.index.get_level_values("node_name")) == ["Revenue"]
    assert df["sum_value"].iloc[0] == 1.0


def test_list_by_tag_prefix() -> None:
    mgr = AdjustmentManager()
    bullish = _make_adj(tags={"Scenario/Bullish"})
    base = _make_adj(tags={"Scenario/Base"}, value=5.0)
    mgr.load_adjustments([bullish, base])

    result = list_by_tag(mgr, "Scenario/Bullish")
    assert result == [bullish]
