"""Unit tests for the stats module."""

import pytest
import statistics
import math
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.core.stats import YoYGrowthNode, MultiPeriodStatNode


class TestYoYGrowthNode:
    """Test cases for YoYGrowthNode."""

    def test_positive_growth(self):
        """Test calculation of positive growth rate."""
        # Arrange
        revenue = FinancialStatementItemNode("revenue", {
            "2021": 1000.0,
            "2022": 1200.0
        })
        growth_node = YoYGrowthNode("revenue_growth", revenue, "2021", "2022")

        # Act
        result = growth_node.calculate()

        # Assert
        assert result == 0.2  # 20% growth

    def test_negative_growth(self):
        """Test calculation of negative growth rate."""
        # Arrange
        revenue = FinancialStatementItemNode("revenue", {
            "2021": 1000.0,
            "2022": 800.0
        })
        growth_node = YoYGrowthNode("revenue_growth", revenue, "2021", "2022")

        # Act
        result = growth_node.calculate()

        # Assert
        assert result == -0.2  # -20% growth

    def test_zero_prior_period(self):
        """Test handling of zero prior period value."""
        # Arrange
        revenue = FinancialStatementItemNode("revenue", {
            "2021": 0.0,
            "2022": 1000.0
        })
        growth_node = YoYGrowthNode("revenue_growth", revenue, "2021", "2022")

        # Act
        result = growth_node.calculate()

        # Assert
        assert math.isnan(result)

    def test_ignores_period_parameter(self):
        """Test that the period parameter is ignored in calculate()."""
        # Arrange
        revenue = FinancialStatementItemNode("revenue", {
            "2021": 1000.0,
            "2022": 1200.0
        })
        growth_node = YoYGrowthNode("revenue_growth", revenue, "2021", "2022")

        # Act
        result1 = growth_node.calculate()
        result2 = growth_node.calculate("2022")

        # Assert
        assert result1 == result2 == 0.2


class TestMultiPeriodStatNode:
    """Test cases for MultiPeriodStatNode."""

    def test_standard_deviation_calculation(self):
        """Test calculation of standard deviation across periods."""
        # Arrange
        revenue = FinancialStatementItemNode("revenue", {
            "2020": 1000.0,
            "2021": 1200.0,
            "2022": 1100.0
        })
        stat_node = MultiPeriodStatNode(
            "revenue_volatility",
            revenue,
            ["2020", "2021", "2022"]
        )

        # Act
        result = stat_node.calculate()

        # Assert
        expected = statistics.stdev([1000.0, 1200.0, 1100.0])
        assert result == expected

    def test_custom_stat_function(self):
        """Test using a custom statistical function."""
        # Arrange
        revenue = FinancialStatementItemNode("revenue", {
            "2020": 1000.0,
            "2021": 1200.0,
            "2022": 1100.0
        })
        stat_node = MultiPeriodStatNode(
            "revenue_mean",
            revenue,
            ["2020", "2021", "2022"],
            stat_func=statistics.mean
        )

        # Act
        result = stat_node.calculate()

        # Assert
        expected = statistics.mean([1000.0, 1200.0, 1100.0])
        assert result == expected

    def test_insufficient_periods(self):
        """Test handling of insufficient periods for statistical calculation."""
        # Arrange
        revenue = FinancialStatementItemNode("revenue", {
            "2020": 1000.0
        })
        stat_node = MultiPeriodStatNode(
            "revenue_volatility",
            revenue,
            ["2020"]
        )

        # Act
        result = stat_node.calculate()

        # Assert
        assert math.isnan(result)

    def test_ignores_period_parameter(self):
        """Test that the period parameter is ignored in calculate()."""
        # Arrange
        revenue = FinancialStatementItemNode("revenue", {
            "2020": 1000.0,
            "2021": 1200.0,
            "2022": 1100.0
        })
        stat_node = MultiPeriodStatNode(
            "revenue_volatility",
            revenue,
            ["2020", "2021", "2022"]
        )

        # Act
        result1 = stat_node.calculate()
        result2 = stat_node.calculate("2022")

        # Assert
        assert result1 == result2 