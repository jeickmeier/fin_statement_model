import pytest
from fin_statement_model.core.adjustments.helpers import tag_matches
from fin_statement_model.core.adjustments.manager import AdjustmentManager
from fin_statement_model.core.adjustments.models import (
    Adjustment,
    AdjustmentType,
    AdjustmentFilter,
)
from fin_statement_model.core.adjustments.analytics import summary, list_by_tag


# -----------------------------------------------------------------------------
# Fixtures --------------------------------------------------------------------
# -----------------------------------------------------------------------------


@pytest.fixture()
def adj_mgr() -> AdjustmentManager:  # noqa: D401: fixture
    """Return a fresh :class:`AdjustmentManager` for every test."""
    return AdjustmentManager()


@pytest.fixture()
def sample_adjustments() -> list[Adjustment]:  # noqa: D401: fixture
    """Provide a small, diverse set of adjustments for filtering tests."""

    return [
        # Default-scenario additive (value 10)
        Adjustment(
            node_name="A",
            period="2023",
            value=10.0,
            reason="add 10",
            tags={"Group/Promo"},
        ),
        # Default-scenario multiplicative (×2, priority 1)
        Adjustment(
            node_name="A",
            period="2023",
            value=2.0,
            type=AdjustmentType.MULTIPLICATIVE,
            priority=1,
            reason="mul 2",
            tags={"Scenario/Bullish"},
        ),
        # Alt-scenario replacement (value 5)
        Adjustment(
            node_name="A",
            period="2023",
            value=5.0,
            type=AdjustmentType.REPLACEMENT,
            scenario="alt",
            reason="override",
            tags={"Override"},
        ),
    ]


# -----------------------------------------------------------------------------
# helpers.tag_matches ----------------------------------------------------------
# -----------------------------------------------------------------------------


def test_tag_matches_basic() -> None:
    """tag_matches should correctly evaluate positive/negative cases."""

    assert tag_matches({"A/B/C", "X"}, {"A/B"}) is True
    assert tag_matches({"A/B/C"}, {"D"}) is False
    # Early-exit branches: empty prefixes or empty tags
    assert tag_matches(set(), {"A"}) is False
    assert tag_matches({"A/B"}, set()) is False


# -----------------------------------------------------------------------------
# AdjustmentManager._apply_one & apply_adjustments -----------------------------
# -----------------------------------------------------------------------------


def test_apply_one_variants(adj_mgr: AdjustmentManager) -> None:
    """Cover additive, multiplicative, replacement and base==0 edge case."""

    add = Adjustment(node_name="N", period="P", value=5, reason="r")
    mult = Adjustment(
        node_name="N",
        period="P",
        value=3,
        type=AdjustmentType.MULTIPLICATIVE,
        reason="r",
    )
    repl = Adjustment(
        node_name="N",
        period="P",
        value=42,
        type=AdjustmentType.REPLACEMENT,
        reason="r",
    )

    assert adj_mgr._apply_one(100, add) == pytest.approx(105)
    assert adj_mgr._apply_one(10, mult) == pytest.approx(30)
    assert adj_mgr._apply_one(0, mult) == 0.0  # special-case path
    assert adj_mgr._apply_one(999, repl) == 42.0


def test_apply_adjustments_priority_order(adj_mgr: AdjustmentManager) -> None:
    """Lower priority should be applied first (0 before 1)."""

    # priority 1 additive, priority 0 multiplicative
    add = Adjustment(node_name="N", period="P", value=10, reason="r", priority=1)
    mult = Adjustment(
        node_name="N",
        period="P",
        value=2,
        type=AdjustmentType.MULTIPLICATIVE,
        reason="r",
        priority=0,
    )
    adjusted, flag = adj_mgr.apply_adjustments(100.0, [add, mult])
    # Expected: 100*2=200 then +10 = 210
    assert adjusted == 210.0
    assert flag is True


# -----------------------------------------------------------------------------
# _normalize_filter & get_filtered_adjustments ---------------------------------
# -----------------------------------------------------------------------------


def test_normalize_filter_variants(adj_mgr: AdjustmentManager) -> None:
    """Exercise the various branches of _normalize_filter."""

    nf_default = adj_mgr._normalize_filter(None, period="2023")
    assert nf_default.include_scenarios == {"default"}
    assert nf_default.period == "2023"

    nf_set = adj_mgr._normalize_filter({"X"}, period="2023")
    assert nf_set.include_tags == {"X"}
    assert nf_set.include_scenarios == {"default"}

    custom_filter = AdjustmentFilter(include_scenarios={"alt"})
    nf_custom = adj_mgr._normalize_filter(custom_filter)
    assert nf_custom.include_scenarios == {"alt"}
    # period remains None because not supplied
    assert nf_custom.period is None


@pytest.mark.usefixtures("sample_adjustments")
def test_get_filtered_adjustments_variants(
    adj_mgr: AdjustmentManager, sample_adjustments: list[Adjustment]
) -> None:
    """Cover tag shorthand, 1-arg callable, 2-arg callable and exclude scenario."""

    # Load adjustments
    adj_mgr.load_adjustments(sample_adjustments)

    # Tag shorthand selects only Bullish tag (multiplicative)
    bull = adj_mgr.get_filtered_adjustments("A", "2023", {"Scenario/Bullish"})
    assert len(bull) == 1 and bull[0].type is AdjustmentType.MULTIPLICATIVE

    # 1-arg callable: value > 5  ⇒ additive (10) & replacement (5) => only additive
    gt5 = adj_mgr.get_filtered_adjustments("A", "2023", lambda a: a.value > 5)
    assert {a.value for a in gt5} == {10.0}

    # 2-arg callable: choose alt scenario only
    alt_only = adj_mgr.get_filtered_adjustments(
        "A",
        "2023",
        lambda a, p: a.scenario == "alt" and p == "2023",
    )
    assert len(alt_only) == 1 and alt_only[0].scenario == "alt"

    # Exclude alt via AdjustmentFilter
    excl_alt = adj_mgr.get_filtered_adjustments(
        "A",
        "2023",
        AdjustmentFilter(exclude_scenarios={"alt"}),
    )
    assert all(a.scenario != "alt" for a in excl_alt)


# -----------------------------------------------------------------------------
# Analytics helpers ------------------------------------------------------------
# -----------------------------------------------------------------------------


def test_summary_group_by_scenario(
    adj_mgr: AdjustmentManager, sample_adjustments: list[Adjustment]
) -> None:
    """Group summary by scenario column and validate aggregation logic."""

    adj_mgr.load_adjustments(sample_adjustments)

    df = summary(adj_mgr, group_by=["scenario"])
    # Two scenarios → two rows
    assert set(df.index) == {"default", "alt"}
    # default scenario: additive (10) + multiplicative (2) raw values = 12
    assert df.loc["default", "sum_value"] == pytest.approx(12.0)
    # alt scenario replacement yields sum 5
    assert df.loc["alt", "sum_value"] == pytest.approx(5.0)


def test_summary_empty(adj_mgr: AdjustmentManager) -> None:
    """Calling summary on an empty manager returns an empty DataFrame with columns."""

    df = summary(adj_mgr)
    assert df.empty and {"count", "sum_value", "mean_abs_value"}.issubset(df.columns)


def test_list_by_tag_callable_filter(
    adj_mgr: AdjustmentManager, sample_adjustments: list[Adjustment]
) -> None:
    """list_by_tag should accept an additional callable filter (uses _filter_adjustments_static callable branch)."""

    adj_mgr.load_adjustments(sample_adjustments)

    res = list_by_tag(adj_mgr, "Group", filter_input=lambda a: a.value > 5)
    assert len(res) == 1 and res[0].tags == {"Group/Promo"}
