"""Tests for the MarkdownNotesBuilder class."""

from unittest.mock import Mock
from datetime import datetime

from fin_statement_model.statements.formatting.markdown.notes import (
    MarkdownNotesBuilder,
)
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.adjustments.models import (
    Adjustment,
    AdjustmentFilter,
    AdjustmentType,
    DEFAULT_SCENARIO,
)


class TestMarkdownNotesBuilder:
    """Test cases for MarkdownNotesBuilder."""

    def test_build_notes_empty(self):
        """Test building notes with no forecast configs or adjustments."""
        builder = MarkdownNotesBuilder()
        mock_graph = Mock(spec=Graph)
        mock_graph.list_all_adjustments.return_value = []

        result = builder.build_notes(mock_graph)
        assert result == []

    def test_build_notes_with_forecast_only(self):
        """Test building notes with forecast configs only."""
        builder = MarkdownNotesBuilder()
        mock_graph = Mock(spec=Graph)
        mock_graph.list_all_adjustments.return_value = []

        forecast_configs = {
            "revenue": {"method": "simple", "config": 0.05},
            "expenses": {"method": "average"},
        }

        result = builder.build_notes(mock_graph, forecast_configs=forecast_configs)

        assert len(result) > 0
        assert "## Forecast Notes" in result
        assert any("revenue" in line for line in result)
        assert any("expenses" in line for line in result)

    def test_build_notes_with_adjustments_only(self):
        """Test building notes with adjustments only."""
        builder = MarkdownNotesBuilder()
        mock_graph = Mock(spec=Graph)

        # Create test adjustments
        adj1 = Adjustment(
            node_name="revenue",
            period="2023",
            type=AdjustmentType.ADDITIVE,
            value=1000.0,
            reason="Test adjustment",
            scenario=DEFAULT_SCENARIO,
            priority=0,
            tags={"test", "revenue"},
            timestamp=datetime.now(),
        )

        mock_graph.list_all_adjustments.return_value = [adj1]

        result = builder.build_notes(mock_graph)

        assert len(result) > 0
        assert "## Adjustment Notes (Matching Filter)" in result
        assert any("revenue" in line and "Test adjustment" in line for line in result)

    def test_build_forecast_notes_simple_method(self):
        """Test forecast notes for simple growth method."""
        builder = MarkdownNotesBuilder()

        forecast_configs = {"revenue": {"method": "simple", "config": 0.05}}

        result = builder._build_forecast_notes(forecast_configs)

        assert "## Forecast Notes" in result
        assert any("revenue" in line for line in result)
        assert any("simple growth rate: 5.0%" in line for line in result)

    def test_build_forecast_notes_curve_method(self):
        """Test forecast notes for curve method."""
        builder = MarkdownNotesBuilder()

        forecast_configs = {
            "revenue": {"method": "curve", "config": [0.05, 0.04, 0.03]}
        }

        result = builder._build_forecast_notes(forecast_configs)

        assert any(
            "specific growth rates: [5.0%, 4.0%, 3.0%]" in line for line in result
        )

    def test_build_forecast_notes_historical_growth(self):
        """Test forecast notes for historical growth method."""
        builder = MarkdownNotesBuilder()

        forecast_configs = {"revenue": {"method": "historical_growth"}}

        result = builder._build_forecast_notes(forecast_configs)

        assert any("based on average historical growth" in line for line in result)

    def test_build_forecast_notes_average_method(self):
        """Test forecast notes for average method."""
        builder = MarkdownNotesBuilder()

        forecast_configs = {"revenue": {"method": "average"}}

        result = builder._build_forecast_notes(forecast_configs)

        assert any("based on historical average value" in line for line in result)

    def test_build_forecast_notes_statistical_method(self):
        """Test forecast notes for statistical method."""
        builder = MarkdownNotesBuilder()

        forecast_configs = {
            "revenue": {
                "method": "statistical",
                "config": {
                    "distribution": "normal",
                    "params": {"mean": 1000.0, "std": 50.0},
                },
            }
        }

        result = builder._build_forecast_notes(forecast_configs)

        assert any("using 'normal' distribution" in line for line in result)
        assert any("mean=1000.000, std=50.000" in line for line in result)

    def test_build_forecast_notes_unknown_method(self):
        """Test forecast notes for unknown method."""
        builder = MarkdownNotesBuilder()

        forecast_configs = {"revenue": {"method": "unknown_method"}}

        result = builder._build_forecast_notes(forecast_configs)

        # Should just end with a period for unknown methods
        assert any(line.endswith("method 'unknown_method'.") for line in result)

    def test_build_adjustment_notes_empty(self):
        """Test adjustment notes with no adjustments."""
        builder = MarkdownNotesBuilder()
        mock_graph = Mock(spec=Graph)
        mock_graph.list_all_adjustments.return_value = []

        result = builder._build_adjustment_notes(mock_graph)
        assert result == []

    def test_build_adjustment_notes_with_multiple_adjustments(self):
        """Test adjustment notes with multiple adjustments."""
        builder = MarkdownNotesBuilder()
        mock_graph = Mock(spec=Graph)

        # Create test adjustments
        adj1 = Adjustment(
            node_name="revenue",
            period="2023",
            type=AdjustmentType.ADDITIVE,
            value=1000.0,
            reason="Revenue adjustment",
            scenario=DEFAULT_SCENARIO,
            priority=1,
            tags={"Q1", "revenue"},
            timestamp=datetime(2023, 1, 1),
        )

        adj2 = Adjustment(
            node_name="expenses",
            period="2023",
            type=AdjustmentType.MULTIPLICATIVE,
            value=0.10,
            reason="Expense adjustment",
            scenario="stress",
            priority=0,
            tags={"Q1", "expenses"},
            timestamp=datetime(2023, 1, 2),
        )

        mock_graph.list_all_adjustments.return_value = [adj1, adj2]

        # Default filter should only include DEFAULT_SCENARIO
        result = builder._build_adjustment_notes(mock_graph)

        assert "## Adjustment Notes (Matching Filter)" in result
        assert any(
            "revenue" in line and "Revenue adjustment" in line for line in result
        )
        # adj2 should be filtered out due to different scenario
        assert not any("expenses" in line for line in result)

    def test_build_adjustment_notes_sorting(self):
        """Test that adjustments are sorted correctly."""
        builder = MarkdownNotesBuilder()
        mock_graph = Mock(spec=Graph)

        # Create adjustments in non-sorted order
        adj1 = Adjustment(
            node_name="zeta",
            period="2024",
            type=AdjustmentType.ADDITIVE,
            value=100.0,
            reason="Test",
            scenario=DEFAULT_SCENARIO,
            priority=2,
            timestamp=datetime(2023, 1, 3),
        )

        adj2 = Adjustment(
            node_name="alpha",
            period="2023",
            type=AdjustmentType.ADDITIVE,
            value=200.0,
            reason="Test",
            scenario=DEFAULT_SCENARIO,
            priority=1,
            timestamp=datetime(2023, 1, 1),
        )

        mock_graph.list_all_adjustments.return_value = [adj1, adj2]

        result = builder._build_adjustment_notes(mock_graph)

        # Find the adjustment lines (skip header and empty lines)
        adj_lines = [line for line in result if line.startswith("- **")]

        # adj2 (alpha) should come before adj1 (zeta) due to node name sorting
        assert "alpha" in adj_lines[0]
        assert "zeta" in adj_lines[1]

    def test_filter_adjustments_with_adjustment_filter(self):
        """Test filtering adjustments with AdjustmentFilter."""
        builder = MarkdownNotesBuilder()

        adj1 = Adjustment(
            node_name="revenue",
            period="2023",
            type=AdjustmentType.ADDITIVE,
            value=100.0,
            reason="Test",
            scenario=DEFAULT_SCENARIO,
            tags={"Q1"},
            timestamp=datetime.now(),
        )

        adj2 = Adjustment(
            node_name="revenue",
            period="2023",
            type=AdjustmentType.ADDITIVE,
            value=200.0,
            reason="Test",
            scenario="stress",
            tags={"Q1"},
            timestamp=datetime.now(),
        )

        all_adjustments = [adj1, adj2]

        # Filter for default scenario only
        filter_obj = AdjustmentFilter(
            include_scenarios={DEFAULT_SCENARIO},
            period=None,
        )

        result = builder._filter_adjustments(all_adjustments, filter_obj)
        assert len(result) == 1
        assert result[0].scenario == DEFAULT_SCENARIO

    def test_filter_adjustments_with_tag_set(self):
        """Test filtering adjustments with tag set."""
        builder = MarkdownNotesBuilder()

        adj1 = Adjustment(
            node_name="revenue",
            period="2023",
            type=AdjustmentType.ADDITIVE,
            value=100.0,
            reason="Test",
            scenario=DEFAULT_SCENARIO,
            tags={"Q1", "revenue"},
            timestamp=datetime.now(),
        )

        adj2 = Adjustment(
            node_name="expenses",
            period="2023",
            type=AdjustmentType.ADDITIVE,
            value=200.0,
            reason="Test",
            scenario=DEFAULT_SCENARIO,
            tags={"Q2", "expenses"},
            timestamp=datetime.now(),
        )

        all_adjustments = [adj1, adj2]

        # Filter by tags
        tag_filter = {"Q1"}

        result = builder._filter_adjustments(all_adjustments, tag_filter)
        assert len(result) == 1
        assert "Q1" in result[0].tags

    def test_filter_adjustments_with_none(self):
        """Test filtering adjustments with None filter."""
        builder = MarkdownNotesBuilder()

        adj1 = Adjustment(
            node_name="revenue",
            period="2023",
            type=AdjustmentType.ADDITIVE,
            value=100.0,
            reason="Test",
            scenario=DEFAULT_SCENARIO,
            tags={"Q1"},
            timestamp=datetime.now(),
        )

        adj2 = Adjustment(
            node_name="revenue",
            period="2023",
            type=AdjustmentType.ADDITIVE,
            value=200.0,
            reason="Test",
            scenario="stress",
            tags={"Q1"},
            timestamp=datetime.now(),
        )

        all_adjustments = [adj1, adj2]

        # None filter should default to DEFAULT_SCENARIO only
        result = builder._filter_adjustments(all_adjustments, None)
        assert len(result) == 1
        assert result[0].scenario == DEFAULT_SCENARIO

    def test_build_notes_integration(self):
        """Test complete integration of forecast and adjustment notes."""
        builder = MarkdownNotesBuilder()
        mock_graph = Mock(spec=Graph)

        # Setup adjustments
        adj = Adjustment(
            node_name="revenue",
            period="2023",
            type=AdjustmentType.MULTIPLICATIVE,
            value=0.05,
            reason="Market conditions",
            scenario=DEFAULT_SCENARIO,
            priority=0,
            tags={"market"},
            timestamp=datetime.now(),
        )
        mock_graph.list_all_adjustments.return_value = [adj]

        # Setup forecast configs
        forecast_configs = {
            "revenue": {"method": "simple", "config": 0.10},
            "expenses": {"method": "historical_growth"},
        }

        # Build notes with filter
        tag_filter = {"market"}
        result = builder.build_notes(
            mock_graph,
            forecast_configs=forecast_configs,
            adjustment_filter=tag_filter,
        )

        # Should have both sections
        assert "## Forecast Notes" in result
        assert "## Adjustment Notes (Matching Filter)" in result

        # Check forecast content
        assert any(
            "revenue" in line and "simple growth rate: 10.0%" in line for line in result
        )
        assert any(
            "expenses" in line and "historical growth" in line for line in result
        )

        # Check adjustment content
        assert any("Market conditions" in line for line in result)
        # The adjustment type is now shown as "Multiplicative"
        assert any("Multiplicative adjustment of 0.05" in line for line in result)
