"""Tests for standard node name referencing feature.

This module tests the new functionality that allows statement configurations
to reference standard node names from the standard_node_registry instead of
always requiring exact graph node_ids.
"""

import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import standard_node_registry
from fin_statement_model.statements.configs.models import LineItemModel
from fin_statement_model.statements.configs.validator import StatementConfig
from fin_statement_model.statements.structure.items import LineItem
from fin_statement_model.statements.structure.builder import StatementStructureBuilder
from fin_statement_model.statements.population.id_resolver import IDResolver
from fin_statement_model.statements.structure import StatementStructure, Section
from fin_statement_model.statements.errors import StatementError
from pydantic import ValidationError


class TestLineItemModelValidation:
    """Test Pydantic validation for the new standard_node_ref field."""

    def test_node_id_only_valid(self) -> None:
        """Test that providing only node_id is valid."""
        model_data = {
            "type": "line_item",
            "id": "revenue",
            "name": "Revenue",
            "node_id": "revenue_data_node",
        }

        model = LineItemModel(**model_data)
        assert model.node_id == "revenue_data_node"
        assert model.standard_node_ref is None

    def test_standard_node_ref_only_valid(self) -> None:
        """Test that providing only standard_node_ref is valid."""
        model_data = {
            "type": "line_item",
            "id": "revenue",
            "name": "Revenue",
            "standard_node_ref": "revenue",
        }

        model = LineItemModel(**model_data)
        assert model.node_id is None
        assert model.standard_node_ref == "revenue"

    def test_neither_provided_raises_error(self) -> None:
        """Test that providing neither node_id nor standard_node_ref raises validation error."""
        model_data = {"type": "line_item", "id": "revenue", "name": "Revenue"}

        with pytest.raises(
            ValidationError,
            match="must provide either 'node_id' or 'standard_node_ref'",
        ):
            LineItemModel(**model_data)

    def test_both_provided_raises_error(self) -> None:
        """Test that providing both node_id and standard_node_ref raises validation error."""
        model_data = {
            "type": "line_item",
            "id": "revenue",
            "name": "Revenue",
            "node_id": "revenue_data_node",
            "standard_node_ref": "revenue",
        }

        with pytest.raises(
            ValidationError,
            match="cannot provide both 'node_id' and 'standard_node_ref'",
        ):
            LineItemModel(**model_data)


class TestLineItemCreation:
    """Test LineItem class with standard node references."""

    def test_create_with_node_id(self) -> None:
        """Test creating LineItem with direct node_id."""
        item = LineItem(id="revenue", name="Revenue", node_id="revenue_data_node")

        assert item.id == "revenue"
        assert item.name == "Revenue"
        assert item.node_id == "revenue_data_node"
        assert item.standard_node_ref is None

    def test_create_with_standard_node_ref(self) -> None:
        """Test creating LineItem with standard_node_ref."""
        item = LineItem(id="revenue", name="Revenue", standard_node_ref="revenue")

        assert item.id == "revenue"
        assert item.name == "Revenue"
        assert item.node_id is None
        assert item.standard_node_ref == "revenue"

    def test_create_with_neither_raises_error(self) -> None:
        """Test that creating LineItem with neither reference raises error."""
        with pytest.raises(StatementError, match=r"Must provide either"):
            LineItem(id="revenue", name="Revenue")

    def test_create_with_both_raises_error(self) -> None:
        """Test that creating LineItem with both references raises error."""
        with pytest.raises(StatementError, match=r"Cannot provide both"):
            LineItem(
                id="revenue",
                name="Revenue",
                node_id="revenue_data_node",
                standard_node_ref="revenue",
            )

    def test_get_resolved_node_id_with_direct_node_id(self) -> None:
        """Test that get_resolved_node_id returns direct node_id when available."""
        item = LineItem(id="revenue", name="Revenue", node_id="custom_revenue_node")

        resolved = item.get_resolved_node_id()
        assert resolved == "custom_revenue_node"

    def test_get_resolved_node_id_with_standard_ref(self) -> None:
        """Test that get_resolved_node_id resolves standard node reference."""
        # Mock some standard nodes in the registry for testing
        original_nodes = standard_node_registry._standard_nodes.copy()
        original_alternates = standard_node_registry._alternate_to_standard.copy()

        try:
            # Add a test standard node
            from fin_statement_model.core.nodes.standard_registry import (
                StandardNodeDefinition,
            )

            test_def = StandardNodeDefinition(
                category="income_statement",
                subcategory="revenue",
                description="Total revenue",
                alternate_names=["sales", "total_sales"],
            )
            standard_node_registry._standard_nodes["revenue"] = test_def
            standard_node_registry._alternate_to_standard["sales"] = "revenue"

            # Test direct standard name
            item = LineItem(id="revenue_item", name="Revenue", standard_node_ref="revenue")

            resolved = item.get_resolved_node_id()
            assert resolved == "revenue"

            # Test alternate name
            item_alt = LineItem(id="sales_item", name="Sales", standard_node_ref="sales")

            resolved_alt = item_alt.get_resolved_node_id()
            assert resolved_alt == "revenue"

        finally:
            # Restore original registry state
            standard_node_registry._standard_nodes = original_nodes
            standard_node_registry._alternate_to_standard = original_alternates


class TestIDResolverWithStandardNodes:
    """Test IDResolver functionality with standard node references."""

    def setup_method(self) -> None:
        """Set up test data for each test."""
        # Mock some standard nodes
        from fin_statement_model.core.nodes.standard_registry import (
            StandardNodeDefinition,
        )

        self.original_nodes = standard_node_registry._standard_nodes.copy()
        self.original_alternates = standard_node_registry._alternate_to_standard.copy()

        # Add test standard nodes
        revenue_def = StandardNodeDefinition(
            category="income_statement",
            subcategory="revenue",
            description="Total revenue",
            alternate_names=["sales", "total_sales"],
        )
        cogs_def = StandardNodeDefinition(
            category="income_statement",
            subcategory="costs",
            description="Cost of goods sold",
            alternate_names=["cost_of_sales"],
        )

        standard_node_registry._standard_nodes["revenue"] = revenue_def
        standard_node_registry._standard_nodes["cost_of_goods_sold"] = cogs_def
        standard_node_registry._alternate_to_standard["sales"] = "revenue"
        standard_node_registry._alternate_to_standard["cost_of_sales"] = "cost_of_goods_sold"

    def teardown_method(self) -> None:
        """Clean up after each test."""
        standard_node_registry._standard_nodes = self.original_nodes
        standard_node_registry._alternate_to_standard = self.original_alternates

    def test_id_resolver_caches_standard_node_refs(self) -> None:
        """Test that IDResolver properly caches standard node references."""
        # Create statement with standard node references
        statement = StatementStructure(id="test", name="Test Statement")
        section = Section(id="revenue_section", name="Revenue")

        revenue_item = LineItem(id="revenue_item", name="Revenue", standard_node_ref="revenue")

        cogs_item = LineItem(
            id="cogs_item",
            name="COGS",
            standard_node_ref="cost_of_sales",  # Alternate name
        )

        section.add_item(revenue_item)
        section.add_item(cogs_item)
        statement.add_section(section)

        # Create resolver and test resolution
        resolver = IDResolver(statement)

        # Test resolving standard node reference
        assert resolver.resolve("revenue_item") == "revenue"

        # Test resolving alternate name
        assert resolver.resolve("cogs_item") == "cost_of_goods_sold"

        # Test batch resolution
        batch_result = resolver.resolve_multiple(["revenue_item", "cogs_item"])
        assert batch_result["revenue_item"] == "revenue"
        assert batch_result["cogs_item"] == "cost_of_goods_sold"

    def test_id_resolver_mixed_node_references(self) -> None:
        """Test IDResolver with mix of direct node_ids and standard references."""
        statement = StatementStructure(id="test", name="Test Statement")
        section = Section(id="mixed_section", name="Mixed")

        # Direct node_id
        item1 = LineItem(id="custom_item", name="Custom Item", node_id="custom_node_123")

        # Standard node reference
        item2 = LineItem(id="standard_item", name="Standard Item", standard_node_ref="revenue")

        section.add_item(item1)
        section.add_item(item2)
        statement.add_section(section)

        resolver = IDResolver(statement)

        assert resolver.resolve("custom_item") == "custom_node_123"
        assert resolver.resolve("standard_item") == "revenue"

    def test_id_resolver_unresolvable_standard_ref(self) -> None:
        """Test IDResolver behavior with unresolvable standard references."""
        statement = StatementStructure(id="test", name="Test Statement")
        section = Section(id="bad_section", name="Bad Section")

        # Reference to non-existent standard node
        bad_item = LineItem(
            id="bad_item",
            name="Bad Item",
            standard_node_ref="nonexistent_standard_node",
        )

        section.add_item(bad_item)
        statement.add_section(section)

        # This should not crash but should log a warning
        resolver = IDResolver(statement)

        # The item should map to the unresolved standard name
        # (since standard_node_registry.get_standard_name returns the original name if not found)
        assert resolver.resolve("bad_item") == "nonexistent_standard_node"


class TestStatementStructureBuilderIntegration:
    """Test integration with StatementStructureBuilder."""

    def setup_method(self) -> None:
        """Set up test data."""
        from fin_statement_model.core.nodes.standard_registry import (
            StandardNodeDefinition,
        )

        self.original_nodes = standard_node_registry._standard_nodes.copy()
        self.original_alternates = standard_node_registry._alternate_to_standard.copy()

        # Add test standard node
        revenue_def = StandardNodeDefinition(
            category="income_statement",
            subcategory="revenue",
            description="Total revenue",
            alternate_names=["sales"],
        )
        standard_node_registry._standard_nodes["revenue"] = revenue_def
        standard_node_registry._alternate_to_standard["sales"] = "revenue"

    def teardown_method(self) -> None:
        """Clean up after test."""
        standard_node_registry._standard_nodes = self.original_nodes
        standard_node_registry._alternate_to_standard = self.original_alternates

    def test_builder_handles_standard_node_ref(self) -> None:
        """Test that StatementStructureBuilder properly handles standard_node_ref."""
        config_data = {
            "id": "test_statement",
            "name": "Test Statement",
            "sections": [
                {
                    "type": "section",
                    "id": "revenue_section",
                    "name": "Revenue Section",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "revenue_item",
                            "name": "Revenue",
                            "standard_node_ref": "revenue",
                        },
                        {
                            "type": "line_item",
                            "id": "sales_item",
                            "name": "Sales",
                            "standard_node_ref": "sales",  # Alternate name
                        },
                    ],
                }
            ],
        }

        config = StatementConfig(config_data)
        validation_errors = config.validate_config()
        assert validation_errors == []

        builder = StatementStructureBuilder()
        statement = builder.build(config)

        # Verify the built structure
        assert statement.id == "test_statement"
        assert len(statement.sections) == 1

        section = statement.sections[0]
        assert len(section.items) == 2

        revenue_item = section.items[0]
        assert isinstance(revenue_item, LineItem)
        assert revenue_item.id == "revenue_item"
        assert revenue_item.standard_node_ref == "revenue"
        assert revenue_item.node_id is None

        sales_item = section.items[1]
        assert isinstance(sales_item, LineItem)
        assert sales_item.id == "sales_item"
        assert sales_item.standard_node_ref == "sales"
        assert sales_item.node_id is None


class TestEndToEndFunctionality:
    """Test complete end-to-end functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        from fin_statement_model.core.nodes.standard_registry import (
            StandardNodeDefinition,
        )

        self.original_nodes = standard_node_registry._standard_nodes.copy()
        self.original_alternates = standard_node_registry._alternate_to_standard.copy()

        # Add comprehensive test nodes
        test_nodes = {
            "revenue": StandardNodeDefinition(
                category="income_statement",
                subcategory="revenue",
                description="Total revenue",
                alternate_names=["sales", "total_sales"],
            ),
            "cost_of_goods_sold": StandardNodeDefinition(
                category="income_statement",
                subcategory="costs",
                description="Cost of goods sold",
                alternate_names=["cogs", "cost_of_sales"],
            ),
            "cash": StandardNodeDefinition(
                category="balance_sheet_assets",
                subcategory="current_assets",
                description="Cash and cash equivalents",
                alternate_names=["cash_and_equivalents"],
            ),
        }

        for name, definition in test_nodes.items():
            standard_node_registry._standard_nodes[name] = definition
            for alt_name in definition.alternate_names:
                standard_node_registry._alternate_to_standard[alt_name] = name

    def teardown_method(self) -> None:
        """Clean up test environment."""
        standard_node_registry._standard_nodes = self.original_nodes
        standard_node_registry._alternate_to_standard = self.original_alternates

    def test_complete_workflow_with_standard_refs(self) -> None:
        """Test complete workflow from config to graph population."""
        # Create a graph with standard-named nodes
        graph = Graph()
        graph.add_financial_statement_item("revenue", {"2023": 1000, "2024": 1200})
        graph.add_financial_statement_item("cost_of_goods_sold", {"2023": 600, "2024": 700})

        # Create config using standard node references
        config_data = {
            "id": "income_statement",
            "name": "Income Statement",
            "sections": [
                {
                    "type": "section",
                    "id": "revenue_section",
                    "name": "Revenue",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "total_revenue",
                            "name": "Total Revenue",
                            "standard_node_ref": "sales",  # Using alternate name
                        }
                    ],
                },
                {
                    "type": "section",
                    "id": "costs_section",
                    "name": "Costs",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "cogs",
                            "name": "Cost of Goods Sold",
                            "standard_node_ref": "cost_of_goods_sold",  # Direct standard name
                        },
                        {
                            "type": "calculated",
                            "id": "gross_profit",
                            "name": "Gross Profit",
                            "calculation": {
                                "type": "subtraction",
                                "inputs": ["total_revenue", "cogs"],
                            },
                        },
                    ],
                },
            ],
        }

        # Build and validate
        config = StatementConfig(config_data)
        validation_errors = config.validate_config()
        assert validation_errors == []

        builder = StatementStructureBuilder()
        statement = builder.build(config)

        # Test ID resolution
        resolver = IDResolver(statement)

        # Should resolve standard reference to standard name
        assert resolver.resolve("total_revenue") == "revenue"  # "sales" -> "revenue"
        assert resolver.resolve("cogs") == "cost_of_goods_sold"
        assert resolver.resolve("gross_profit") == "gross_profit"  # Calculated item uses its own ID

        # Test with graph context
        assert resolver.resolve("total_revenue", graph) == "revenue"

        # The graph has "revenue" node, which matches the resolved standard name
        assert graph.has_node("revenue")
        assert graph.has_node("cost_of_goods_sold")

    def test_mixed_standard_and_custom_refs(self) -> None:
        """Test mixing standard node references with custom node_ids."""
        config_data = {
            "id": "mixed_statement",
            "name": "Mixed Statement",
            "sections": [
                {
                    "type": "section",
                    "id": "mixed_section",
                    "name": "Mixed Section",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "standard_item",
                            "name": "Standard Revenue",
                            "standard_node_ref": "revenue",
                        },
                        {
                            "type": "line_item",
                            "id": "custom_item",
                            "name": "Custom Revenue Stream",
                            "node_id": "custom_revenue_stream_node",
                        },
                    ],
                }
            ],
        }

        config = StatementConfig(config_data)
        validation_errors = config.validate_config()
        assert validation_errors == []

        builder = StatementStructureBuilder()
        statement = builder.build(config)

        resolver = IDResolver(statement)

        assert resolver.resolve("standard_item") == "revenue"
        assert resolver.resolve("custom_item") == "custom_revenue_stream_node"

    def test_fallback_strategy_for_non_standard_graphs(self) -> None:
        """Test behavior when graph doesn't use standard node names."""
        # Create config using standard references
        config_data = {
            "id": "fallback_test",
            "name": "Fallback Test",
            "sections": [
                {
                    "type": "section",
                    "id": "test_section",
                    "name": "Test Section",
                    "items": [
                        {
                            "type": "line_item",
                            "id": "revenue_item",
                            "name": "Revenue",
                            "standard_node_ref": "revenue",
                        }
                    ],
                }
            ],
        }

        config = StatementConfig(config_data)
        validation_errors = config.validate_config()
        assert validation_errors == []

        builder = StatementStructureBuilder()
        statement = builder.build(config)

        # Create graph that doesn't use standard names
        graph = Graph()
        graph.add_financial_statement_item("company_revenue_2024", {"2024": 1000})

        resolver = IDResolver(statement)

        # Should resolve to the standard name even if graph doesn't have it
        assert resolver.resolve("revenue_item") == "revenue"

        # Graph doesn't have standard node name
        assert not graph.has_node("revenue")
        assert graph.has_node("company_revenue_2024")

        # This demonstrates the need for explicit mapping when graph doesn't use standard names
        # In practice, users would either:
        # 1. Use node_id pointing to "company_revenue_2024"
        # 2. Rename their graph nodes to use standard names
        # 3. Add a mapping layer (future enhancement)


if __name__ == "__main__":
    pytest.main([__file__])
