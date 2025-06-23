import textwrap
from pathlib import Path
import yaml
import pytest

from fin_statement_model.core.metrics.models import (
    MetricDefinition,
    MetricInterpretation,
)
from fin_statement_model.core.metrics.interpretation import (
    MetricInterpreter,
    MetricRating,
    interpret_metric,
)
from fin_statement_model.core.metrics.registry import MetricRegistry
from fin_statement_model.core.nodes.standard_registry import StandardNodeRegistry


# ---------------------------------------------------------------------------
# Metric interpretation helpers
# ---------------------------------------------------------------------------


def _make_metric_def() -> MetricDefinition:
    """Create a dummy metric definition with full interpretation rules."""

    interpretation = MetricInterpretation(
        good_range=[1.0, 2.0],
        warning_below=0.9,
        warning_above=2.2,
        excellent_above=2.5,
        poor_below=0.5,
        notes="Dummy metric for testing purposes.",
    )

    return MetricDefinition(
        name="Dummy Metric",
        description="A dummy metric used for unit-tests.",
        inputs=["a", "b"],
        formula="a / b",
        tags=["test"],
        units="ratio",
        category="testing",
        interpretation=interpretation,
        related_metrics=["other_dummy"],
    )


class TestMetricInterpreter:
    """Cover the decision branches of MetricInterpreter._rate_value."""

    @pytest.fixture(scope="module")
    def metric_def(self):  # type: ignore[override]
        return _make_metric_def()

    @pytest.mark.parametrize(
        ("value", "expected_rating"),
        [
            (3.0, MetricRating.EXCELLENT),  # above excellent_above
            (1.5, MetricRating.GOOD),  # within good_range
            (0.8, MetricRating.WARNING),  # below warning_below but above poor_below
            (2.3, MetricRating.WARNING),  # above warning_above but below excellent
            (0.4, MetricRating.POOR),  # below poor_below
            (2.1, MetricRating.ADEQUATE),  # none of the other rules - adequate
        ],
    )
    def test_rate_value(self, metric_def: MetricDefinition, value, expected_rating):
        interpreter = MetricInterpreter(metric_def)
        assert interpreter.rate_value(value) is expected_rating

    def test_interpret_metric_wrapper(self, metric_def: MetricDefinition):
        """The interpret_metric convenience helper should round-trip expected fields."""
        result = interpret_metric(metric_def, 1.6)
        # Ensure key fields are present and correct
        assert result["rating"] == MetricRating.GOOD.value
        assert result["metric_name"] == metric_def.name
        assert "interpretation_message" in result and result[
            "interpretation_message"
        ].startswith("Good")
        assert "guidelines" in result  # guidelines dict should be attached
        assert "related_metrics" in result  # and related_metrics too


# ---------------------------------------------------------------------------
# Metric registry helpers
# ---------------------------------------------------------------------------


def _yaml_metric_content(name: str) -> str:
    """Return YAML string for a very small metric definition."""

    return textwrap.dedent(
        f"""
        name: {name}
        description: Test metric {name}
        inputs: [x, y]
        formula: x / y
        tags: [t]
        units: ratio
        """
    )


class TestMetricRegistry:
    """Exercise MetricRegistry loading logic covering single & multi-metric YAML files."""

    def test_load_metrics_from_directory(self, tmp_path: Path):
        """Registry should discover, parse, and register YAML metrics."""
        # Arrange - create two YAML files
        single_metric_file = tmp_path / "single.yaml"
        multi_metric_file = tmp_path / "multi.yaml"

        single_metric_file.write_text(_yaml_metric_content("single_metric"))

        multi_defs = [
            yaml.safe_load(_yaml_metric_content("m1")),
            yaml.safe_load(_yaml_metric_content("m2")),
        ]
        multi_metric_file.write_text(yaml.safe_dump(multi_defs))

        registry = MetricRegistry()

        # Act
        loaded = registry.load_metrics_from_directory(tmp_path)

        # Assert - all three metrics should be present
        assert loaded == 3
        assert set(registry.list_metrics()) == {"single_metric", "m1", "m2"}
        for metric_id in registry.list_metrics():
            assert metric_id in registry  # __contains__
            # get() should return a MetricDefinition
            definition = registry.get(metric_id)
            assert definition.name.lower().replace(" ", "_") == metric_id

    def test_get_missing_metric_raises(self):
        registry = MetricRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")


# ---------------------------------------------------------------------------
# Standard node registry helpers
# ---------------------------------------------------------------------------


def _standard_nodes_fixture() -> dict[str, dict]:
    return {
        "revenue": {
            "category": "income_statement",
            "subcategory": "top_line",
            "description": "Total revenue",
            "alternate_names": ["sales", "turnover"],
            "sign_convention": "positive",
        },
        "treasury_stock": {
            "category": "balance_sheet_equity",
            "subcategory": "equity",
            "description": "Treasury stock held by company",
            "alternate_names": ["treasury_shares"],
            "sign_convention": "negative",
        },
    }


class TestStandardNodeRegistry:
    """Cover main public helpers of StandardNodeRegistry."""

    @pytest.fixture(scope="module")
    def registry(self):  # type: ignore[override]
        reg = StandardNodeRegistry()
        loaded = reg._load_nodes_from_data(_standard_nodes_fixture(), "unit-test-data")
        assert loaded == 2
        return reg

    def test_name_resolution_and_checks(self, registry: StandardNodeRegistry):
        assert registry.is_standard_name("revenue")
        assert registry.is_alternate_name("sales")
        assert registry.is_recognized_name("turnover")

        assert registry.get_standard_name("sales") == "revenue"
        assert registry.get_standard_name("revenue") == "revenue"
        assert registry.get_definition("treasury_shares").sign_convention == "negative"  # type: ignore[call-arg]

    def test_list_helpers(self, registry: StandardNodeRegistry):
        assert "income_statement" in registry.list_categories()
        assert "revenue" in registry.list_standard_names("income_statement")

    def test_validation_messages(self, registry: StandardNodeRegistry):
        ok, msg = registry.validate_node_name("sales")
        assert ok and "alternate" in msg

        ok, msg = registry.validate_node_name("turnover", strict=True)
        assert not ok and "alternate name" in msg

    def test_duplicate_detection(self):
        reg = StandardNodeRegistry()
        reg._load_nodes_from_data(_standard_nodes_fixture(), "first")
        # Attempting to load duplicates without overwrite should raise
        with pytest.raises(ValueError):
            reg._load_nodes_from_data(
                _standard_nodes_fixture(), "second", overwrite_existing=False
            )

        # With overwrite=True it should succeed and return same count
        count = reg._load_nodes_from_data(
            _standard_nodes_fixture(), "second", overwrite_existing=True
        )
        assert count == 2
