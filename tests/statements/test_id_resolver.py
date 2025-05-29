"""Tests for the IDResolver class.

This module tests the centralized ID resolution logic that maps statement
item IDs to graph node IDs, handling the complexity of different item types
having different ID mapping rules.
"""

from unittest.mock import Mock

from fin_statement_model.core.graph import Graph
from fin_statement_model.statements.structure import (
    StatementStructure,
    Section,
    LineItem,
    CalculatedLineItem,
    SubtotalLineItem,
    MetricLineItem,
)
from fin_statement_model.statements.population.id_resolver import IDResolver


class TestIDResolver:
    """Test the IDResolver class."""

    def setup_method(self):
        """Set up test data."""
        # Create a statement structure with various item types
        self.statement = StatementStructure(id="test_statement", name="Test Statement")

        # Create a section
        section = Section(id="section1", name="Section 1")

        # Add different types of items
        # LineItem - has separate node_id
        section.add_item(LineItem(id="revenue", name="Revenue", node_id="revenue_node"))

        # CalculatedLineItem - uses its ID as node_id
        section.add_item(
            CalculatedLineItem(
                id="gross_profit",
                name="Gross Profit",
                calculation={"type": "subtraction", "inputs": ["revenue", "cogs"]},
            )
        )

        # SubtotalLineItem - uses its ID as node_id
        section.add_item(
            SubtotalLineItem(
                id="total_revenue",
                name="Total Revenue",
                item_ids=["revenue", "other_revenue"],
            )
        )

        # MetricLineItem - uses its ID as node_id
        section.add_item(
            MetricLineItem(
                id="revenue_growth",
                name="Revenue Growth",
                metric_id="growth_rate",
                inputs={"current": "revenue", "previous": "prior_revenue"},
            )
        )

        self.statement.add_section(section)

        # Create ID resolver
        self.resolver = IDResolver(self.statement)

    def test_resolve_line_item(self):
        """Test resolving LineItem ID to its node_id."""
        # LineItem 'revenue' should resolve to 'revenue_node'
        node_id = self.resolver.resolve("revenue")
        assert node_id == "revenue_node"

    def test_resolve_calculated_item(self):
        """Test resolving CalculatedLineItem ID."""
        # CalculatedLineItem uses its ID directly
        node_id = self.resolver.resolve("gross_profit")
        assert node_id == "gross_profit"

    def test_resolve_subtotal_item(self):
        """Test resolving SubtotalLineItem ID."""
        # SubtotalLineItem uses its ID directly
        node_id = self.resolver.resolve("total_revenue")
        assert node_id == "total_revenue"

    def test_resolve_metric_item(self):
        """Test resolving MetricLineItem ID."""
        # MetricLineItem uses its ID directly
        node_id = self.resolver.resolve("revenue_growth")
        assert node_id == "revenue_growth"

    def test_resolve_nonexistent_item(self):
        """Test resolving an item that doesn't exist in statement."""
        node_id = self.resolver.resolve("nonexistent")
        assert node_id is None

    def test_resolve_with_graph_fallback(self):
        """Test resolving an item that exists directly in graph."""
        # Create a mock graph
        graph = Mock(spec=Graph)
        graph.has_node.side_effect = lambda x: x == "external_node"

        # Item not in statement but exists in graph
        node_id = self.resolver.resolve("external_node", graph)
        assert node_id == "external_node"

        # Verify it was cached
        assert "external_node" in self.resolver._item_to_node_cache

    def test_resolve_multiple(self):
        """Test resolving multiple IDs at once."""
        item_ids = ["revenue", "gross_profit", "nonexistent"]

        results = self.resolver.resolve_multiple(item_ids)

        assert results == {
            "revenue": "revenue_node",
            "gross_profit": "gross_profit",
            "nonexistent": None,
        }

    def test_get_items_for_node(self):
        """Test reverse lookup - get items that map to a node."""
        # revenue_node is mapped from 'revenue' item
        items = self.resolver.get_items_for_node("revenue_node")
        assert items == ["revenue"]

        # gross_profit node is mapped from 'gross_profit' item
        items = self.resolver.get_items_for_node("gross_profit")
        assert items == ["gross_profit"]

        # Nonexistent node
        items = self.resolver.get_items_for_node("nonexistent_node")
        assert items == []

    def test_get_all_mappings(self):
        """Test getting all ID mappings."""
        mappings = self.resolver.get_all_mappings()

        assert mappings == {
            "revenue": "revenue_node",
            "gross_profit": "gross_profit",
            "total_revenue": "total_revenue",
            "revenue_growth": "revenue_growth",
        }

    def test_cache_invalidation(self):
        """Test cache invalidation and refresh."""
        # Initial resolution
        assert self.resolver.resolve("revenue") == "revenue_node"

        # Invalidate cache
        self.resolver.invalidate_cache()
        assert len(self.resolver._item_to_node_cache) == 0
        assert len(self.resolver._node_to_items_cache) == 0

        # Resolution should still work (rebuilds cache)
        assert self.resolver.resolve("revenue") == "revenue_node"
        assert len(self.resolver._item_to_node_cache) > 0

    def test_refresh_cache(self):
        """Test cache refresh."""
        initial_cache_size = len(self.resolver._item_to_node_cache)

        # Refresh cache
        self.resolver.refresh_cache()

        # Cache should be rebuilt with same size
        assert len(self.resolver._item_to_node_cache) == initial_cache_size

    def test_nested_sections(self):
        """Test ID resolution with nested sections."""
        # Create a nested structure
        statement = StatementStructure(id="nested", name="Nested Statement")

        parent_section = Section(id="parent", name="Parent")
        child_section = Section(id="child", name="Child")

        # Add item to child section
        child_section.add_item(
            LineItem(id="nested_item", name="Nested Item", node_id="nested_node")
        )

        parent_section.add_item(child_section)
        statement.add_section(parent_section)

        # Create resolver for nested structure
        resolver = IDResolver(statement)

        # Should resolve nested item
        assert resolver.resolve("nested_item") == "nested_node"
