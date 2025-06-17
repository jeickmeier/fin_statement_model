"""Tests for the MarkdownStatementRenderer class."""

from unittest.mock import Mock

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.formats.markdown.renderer import MarkdownStatementRenderer
from fin_statement_model.statements.structure import (
    Section,
    StatementStructure,
    LineItem,
    CalculatedLineItem,
    SubtotalLineItem,
    MetricLineItem,
)


class TestMarkdownStatementRenderer:
    """Test cases for MarkdownStatementRenderer."""

    def test_init(self):
        """Test renderer initialization."""
        # Create mock graph
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = {"2023", "2024", "2022"}

        renderer = MarkdownStatementRenderer(mock_graph)
        assert renderer.graph == mock_graph
        assert renderer.indent_spaces == 4
        assert renderer.periods == ["2022", "2023", "2024"]  # Should be sorted

        # Test with custom indent
        renderer = MarkdownStatementRenderer(mock_graph, indent_spaces=2)
        assert renderer.indent_spaces == 2

    def test_render_structure_empty(self):
        """Test rendering empty structure."""
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = set()

        renderer = MarkdownStatementRenderer(mock_graph)

        # Empty structure - using correct initialization
        structure = StatementStructure(
            id="test_statement",
            name="Test Statement",
        )

        result = renderer.render_structure(structure)
        assert result == []

    def test_render_structure_with_sections(self):
        """Test rendering structure with sections."""
        # Setup mock graph
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = {"2023"}

        # Mock node and calculation
        mock_node = Mock()
        mock_node.calculate.return_value = 1000.0
        mock_graph.get_node.return_value = mock_node

        renderer = MarkdownStatementRenderer(mock_graph)

        # Create structure with items
        item1 = LineItem(
            id="revenue",
            name="Revenue",
            node_id="revenue_node",
        )

        section = Section(
            id="income",
            name="Income",
        )
        section.add_item(item1)

        structure = StatementStructure(
            id="test_statement",
            name="Test Statement",
        )
        structure.add_section(section)

        result = renderer.render_structure(structure)

        assert len(result) == 1
        assert result[0]["name"] == "Revenue"
        assert result[0]["level"] == 1
        assert result[0]["values"]["2023"] == 1000.0

    def test_render_section_nested(self):
        """Test rendering nested sections."""
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = {"2023"}

        renderer = MarkdownStatementRenderer(mock_graph)

        # Create nested sections
        inner_section = Section(
            id="inner",
            name="Inner",
        )

        outer_section = Section(
            id="outer",
            name="Outer",
        )
        outer_section.add_item(inner_section)

        # Render should handle nested sections
        result = renderer._render_section(outer_section, level=0)
        assert result == []  # Empty because no actual items

    def test_render_section_with_subtotal(self):
        """Test rendering section with subtotal."""
        # Setup mock graph
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = {"2023"}
        mock_graph.get_node.return_value = Mock()
        mock_graph.calculate.return_value = 500.0

        renderer = MarkdownStatementRenderer(mock_graph)

        # Create section with subtotal
        subtotal_item = SubtotalLineItem(
            id="total_revenue",
            name="Total Revenue",
            item_ids=["revenue1", "revenue2"],
        )

        section = Section(
            id="revenue_section",
            name="Revenue",
        )
        section.subtotal = subtotal_item

        result = renderer._render_section(section, level=0)

        assert len(result) == 1
        assert result[0]["name"] == "Total Revenue"
        assert result[0]["is_subtotal"] is True

    def test_render_item_line_item(self):
        """Test rendering basic LineItem."""
        # Setup mock graph
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = ["2023"]

        mock_node = Mock()
        mock_node.calculate.return_value = 1500.0
        mock_graph.get_node.return_value = mock_node

        renderer = MarkdownStatementRenderer(mock_graph)

        item = LineItem(
            id="sales",
            name="Sales",
            node_id="sales_node",
            sign_convention=-1,
            display_format=",.0f",
            units="USD",
            display_scale_factor=0.001,  # Convert to thousands
        )

        result = renderer._render_item(item, level=1)

        assert result is not None
        assert result["name"] == "Sales"
        assert result["level"] == 1
        assert result["is_subtotal"] is False
        assert result["sign_convention"] == -1
        assert result["display_format"] == ",.0f"
        assert result["units"] == "USD"
        assert result["display_scale_factor"] == 0.001
        # Value should be 1500 * -1 * 0.001 = -1.5
        assert result["values"]["2023"] == -1.5

    def test_render_item_calculated_line_item(self):
        """Test rendering CalculatedLineItem."""
        # Setup mock graph
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = ["2023"]
        mock_graph.get_node.return_value = Mock()
        mock_graph.calculate.return_value = 2000.0

        renderer = MarkdownStatementRenderer(mock_graph)

        item = CalculatedLineItem(
            id="gross_profit",
            name="Gross Profit",
            calculation={
                "type": "subtraction",
                "inputs": ["revenue", "cogs"],
            },
        )

        result = renderer._render_item(item, level=2)

        assert result is not None
        assert result["name"] == "Gross Profit"
        assert result["level"] == 2
        assert result["values"]["2023"] == 2000.0

    def test_render_item_metric_line_item(self):
        """Test rendering MetricLineItem."""
        # Setup mock graph
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = ["2023"]
        mock_graph.get_node.return_value = Mock()
        mock_graph.calculate.return_value = 0.35

        renderer = MarkdownStatementRenderer(mock_graph)

        item = MetricLineItem(
            id="gross_margin",
            name="Gross Margin",
            metric_id="gross_margin",
            inputs={"revenue": "revenue", "gross_profit": "gross_profit"},
            display_format=".1%",
        )

        result = renderer._render_item(item, level=1)

        assert result is not None
        assert result["name"] == "Gross Margin"
        assert result["values"]["2023"] == 0.35
        assert result["display_format"] == ".1%"

    def test_render_item_with_contra(self):
        """Test rendering contra item."""
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = ["2023"]

        mock_node = Mock()
        mock_node.calculate.return_value = -100.0
        mock_graph.get_node.return_value = mock_node

        renderer = MarkdownStatementRenderer(mock_graph)

        item = LineItem(
            id="returns",
            name="Sales Returns",
            node_id="returns_node",
            is_contra=True,
        )

        result = renderer._render_item(item, level=1)

        assert result is not None
        assert result["is_contra"] is True

    def test_render_item_exception_handling(self):
        """Test render_item handles exceptions gracefully."""
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = ["2023"]
        mock_graph.get_node.side_effect = Exception("Node error")

        renderer = MarkdownStatementRenderer(mock_graph)

        item = LineItem(
            id="test",
            name="Test",
            node_id="test_node",
        )

        result = renderer._render_item(item, level=1)

        # Should handle error gracefully and return item with ERROR values
        assert result is not None
        assert result["values"]["2023"] == "ERROR"

    def test_extract_values_no_node_id(self):
        """Test extract_values when node ID cannot be determined."""
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = ["2023"]

        renderer = MarkdownStatementRenderer(mock_graph)

        # LineItem with standard_node_ref instead of node_id
        item = LineItem(
            id="test",
            name="Test",
            standard_node_ref="revenue",
        )
        # Mock the get_resolved_node_id to return None
        item.get_resolved_node_id = Mock(return_value=None)

        values = renderer._extract_values(item)
        assert values == {"2023": None}

    def test_extract_values_calculation_error(self):
        """Test extract_values handles calculation errors."""
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = ["2023"]
        mock_graph.get_node.return_value = Mock()
        mock_graph.calculate.side_effect = Exception("Calc error")

        renderer = MarkdownStatementRenderer(mock_graph)

        item = CalculatedLineItem(
            id="test_calc",
            name="Test Calculation",
            calculation={
                "type": "addition",
                "inputs": ["a", "b"],
            },
        )

        values = renderer._extract_values(item)
        assert values["2023"] == "CALC_ERR"

    def test_extract_values_node_not_found(self):
        """Test extract_values when node is not found in graph."""
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = ["2023"]
        mock_graph.get_node.side_effect = KeyError("Node not found")

        renderer = MarkdownStatementRenderer(mock_graph)

        item = LineItem(
            id="test",
            name="Test",
            node_id="missing_node",
        )

        values = renderer._extract_values(item)
        assert values == {"2023": None}

    def test_get_node_id_line_item_with_node_id(self):
        """Test getting node ID from LineItem with node_id."""
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = []
        renderer = MarkdownStatementRenderer(mock_graph)

        item = LineItem(
            id="test",
            name="Test",
            node_id="explicit_node_id",
        )

        node_id = renderer._get_node_id(item)
        assert node_id == "explicit_node_id"

    def test_get_node_id_line_item_with_standard_ref(self):
        """Test getting node ID from LineItem with standard_node_ref."""
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = []
        renderer = MarkdownStatementRenderer(mock_graph)

        # Mock the standard node registry lookup
        item = LineItem(
            id="test",
            name="Test",
            standard_node_ref="revenue",
        )
        item.get_resolved_node_id = Mock(return_value="resolved_revenue_node")

        node_id = renderer._get_node_id(item)
        assert node_id == "resolved_revenue_node"

    def test_get_node_id_calculated_items(self):
        """Test getting node ID from calculated item types."""
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = []
        renderer = MarkdownStatementRenderer(mock_graph)

        # CalculatedLineItem uses its ID as node ID
        calc_item = CalculatedLineItem(
            id="gross_profit",
            name="Gross Profit",
            calculation={
                "type": "subtraction",
                "inputs": ["revenue", "cogs"],
            },
        )
        assert renderer._get_node_id(calc_item) == "gross_profit"

        # SubtotalLineItem uses its ID as node ID
        subtotal_item = SubtotalLineItem(
            id="total_revenue",
            name="Total Revenue",
            item_ids=["rev1", "rev2"],
        )
        assert renderer._get_node_id(subtotal_item) == "total_revenue"

        # MetricLineItem uses its ID as node ID
        metric_item = MetricLineItem(
            id="margin_metric",
            name="Margin",
            metric_id="gross_margin",
            inputs={"revenue": "revenue"},
        )
        assert renderer._get_node_id(metric_item) == "margin_metric"

    def test_apply_formatting_none_and_string(self):
        """Test apply_formatting with None and string values."""
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = []
        renderer = MarkdownStatementRenderer(mock_graph)

        item = LineItem(id="test", name="Test", node_id="test")

        # None should stay None
        assert renderer._apply_formatting(None, item) is None

        # Strings should stay as strings
        assert renderer._apply_formatting("ERROR", item) == "ERROR"
        assert renderer._apply_formatting("N/A", item) == "N/A"

    def test_apply_formatting_numeric(self):
        """Test apply_formatting with numeric values."""
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = []
        renderer = MarkdownStatementRenderer(mock_graph)

        # Test sign convention
        item = LineItem(
            id="test",
            name="Test",
            node_id="test",
            sign_convention=-1,
            display_scale_factor=1.0,
        )
        assert renderer._apply_formatting(100.0, item) == -100.0

        # Test scale factor
        item = LineItem(
            id="test",
            name="Test",
            node_id="test",
            sign_convention=1,
            display_scale_factor=0.001,  # Convert to thousands
        )
        assert renderer._apply_formatting(1000000.0, item) == 1000.0

        # Test both sign and scale
        item = LineItem(
            id="test",
            name="Test",
            node_id="test",
            sign_convention=-1,
            display_scale_factor=0.001,
        )
        assert renderer._apply_formatting(2000000.0, item) == -2000.0

    def test_render_structure_with_all_periods(self):
        """Test rendering with historical and forecast periods."""
        mock_graph = Mock(spec=Graph)
        mock_graph.periods = {"2022", "2023", "2024"}
        mock_graph.get_node.return_value = Mock()

        renderer = MarkdownStatementRenderer(mock_graph)

        structure = StatementStructure(
            id="test",
            name="Test",
        )

        # Test with period sets
        historical_periods = {"2022", "2023"}
        forecast_periods = {"2024"}

        renderer.render_structure(
            structure,
            historical_periods=historical_periods,
            forecast_periods=forecast_periods,
        )

        # The renderer itself doesn't use these sets, it just ensures all periods are processed
        assert renderer.periods == ["2022", "2023", "2024"]
