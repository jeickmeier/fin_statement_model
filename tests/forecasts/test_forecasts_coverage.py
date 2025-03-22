"""Unit tests to increase coverage for the forecasts module.

This module contains additional test cases for the forecasts module to achieve 100% code coverage.
These tests focus on specific methods and edge cases not covered by the main test suite.
"""

import pytest
from unittest.mock import Mock, patch
import logging

from fin_statement_model.forecasts.forecasts import (
    AverageValueForecastNode,
    AverageHistoricalGrowthForecastNode
)


class TestAverageValueForecastNodeCoverage:
    """Additional tests for AverageValueForecastNode for coverage."""
    
    @pytest.fixture
    def mock_input_node(self):
        """Create a mock input node with historical values."""
        node = Mock()
        node.name = "test_node"
        node.values = {
            "FY2020": 100.0,
            "FY2021": 110.0,
            "FY2022": 120.0
        }
        node.calculate = lambda period: node.values.get(period, 0.0)
        return node
    
    def test_growth_factor_method(self, mock_input_node):
        """Test the _get_growth_factor_for_period method that's not used in this class.
        
        This tests line 357 in forecasts.py.
        """
        forecast = AverageValueForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            115.0
        )
        
        # The method should return 0.0 as it's not used for average value forecasts
        assert forecast._get_growth_factor_for_period("FY2023", "FY2022", 120.0) == 0.0


class TestAverageHistoricalGrowthForecastNodeCoverage:
    """Additional tests for AverageHistoricalGrowthForecastNode for coverage."""
    
    @pytest.fixture
    def mock_input_node_all_zeroes(self):
        """Create a mock input node with zero values."""
        node = Mock()
        node.name = "zero_node"
        node.values = {
            "FY2020": 0.0,
            "FY2021": 0.0,
            "FY2022": 0.0  # All periods are zero
        }
        node.calculate = lambda period: node.values.get(period, 0.0)
        return node
    
    def test_all_historical_values_zero(self, mock_input_node_all_zeroes, caplog):
        """Test case where all historical values are zero.
        
        This tests lines 423-424 in forecasts.py.
        """
        with caplog.at_level(logging.WARNING):
            forecast = AverageHistoricalGrowthForecastNode(
                mock_input_node_all_zeroes,
                "FY2022",
                ["FY2023", "FY2024", "FY2025"]
            )
            
            # Verify the growth rate is 0.0 when no valid rates could be calculated
            assert forecast.avg_growth_rate == 0.0
            
            # Check that a warning was logged
            assert "No valid growth rates calculated for zero_node" in caplog.text
            
            # Test calculate method with the 0.0 growth rate
            result = forecast.calculate("FY2023")
            assert result == 0.0  # 0.0 * (1 + 0.0) = 0.0 