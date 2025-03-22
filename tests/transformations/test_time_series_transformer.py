"""Unit tests for the TimeSeriesTransformer.

This module contains tests for the TimeSeriesTransformer class from
financial_transformers.py.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock

from fin_statement_model.transformations.financial_transformers import TimeSeriesTransformer


class TestTimeSeriesTransformer:
    """Tests for the TimeSeriesTransformer class."""
    
    @pytest.fixture
    def sample_df(self):
        """Create a sample DataFrame with time series data."""
        return pd.DataFrame({
            'revenue': [1000, 1100, 1210, 1331],
            'expenses': [600, 630, 662, 695]
        }, index=pd.date_range(start='2020-01-01', periods=4, freq='YE'))
    
    @pytest.fixture
    def sample_dict(self):
        """Create a sample dictionary with time series data."""
        return {
            '2020': 1000,
            '2021': 1100,
            '2022': 1210,
            '2023': 1331
        }
    
    def test_init_default(self):
        """Test initialization with default values."""
        transformer = TimeSeriesTransformer()
        assert transformer.transformation_type == 'growth_rate'
        assert transformer.periods == 1
        assert transformer.window_size == 3
        assert transformer.config == {}
    
    def test_init_custom(self):
        """Test initialization with custom values."""
        config = {'preserve_original': True}
        transformer = TimeSeriesTransformer(
            transformation_type='moving_avg',
            periods=2,
            window_size=4,
            config=config
        )
        assert transformer.transformation_type == 'moving_avg'
        assert transformer.periods == 2
        assert transformer.window_size == 4
        assert transformer.config == config
    
    def test_init_invalid_type(self):
        """Test initialization with invalid transformation type."""
        with pytest.raises(ValueError) as exc_info:
            TimeSeriesTransformer(transformation_type='invalid_type')
        assert "Invalid transformation type" in str(exc_info.value)
    
    def test_growth_rate_dataframe(self, sample_df):
        """Test growth_rate transformation with DataFrame."""
        transformer = TimeSeriesTransformer(transformation_type='growth_rate')
        
        result = transformer.transform(sample_df)
        
        # Check new columns were added
        assert 'revenue_growth' in result.columns
        assert 'expenses_growth' in result.columns
        
        # First row should be NaN (no previous period)
        assert pd.isna(result['revenue_growth'].iloc[0])
        assert pd.isna(result['expenses_growth'].iloc[0])
        
        # Check growth rates calculation
        # revenue: 1000 -> 1100 is 10% growth
        assert abs(result['revenue_growth'].iloc[1] - 10.0) < 1e-6
        
        # revenue: 1100 -> 1210 is 10% growth
        assert abs(result['revenue_growth'].iloc[2] - 10.0) < 1e-6
    
    def test_growth_rate_dict(self, sample_dict):
        """Test growth_rate transformation with dictionary."""
        transformer = TimeSeriesTransformer(transformation_type='growth_rate')
        
        result = transformer.transform(sample_dict)
        
        # For dictionaries, the return format from to_dict() is different from what might be expected
        # The structure is {column -> {index -> value}}
        
        # Check that the original values are preserved in the result
        assert 0 in result  # Column 0 contains the original values
        assert result[0]['2020'] == 1000
        assert result[0]['2021'] == 1100
        assert result[0]['2022'] == 1210
        assert result[0]['2023'] == 1331
        
        # Check that the growth rates are added
        assert '0_growth' in result  # Column '0_growth' contains growth rates
        assert pd.isna(result['0_growth']['2020'])  # First period has no growth rate
        assert abs(result['0_growth']['2021'] - 10.0) < 1e-6  # 1000 -> 1100 is 10% growth
        assert abs(result['0_growth']['2022'] - 10.0) < 1e-6  # 1100 -> 1210 is 10% growth
        assert abs(result['0_growth']['2023'] - 10.0) < 1e-6  # 1210 -> 1331 is 10% growth
    
    def test_moving_avg_dataframe(self, sample_df):
        """Test moving_avg transformation with DataFrame."""
        transformer = TimeSeriesTransformer(
            transformation_type='moving_avg',
            window_size=3
        )
        
        result = transformer.transform(sample_df)
        
        # Check new columns were added
        assert 'revenue_ma3' in result.columns
        assert 'expenses_ma3' in result.columns
        
        # First two rows should be NaN (not enough data for window=3)
        assert pd.isna(result['revenue_ma3'].iloc[0])
        assert pd.isna(result['revenue_ma3'].iloc[1])
        
        # Third row should be the average of first three values
        expected_ma3 = (1000 + 1100 + 1210) / 3
        assert abs(result['revenue_ma3'].iloc[2] - expected_ma3) < 1e-6
    
    def test_cagr_dataframe(self, sample_df):
        """Test CAGR transformation with DataFrame."""
        transformer = TimeSeriesTransformer(transformation_type='cagr')
        
        result = transformer.transform(sample_df)
        
        # Check new columns were added
        assert 'revenue_cagr' in result.columns
        assert 'expenses_cagr' in result.columns
        
        # Calculate expected CAGR for revenue
        # CAGR formula: (end_value/start_value)^(1/periods) - 1
        # revenue: (1331/1000)^(1/3) - 1 ≈ 10%
        expected_cagr = ((1331/1000) ** (1/3) - 1) * 100
        
        # The CAGR column should have the same value for all rows
        for i in range(len(result)):
            assert abs(result['revenue_cagr'].iloc[i] - expected_cagr) < 1e-6
    
    def test_yoy_dataframe(self, sample_df):
        """Test YoY transformation with DataFrame."""
        transformer = TimeSeriesTransformer(transformation_type='yoy')
        
        result = transformer.transform(sample_df)
        
        # Check new columns were added
        assert 'revenue_yoy' in result.columns
        assert 'expenses_yoy' in result.columns
        
        # First row should be NaN (no previous year)
        assert pd.isna(result['revenue_yoy'].iloc[0])
        
        # YoY growth should match the growth rate
        # revenue: 1000 -> 1100 is 10% growth
        assert abs(result['revenue_yoy'].iloc[1] - 10.0) < 1e-6
    
    def test_qoq_dataframe(self, sample_df):
        """Test QoQ transformation with DataFrame."""
        transformer = TimeSeriesTransformer(transformation_type='qoq')
        
        result = transformer.transform(sample_df)
        
        # Check new columns were added
        assert 'revenue_qoq' in result.columns
        assert 'expenses_qoq' in result.columns
        
        # QoQ is effectively the same calculation as YoY, just with quarterly interpretation
        assert pd.isna(result['revenue_qoq'].iloc[0])
        assert abs(result['revenue_qoq'].iloc[1] - 10.0) < 1e-6
    
    def test_transform_unsupported_type(self):
        """Test transform with unsupported data type."""
        transformer = TimeSeriesTransformer()
        
        with pytest.raises(ValueError) as exc_info:
            transformer.transform("not supported")
        assert "Unsupported data type" in str(exc_info.value)
    
    def test_custom_periods(self, sample_df):
        """Test growth_rate with custom periods parameter."""
        transformer = TimeSeriesTransformer(
            transformation_type='growth_rate',
            periods=2
        )
        
        result = transformer.transform(sample_df)
        
        # First two rows should be NaN (need at least 2 periods of data)
        assert pd.isna(result['revenue_growth'].iloc[0])
        assert pd.isna(result['revenue_growth'].iloc[1])
        
        # Growth over 2 periods: 1000 -> 1210 is 21% growth
        expected_growth = ((1210 / 1000) - 1) * 100
        assert abs(result['revenue_growth'].iloc[2] - expected_growth) < 1e-6
    
    def test_custom_window_size(self, sample_df):
        """Test moving_avg with custom window size parameter."""
        transformer = TimeSeriesTransformer(
            transformation_type='moving_avg',
            window_size=2
        )
        
        result = transformer.transform(sample_df)
        
        # Check the column name reflects the window size
        assert 'revenue_ma2' in result.columns
        
        # First row should be NaN (need at least 2 periods for window=2)
        assert pd.isna(result['revenue_ma2'].iloc[0])
        
        # Second row should be the average of first two values
        expected_ma2 = (1000 + 1100) / 2
        assert abs(result['revenue_ma2'].iloc[1] - expected_ma2) < 1e-6 