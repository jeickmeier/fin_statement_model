"""Tests for statement formatter with adjustment functionality."""

from fin_statement_model.core.graph import Graph
from fin_statement_model.statements.formatting.formatter import StatementFormatter
from fin_statement_model.statements.structure import (
    StatementStructure,
    Section,
    LineItem,
    SubtotalLineItem,
)
from fin_statement_model.core.adjustments.models import (
    AdjustmentType,
    AdjustmentFilter,
)


class TestStatementFormatterAdjustments:
    """Test the StatementFormatter with adjustment functionality."""

    def setup_method(self):
        """Set up test data."""
        # Create a simple statement structure
        self.statement = StatementStructure(
            id="test_statement",
            name="Test Statement",
            description="Test statement for formatter",
        )

        # Add a section with items
        section = Section(id="revenue_section", name="Revenue")
        section.add_item(
            LineItem(
                id="product_revenue",
                name="Product Revenue",
                node_id="product_revenue_node",
            )
        )
        section.add_item(
            LineItem(
                id="service_revenue",
                name="Service Revenue",
                node_id="service_revenue_node",
            )
        )
        section.add_item(
            SubtotalLineItem(
                id="total_revenue",
                name="Total Revenue",
                item_ids=["product_revenue", "service_revenue"],
            )
        )
        self.statement.add_section(section)

        # Create a graph with test data
        self.graph = Graph()
        self.graph.add_financial_statement_item(
            "product_revenue_node",
            {"2023Q1": 1000, "2023Q2": 1100, "2023Q3": 1200},
        )
        self.graph.add_financial_statement_item(
            "service_revenue_node",
            {"2023Q1": 500, "2023Q2": 550, "2023Q3": 600},
        )

        # Add adjustments to product revenue
        self.graph.add_adjustment(
            node_name="product_revenue_node",
            period="2023Q2",
            value=100,
            reason="Seasonal adjustment",
            adj_type=AdjustmentType.ADDITIVE,
            tags={"forecast"},
            # Note: scenario defaults to "default" if not specified
        )

        # Add the total revenue calculation
        self.graph.add_calculation(
            name="total_revenue",
            input_names=["product_revenue_node", "service_revenue_node"],
            operation_type="addition",
        )

        # Create formatter
        self.formatter = StatementFormatter(self.statement)

    def test_generate_dataframe_with_adjustments(self):
        """Test generating DataFrame with adjustment filter."""
        # Create adjustment filter that includes our tags
        filter_input = AdjustmentFilter(
            include_tags={"forecast"},
        )

        # Generate DataFrame with adjustments
        df = self.formatter.generate_dataframe(
            graph=self.graph,
            adjustment_filter=filter_input,
            include_empty_items=False,
        )

        # Check structure
        assert len(df) == 3  # 2 line items + 1 subtotal
        assert list(df.columns[:2]) == ["Line Item", "ID"]
        assert "2023Q1" in df.columns
        assert "2023Q2" in df.columns
        assert "2023Q3" in df.columns

        # Check values - Q2 product revenue should be adjusted
        product_row = df[df["ID"] == "product_revenue"].iloc[0]
        assert product_row["2023Q1"] == "1,000.00"
        assert product_row["2023Q2"] == "1,200.00"  # 1100 + 100 adjustment
        assert product_row["2023Q3"] == "1,200.00"

        # Check total is calculated with base values (adjustments don't propagate through calculations)
        total_row = df[df["ID"] == "total_revenue"].iloc[0]
        assert total_row["2023Q2"] == "1,650.00"  # 1100 + 550 (base values)

    def test_generate_dataframe_with_is_adjusted_column(self):
        """Test generating DataFrame with is_adjusted indicator columns."""
        # Create adjustment filter
        filter_input = AdjustmentFilter(
            include_tags={"forecast"},
        )

        # Generate DataFrame with is_adjusted columns
        df = self.formatter.generate_dataframe(
            graph=self.graph,
            adjustment_filter=filter_input,
            add_is_adjusted_column=True,
        )

        # Check that is_adjusted columns exist
        assert "2023Q1_is_adjusted" in df.columns
        assert "2023Q2_is_adjusted" in df.columns
        assert "2023Q3_is_adjusted" in df.columns

        # Check is_adjusted values for product revenue
        product_row = df[df["ID"] == "product_revenue"].iloc[0]
        assert not product_row["2023Q1_is_adjusted"]
        assert product_row["2023Q2_is_adjusted"]  # Has adjustment
        assert not product_row["2023Q3_is_adjusted"]

        # Check is_adjusted values for service revenue (no adjustments)
        service_row = df[df["ID"] == "service_revenue"].iloc[0]
        assert not service_row["2023Q1_is_adjusted"]
        assert not service_row["2023Q2_is_adjusted"]
        assert not service_row["2023Q3_is_adjusted"]

        # Calculated items should always be False
        total_row = df[df["ID"] == "total_revenue"].iloc[0]
        assert not total_row["2023Q1_is_adjusted"]
        assert not total_row["2023Q2_is_adjusted"]
        assert not total_row["2023Q3_is_adjusted"]

    def test_generate_dataframe_without_adjustments(self):
        """Test generating DataFrame without applying adjustments."""
        # Create a filter that excludes all adjustments
        filter_input = AdjustmentFilter(
            include_scenarios=set(),  # Empty set means no scenarios
        )
        # Generate DataFrame without adjustments
        df = self.formatter.generate_dataframe(
            graph=self.graph,
            adjustment_filter=filter_input,
            include_empty_items=False,
        )

        # Check values - should get base values without adjustments
        product_row = df[df["ID"] == "product_revenue"].iloc[0]
        assert product_row["2023Q1"] == "1,000.00"
        assert product_row["2023Q2"] == "1,100.00"  # Base value, no adjustment
        assert product_row["2023Q3"] == "1,200.00"

    def test_generate_dataframe_with_default_adjustments(self):
        """Test generating DataFrame with default adjustments (None filter)."""
        # Generate DataFrame with None filter (applies default scenario)
        df = self.formatter.generate_dataframe(
            graph=self.graph,
            adjustment_filter=None,
            include_empty_items=False,
        )

        # Check values - should get adjusted values from default scenario
        product_row = df[df["ID"] == "product_revenue"].iloc[0]
        assert product_row["2023Q1"] == "1,000.00"
        assert (
            product_row["2023Q2"] == "1,200.00"
        )  # 1100 + 100 adjustment (default scenario)
        assert product_row["2023Q3"] == "1,200.00"

    def test_generate_dataframe_with_metadata_columns(self):
        """Test including metadata columns in output."""
        df = self.formatter.generate_dataframe(
            graph=self.graph,
            include_metadata_cols=True,
        )

        # Check metadata columns exist
        assert "line_type" in df.columns
        assert "node_id" in df.columns
        assert "sign_convention" in df.columns
        assert "is_subtotal" in df.columns
        assert "is_calculated" in df.columns

        # Check metadata values
        product_row = df[df["ID"] == "product_revenue"].iloc[0]
        assert product_row["line_type"] == "item"
        assert product_row["node_id"] == "product_revenue_node"
        assert product_row["sign_convention"] == 1
        assert not product_row["is_subtotal"]
        assert not product_row["is_calculated"]

        total_row = df[df["ID"] == "total_revenue"].iloc[0]
        assert total_row["line_type"] == "subtotal"
        assert total_row["is_subtotal"]

    def test_format_html_with_adjustments(self):
        """Test HTML formatting with adjustments."""
        html = self.formatter.format_html(
            graph=self.graph,
            should_apply_signs=True,
            include_empty_items=False,
        )

        # Basic checks - should contain table and values
        assert "<table" in html
        assert "Product Revenue" in html
        assert "1,000.00" in html  # Q1 value

    def test_empty_graph_periods(self):
        """Test handling when graph has no periods."""
        empty_graph = Graph()
        df = self.formatter.generate_dataframe(graph=empty_graph)

        # Should return empty DataFrame with basic columns
        assert len(df) == 0
        assert list(df.columns) == ["Line Item", "ID"]
