"""Tests for the calculate_metric helper function."""

import pytest
from fin_statement_model.core.metrics import calculate_metric
from fin_statement_model.core.nodes import FinancialStatementItemNode


class TestCalculateMetricHelper:
    """Test the calculate_metric helper function."""

    def test_basic_metric_calculation(self):
        """Test basic metric calculation with simple inputs."""
        # Create test nodes
        revenue = FinancialStatementItemNode("revenue", {"2023": 1000000})
        cogs = FinancialStatementItemNode("cost_of_goods_sold", {"2023": 600000})

        data_nodes = {
            "revenue": revenue,
            "cost_of_goods_sold": cogs,
        }

        # Calculate gross profit using helper
        result = calculate_metric("gross_profit", data_nodes, "2023")

        # Should be 1000000 - 600000 = 400000
        assert result == 400000.0

    def test_multiple_input_metric(self):
        """Test metric calculation with multiple inputs."""
        # Create test nodes for current ratio
        current_assets = FinancialStatementItemNode("current_assets", {"2023": 500000})
        current_liabilities = FinancialStatementItemNode(
            "current_liabilities", {"2023": 250000}
        )

        data_nodes = {
            "current_assets": current_assets,
            "current_liabilities": current_liabilities,
        }

        # Calculate current ratio using helper
        result = calculate_metric("current_ratio", data_nodes, "2023")

        # Should be 500000 / 250000 = 2.0
        assert result == 2.0

    def test_missing_metric_error(self):
        """Test error handling when metric is not found."""
        data_nodes = {"revenue": FinancialStatementItemNode("revenue", {"2023": 1000})}

        with pytest.raises(KeyError) as exc_info:
            calculate_metric("nonexistent_metric", data_nodes, "2023")

        assert "not found in registry" in str(exc_info.value)
        assert "Available metrics:" in str(exc_info.value)

    def test_missing_input_nodes_error(self):
        """Test error handling when required input nodes are missing."""
        # Only provide revenue, but gross_profit also needs cost_of_goods_sold
        data_nodes = {
            "revenue": FinancialStatementItemNode("revenue", {"2023": 1000000})
        }

        with pytest.raises(
            ValueError, match="Missing required input nodes"
        ) as exc_info:
            calculate_metric("gross_profit", data_nodes, "2023")

        assert "cost_of_goods_sold" in str(exc_info.value)

    def test_custom_node_name(self):
        """Test using a custom node name for the calculation."""
        revenue = FinancialStatementItemNode("revenue", {"2023": 1000000})
        cogs = FinancialStatementItemNode("cost_of_goods_sold", {"2023": 600000})

        data_nodes = {
            "revenue": revenue,
            "cost_of_goods_sold": cogs,
        }

        # Calculate with custom node name
        result = calculate_metric(
            "gross_profit", data_nodes, "2023", node_name="custom_gp"
        )

        # Result should be the same regardless of node name
        assert result == 400000.0

    def test_real_estate_metric(self):
        """Test calculation of a real estate specific metric."""
        # Test debt yield calculation
        noi = FinancialStatementItemNode("net_operating_income", {"2023": 1000000})
        debt = FinancialStatementItemNode("total_debt", {"2023": 10000000})

        data_nodes = {
            "net_operating_income": noi,
            "total_debt": debt,
        }

        result = calculate_metric("debt_yield", data_nodes, "2023")

        # Should be (1000000 / 10000000) * 100 = 10.0%
        assert result == 10.0

    def test_coverage_ratio_metric(self):
        """Test calculation of a coverage ratio metric."""
        # Test times interest earned (interest coverage ratio)
        ebit = FinancialStatementItemNode("ebit", {"2023": 500000})
        interest = FinancialStatementItemNode("interest_expense", {"2023": 100000})

        data_nodes = {
            "ebit": ebit,
            "interest_expense": interest,
        }

        result = calculate_metric("times_interest_earned", data_nodes, "2023")

        # Should be 500000 / 100000 = 5.0
        assert result == 5.0

    def test_percentage_metric(self):
        """Test calculation of a percentage-based metric."""
        # Test gross profit margin
        gross_profit = FinancialStatementItemNode("gross_profit", {"2023": 400000})
        revenue = FinancialStatementItemNode("revenue", {"2023": 1000000})

        data_nodes = {
            "gross_profit": gross_profit,
            "revenue": revenue,
        }

        result = calculate_metric("gross_profit_margin", data_nodes, "2023")

        # Should be (400000 / 1000000) * 100 = 40.0%
        assert result == 40.0
