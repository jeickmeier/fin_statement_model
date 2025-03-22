"""Unit tests for the forecasts module.

This module contains tests for the various forecast node classes 
that are used to project future values based on historical data.
"""
import pytest
from unittest.mock import Mock, patch
import numpy as np

from fin_statement_model.forecasts.forecasts import (
    ForecastNode,
    FixedGrowthForecastNode,
    CurveGrowthForecastNode,
    StatisticalGrowthForecastNode,
    CustomGrowthForecastNode,
    AverageValueForecastNode,
    AverageHistoricalGrowthForecastNode
)


class TestForecastNode:
    """Tests for the base ForecastNode class."""
    
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
    
    def test_init(self, mock_input_node):
        """Test initialization of ForecastNode."""
        forecast = ForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"]
        )
        
        assert forecast.name == "test_node"
        assert forecast.input_node == mock_input_node
        assert forecast.base_period == "FY2022"
        assert forecast.forecast_periods == ["FY2023", "FY2024", "FY2025"]
        assert forecast.values == mock_input_node.values
        assert forecast._cache == {}
    
    def test_init_no_values(self):
        """Test initialization with an input node without values attribute."""
        node = Mock(spec=['name'])  # Only specify 'name' in spec to prevent 'values' attribute
        node.name = "test_node"
        
        forecast = ForecastNode(node, "FY2022", ["FY2023"])
        assert forecast.values == {}
    
    def test_calculate_historical(self, mock_input_node):
        """Test calculation for historical periods."""
        forecast = ForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"]
        )
        
        # Should return historical value
        assert forecast.calculate("FY2020") == 100.0
        assert forecast.calculate("FY2021") == 110.0
        assert forecast.calculate("FY2022") == 120.0
    
    def test_forecast_value_alias(self, mock_input_node):
        """Test that forecast_value is an alias for calculate."""
        forecast = ForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"]
        )
        
        with patch.object(forecast, 'calculate') as mock_calculate:
            mock_calculate.return_value = 42.0
            result = forecast.forecast_value("FY2023")
            
            mock_calculate.assert_called_once_with("FY2023")
            assert result == 42.0
    
    def test_clear_cache(self, mock_input_node):
        """Test clearing the calculation cache."""
        forecast = ForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"]
        )
        
        # Add a value to the cache
        forecast._cache["FY2023"] = 150.0
        
        # Clear the cache
        forecast.clear_cache()
        
        assert forecast._cache == {}
    
    def test_get_previous_period(self, mock_input_node):
        """Test getting the previous period."""
        forecast = ForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"]
        )
        
        assert forecast._get_previous_period("FY2023") == "FY2022"
        assert forecast._get_previous_period("FY2024") == "FY2023"
        assert forecast._get_previous_period("FY2025") == "FY2024"

    def test_calculate_invalid_period(self, mock_input_node):
        """Test calculation for an invalid period."""
        forecast = ForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"]
        )
        
        # Period not in forecast periods
        with pytest.raises(ValueError) as excinfo:
            forecast._calculate_value("FY2026")
        
        assert "not in forecast periods" in str(excinfo.value)
    
    def test_get_growth_factor_not_implemented(self, mock_input_node):
        """Test that _get_growth_factor_for_period raises NotImplementedError."""
        forecast = ForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"]
        )
        
        with pytest.raises(NotImplementedError):
            forecast._get_growth_factor_for_period("FY2023", "FY2022", 120.0)


class TestFixedGrowthForecastNode:
    """Tests for the FixedGrowthForecastNode class."""
    
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
    
    def test_init(self, mock_input_node):
        """Test initialization with valid parameters."""
        forecast = FixedGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            0.05
        )
        
        assert forecast.name == "test_node"
        assert forecast.input_node == mock_input_node
        assert forecast.base_period == "FY2022"
        assert forecast.forecast_periods == ["FY2023", "FY2024", "FY2025"]
        assert forecast.growth_rate == 0.05
    
    def test_get_growth_factor(self, mock_input_node):
        """Test getting the growth factor."""
        forecast = FixedGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            0.05
        )
        
        # Should always return the fixed growth rate
        assert forecast._get_growth_factor_for_period("FY2023", "FY2022", 120.0) == 0.05
        assert forecast._get_growth_factor_for_period("FY2024", "FY2023", 126.0) == 0.05
        assert forecast._get_growth_factor_for_period("FY2025", "FY2024", 132.3) == 0.05
    
    def test_calculate_forecast(self, mock_input_node):
        """Test forecasting future values."""
        forecast = FixedGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            0.05
        )
        
        # FY2023 = 120.0 * (1 + 0.05) = 126.0
        assert forecast.calculate("FY2023") == pytest.approx(126.0)
        
        # FY2024 = 126.0 * (1 + 0.05) = 132.3
        assert forecast.calculate("FY2024") == pytest.approx(132.3)
        
        # FY2025 = 132.3 * (1 + 0.05) = 138.915
        assert forecast.calculate("FY2025") == pytest.approx(138.915)


class TestCurveGrowthForecastNode:
    """Tests for the CurveGrowthForecastNode class."""
    
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
    
    def test_init_valid(self, mock_input_node):
        """Test initialization with valid parameters."""
        forecast = CurveGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            [0.08, 0.06, 0.04]
        )
        
        assert forecast.name == "test_node"
        assert forecast.input_node == mock_input_node
        assert forecast.base_period == "FY2022"
        assert forecast.forecast_periods == ["FY2023", "FY2024", "FY2025"]
        assert forecast.growth_rates == [0.08, 0.06, 0.04]
    
    def test_init_invalid_growth_rates(self, mock_input_node):
        """Test initialization with invalid growth rates."""
        with pytest.raises(ValueError) as excinfo:
            CurveGrowthForecastNode(
                mock_input_node,
                "FY2022",
                ["FY2023", "FY2024", "FY2025"],
                [0.08, 0.06]  # Only 2 rates for 3 periods
            )
        
        assert "Number of growth rates must match forecast periods" in str(excinfo.value)
    
    def test_get_growth_factor(self, mock_input_node):
        """Test getting the growth factor for specific periods."""
        forecast = CurveGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            [0.08, 0.06, 0.04]
        )
        
        assert forecast._get_growth_factor_for_period("FY2023", "FY2022", 120.0) == 0.08
        assert forecast._get_growth_factor_for_period("FY2024", "FY2023", 129.6) == 0.06
        assert forecast._get_growth_factor_for_period("FY2025", "FY2024", 137.376) == 0.04
    
    def test_calculate_forecast(self, mock_input_node):
        """Test forecasting future values."""
        forecast = CurveGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            [0.08, 0.06, 0.04]
        )
        
        # FY2023 = 120.0 * (1 + 0.08) = 129.6
        assert forecast.calculate("FY2023") == pytest.approx(129.6)
        
        # FY2024 = 129.6 * (1 + 0.06) = 137.376
        assert forecast.calculate("FY2024") == pytest.approx(137.376)
        
        # FY2025 = 137.376 * (1 + 0.04) = 142.87104
        assert forecast.calculate("FY2025") == pytest.approx(142.87104)


class TestStatisticalGrowthForecastNode:
    """Tests for the StatisticalGrowthForecastNode class."""
    
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
    
    def test_init(self, mock_input_node):
        """Test initialization with valid parameters."""
        distribution = lambda: 0.05
        forecast = StatisticalGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            distribution
        )
        
        assert forecast.name == "test_node"
        assert forecast.input_node == mock_input_node
        assert forecast.base_period == "FY2022"
        assert forecast.forecast_periods == ["FY2023", "FY2024", "FY2025"]
        assert forecast.distribution_callable is distribution
    
    def test_get_growth_factor(self, mock_input_node):
        """Test getting the growth factor."""
        distribution = Mock(return_value=0.05)
        forecast = StatisticalGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            distribution
        )
        
        assert forecast._get_growth_factor_for_period("FY2023", "FY2022", 120.0) == 0.05
        distribution.assert_called_once()
    
    def test_calculate_forecast(self, mock_input_node):
        """Test forecasting future values."""
        # Use a fixed value for deterministic testing
        distribution = lambda: 0.05
        forecast = StatisticalGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            distribution
        )
        
        # FY2023 = 120.0 * (1 + 0.05) = 126.0
        assert forecast.calculate("FY2023") == pytest.approx(126.0)
        
        # FY2024 = 126.0 * (1 + 0.05) = 132.3
        assert forecast.calculate("FY2024") == pytest.approx(132.3)
        
        # FY2025 = 132.3 * (1 + 0.05) = 138.915
        assert forecast.calculate("FY2025") == pytest.approx(138.915)


class TestCustomGrowthForecastNode:
    """Tests for the CustomGrowthForecastNode class."""
    
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
    
    def test_init(self, mock_input_node):
        """Test initialization with valid parameters."""
        growth_function = lambda period, prev_period, prev_value: 0.05
        forecast = CustomGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            growth_function
        )
        
        assert forecast.name == "test_node"
        assert forecast.input_node == mock_input_node
        assert forecast.base_period == "FY2022"
        assert forecast.forecast_periods == ["FY2023", "FY2024", "FY2025"]
        assert forecast.growth_function is growth_function
    
    def test_get_growth_factor(self, mock_input_node):
        """Test getting the growth factor."""
        growth_function = Mock(return_value=0.05)
        forecast = CustomGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            growth_function
        )
        
        assert forecast._get_growth_factor_for_period("FY2023", "FY2022", 120.0) == 0.05
        growth_function.assert_called_once_with("FY2023", "FY2022", 120.0)
    
    def test_calculate_forecast_with_year_dependent_growth(self, mock_input_node):
        """Test forecasting with a growth function that depends on the year."""
        # Growth increases by 1% each year
        def custom_growth(period, prev_period, prev_value):
            year_diff = int(period[-4:]) - 2022
            return 0.05 + (0.01 * year_diff)
        
        forecast = CustomGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            custom_growth
        )
        
        # FY2023 = 120.0 * (1 + 0.06) = 127.2  (0.05 + 0.01)
        assert forecast.calculate("FY2023") == pytest.approx(127.2)
        
        # FY2024 = 127.2 * (1 + 0.07) = 136.104  (0.05 + 0.02)
        assert forecast.calculate("FY2024") == pytest.approx(136.104)
        
        # FY2025 = 136.104 * (1 + 0.08) = 146.99232  (0.05 + 0.03)
        assert forecast.calculate("FY2025") == pytest.approx(146.99232)


class TestAverageValueForecastNode:
    """Tests for the AverageValueForecastNode class."""
    
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
    
    def test_init(self, mock_input_node):
        """Test initialization with valid parameters."""
        forecast = AverageValueForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            110.0
        )
        
        assert forecast.name == "test_node"
        assert forecast.input_node == mock_input_node
        assert forecast.base_period == "FY2022"
        assert forecast.forecast_periods == ["FY2023", "FY2024", "FY2025"]
        assert forecast.average_value == 110.0
    
    def test_calculate_value(self, mock_input_node):
        """Test calculation for both historical and forecast periods."""
        forecast = AverageValueForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            110.0
        )
        
        # Historical periods use actual values
        assert forecast._calculate_value("FY2020") == 100.0
        assert forecast._calculate_value("FY2021") == 110.0
        assert forecast._calculate_value("FY2022") == 120.0
        
        # Forecast periods use the average value
        assert forecast._calculate_value("FY2023") == 110.0
        assert forecast._calculate_value("FY2024") == 110.0
        assert forecast._calculate_value("FY2025") == 110.0
    
    def test_calculate_invalid_period(self, mock_input_node):
        """Test calculation for an invalid period."""
        forecast = AverageValueForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            110.0
        )
        
        # Period not in forecast periods
        with pytest.raises(ValueError) as excinfo:
            forecast._calculate_value("FY2026")
        
        assert "not in forecast periods" in str(excinfo.value)


class TestAverageHistoricalGrowthForecastNode:
    """Tests for the AverageHistoricalGrowthForecastNode class."""
    
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
    
    def test_init_calculates_avg_growth(self, mock_input_node):
        """Test that initialization calculates the average growth rate."""
        forecast = AverageHistoricalGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"]
        )
        
        # Growth rate: (110/100 - 1) = 0.1, (120/110 - 1) = 0.0909
        # Average: (0.1 + 0.0909) / 2 = 0.09545
        expected_rate = ((110.0/100.0 - 1) + (120.0/110.0 - 1)) / 2
        
        assert forecast.avg_growth_rate == pytest.approx(expected_rate)
    
    def test_calculate_average_growth_rate(self, mock_input_node):
        """Test calculation of average growth rate with various scenarios."""
        # Normal case tested above
        
        # Test with no historical values
        empty_node = Mock()
        empty_node.name = "empty_node"
        empty_node.values = {}
        
        forecast = AverageHistoricalGrowthForecastNode(
            empty_node,
            "FY2022",
            ["FY2023"]
        )
        
        assert forecast.avg_growth_rate == 0.0
        
        # Test with insufficient historical data (only one period)
        single_node = Mock()
        single_node.name = "single_node"
        single_node.values = {"FY2022": 100.0}
        
        forecast = AverageHistoricalGrowthForecastNode(
            single_node,
            "FY2022",
            ["FY2023"]
        )
        
        assert forecast.avg_growth_rate == 0.0
        
        # Test with zero values
        zero_node = Mock()
        zero_node.name = "zero_node"
        zero_node.values = {
            "FY2020": 0.0,
            "FY2021": 10.0,
            "FY2022": 20.0
        }
        
        forecast = AverageHistoricalGrowthForecastNode(
            zero_node,
            "FY2022",
            ["FY2023"]
        )
        
        # Should skip the first period where prev_value is 0
        assert forecast.avg_growth_rate == 1.0  # (20/10 - 1) = 1.0
    
    def test_get_growth_factor(self, mock_input_node):
        """Test getting the growth factor."""
        forecast = AverageHistoricalGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"]
        )
        
        expected_rate = ((110.0/100.0 - 1) + (120.0/110.0 - 1)) / 2
        
        # Should always return the calculated average growth rate
        assert forecast._get_growth_factor_for_period("FY2023", "FY2022", 120.0) == pytest.approx(expected_rate)
        assert forecast._get_growth_factor_for_period("FY2024", "FY2023", 130.0) == pytest.approx(expected_rate)
    
    def test_calculate_forecast(self, mock_input_node):
        """Test forecasting future values."""
        forecast = AverageHistoricalGrowthForecastNode(
            mock_input_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"]
        )
        
        expected_rate = ((110.0/100.0 - 1) + (120.0/110.0 - 1)) / 2
        
        # FY2023 = 120.0 * (1 + expected_rate)
        expected_fy2023 = 120.0 * (1 + expected_rate)
        assert forecast.calculate("FY2023") == pytest.approx(expected_fy2023)
        
        # FY2024 = expected_fy2023 * (1 + expected_rate)
        expected_fy2024 = expected_fy2023 * (1 + expected_rate)
        assert forecast.calculate("FY2024") == pytest.approx(expected_fy2024)
        
        # FY2025 = expected_fy2024 * (1 + expected_rate)
        expected_fy2025 = expected_fy2024 * (1 + expected_rate)
        assert forecast.calculate("FY2025") == pytest.approx(expected_fy2025) 