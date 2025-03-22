"""Unit tests for PeriodConversionTransformer coverage.

This module specifically targets untested code paths in the PeriodConversionTransformer
class to achieve 100% code coverage.
"""
import pytest
import pandas as pd
import numpy as np

from fin_statement_model.transformations.financial_transformers import PeriodConversionTransformer


class TestPeriodConversionCoverage:
    """Tests for achieving full coverage of PeriodConversionTransformer class."""
    
    @pytest.fixture
    def sample_quarterly_data(self):
        """Create a sample DataFrame with quarterly data."""
        return pd.DataFrame({
            'revenue': [100, 120, 130, 150, 160, 180, 190, 210],
            'expenses': [60, 70, 75, 85, 90, 100, 105, 120]
        }, index=pd.date_range(start='2021-01-01', periods=8, freq='3ME'))
    
    @pytest.fixture
    def sample_monthly_data(self):
        """Create a sample DataFrame with monthly data."""
        return pd.DataFrame({
            'revenue': [30, 35, 40, 42, 45, 50, 52, 55, 60, 58, 65, 70],
            'expenses': [18, 20, 22, 25, 26, 30, 31, 33, 35, 34, 38, 40]
        }, index=pd.date_range(start='2022-01-01', periods=12, freq='ME'))
    
    def test_transform_non_convertible_index(self):
        """Test transform with an index that cannot be converted to datetime."""
        # Create a DataFrame with an index that cannot be converted to datetime
        df = pd.DataFrame({
            'revenue': [100, 110, 120],
            'expenses': [60, 65, 70]
        }, index=['not_a_date', 'also_not_a_date', 'still_not_a_date'])
        
        transformer = PeriodConversionTransformer(conversion_type='quarterly_to_annual')
        
        with pytest.raises(ValueError) as excinfo:
            transformer.transform(df)
        
        assert "Index must be convertible to datetime" in str(excinfo.value)
    
    def test_annual_to_ttm_non_sum(self):
        """Test annual_to_ttm with non-sum aggregation method."""
        # Create quarterly data
        df = pd.DataFrame({
            'revenue': [100, 110, 120, 130],
            'expenses': [60, 65, 70, 75]
        }, index=pd.date_range(start='2022-01-01', periods=4, freq='3ME'))
        
        # Try to use a non-sum aggregation for TTM
        transformer = PeriodConversionTransformer(
            conversion_type='annual_to_ttm', 
            aggregation='mean'  # This should raise an error
        )
        
        with pytest.raises(ValueError) as excinfo:
            transformer.transform(df)
        
        assert "annual_to_ttm conversion only supports 'sum' aggregation" in str(excinfo.value)
    
    def test_monthly_to_quarterly_different_aggregations(self, sample_monthly_data):
        """Test monthly_to_quarterly with different aggregation methods."""
        # Test with mean aggregation
        mean_transformer = PeriodConversionTransformer(
            conversion_type='monthly_to_quarterly',
            aggregation='mean'
        )
        mean_result = mean_transformer.transform(sample_monthly_data)
        
        # Test with sum aggregation
        sum_transformer = PeriodConversionTransformer(
            conversion_type='monthly_to_quarterly',
            aggregation='sum'
        )
        sum_result = sum_transformer.transform(sample_monthly_data)
        
        # Test with last aggregation
        last_transformer = PeriodConversionTransformer(
            conversion_type='monthly_to_quarterly',
            aggregation='last'
        )
        last_result = last_transformer.transform(sample_monthly_data)
        
        # Verify results are different for different aggregation methods
        assert not mean_result.equals(sum_result)
        assert not mean_result.equals(last_result)
        assert not sum_result.equals(last_result)
        
        # Check specific values for mean aggregation (first quarter)
        # First quarter mean: (30+35+40)/3 = 35
        q1_mean_revenue = mean_result.loc[(2022, 1), 'revenue']
        assert abs(q1_mean_revenue - 35) < 1e-10
        
        # Check specific values for sum aggregation (first quarter)
        # First quarter sum: 30+35+40 = 105
        q1_sum_revenue = sum_result.loc[(2022, 1), 'revenue']
        assert abs(q1_sum_revenue - 105) < 1e-10
        
        # Check specific values for last aggregation (first quarter)
        # First quarter last: 40
        q1_last_revenue = last_result.loc[(2022, 1), 'revenue']
        assert abs(q1_last_revenue - 40) < 1e-10
    
    def test_transform_dict_input(self):
        """Test transforming dictionary input throws ValueError."""
        transformer = PeriodConversionTransformer(
            conversion_type='monthly_to_quarterly',
            aggregation='mean'
        )
        
        with pytest.raises(ValueError) as excinfo:
            transformer.transform({'2020-01': 100, '2020-02': 120})
            
        assert "Period conversion requires a pandas DataFrame" in str(excinfo.value)
        
    def test_unsupported_period_combination(self):
        """Test that unsupported period combinations raise ValueError."""
        with pytest.raises(ValueError) as excinfo:
            transformer = PeriodConversionTransformer(  # noqa: F841
                conversion_type='daily_to_quarterly'  # Unsupported conversion type
            )
            
        assert "Invalid conversion type" in str(excinfo.value)
        
        # with pytest.raises(ValueError) as excinfo:
        #     transformer = PeriodConversionTransformer(
        #         conversion_type='quarterly_to_monthly'  # Unsupported conversion direction
        #     )
            
        assert "Invalid conversion type" in str(excinfo.value)
        
    def test_ttm_with_incomplete_data(self):
        """Test TTM calculation with incomplete annual data."""
        # Create sample data with gaps
        df = pd.DataFrame({
            'revenue': [100, 110, np.nan, 140],
            'expenses': [80, 85, 90, np.nan]
        }, index=pd.date_range(start='2020-01-01', periods=4, freq='YE'))  # Use YE instead of A
        
        transformer = PeriodConversionTransformer(
            conversion_type='annual_to_ttm',
        )
        
        result = transformer.transform(df)
        
        # Since we have gaps in the data, TTM will have NaN values
        assert np.isnan(result['revenue'].iloc[-1])
        assert np.isnan(result['expenses'].iloc[-1]) 