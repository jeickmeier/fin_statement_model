"""Unit tests for the PeriodConversionTransformer.

This module contains tests for the PeriodConversionTransformer class from
financial_transformers.py.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock

from fin_statement_model.transformations.financial_transformers import PeriodConversionTransformer


class TestPeriodConversionTransformer:
    """Tests for the PeriodConversionTransformer class."""
    
    @pytest.fixture
    def monthly_data(self):
        """Create sample monthly data."""
        # Create a DataFrame with monthly data for 2 years
        dates = pd.date_range(start='2020-01-01', periods=24, freq='ME')
        # Generate revenue data with seasonal pattern (higher in Q4)
        revenues = []
        for i in range(24):
            base = 1000 + i * 50  # Upward trend
            seasonal = 200 if (i % 12) >= 9 else 0  # Q4 boost
            revenues.append(base + seasonal)
        
        return pd.DataFrame({
            'revenue': revenues,
            'expenses': [rev * 0.6 for rev in revenues],
            'profit': [rev * 0.4 for rev in revenues]
        }, index=dates)
    
    @pytest.fixture
    def quarterly_data(self):
        """Create sample quarterly data."""
        # Create a DataFrame with quarterly data for 3 years
        dates = pd.date_range(start='2020-01-01', periods=12, freq='QE')
        # Generate data with upward trend
        revenues = [1000 + i * 150 for i in range(12)]
        
        return pd.DataFrame({
            'revenue': revenues,
            'expenses': [rev * 0.6 for rev in revenues],
            'profit': [rev * 0.4 for rev in revenues]
        }, index=dates)
    
    def test_init_default(self):
        """Test initialization with default values."""
        transformer = PeriodConversionTransformer(conversion_type='quarterly_to_annual')
        assert transformer.conversion_type == 'quarterly_to_annual'
        assert transformer.aggregation == 'sum'
        assert transformer.config == {}
    
    def test_init_custom(self):
        """Test initialization with custom values."""
        config = {'preserve_original': True}
        transformer = PeriodConversionTransformer(
            conversion_type='monthly_to_quarterly',
            aggregation='mean',
            config=config
        )
        assert transformer.conversion_type == 'monthly_to_quarterly'
        assert transformer.aggregation == 'mean'
        assert transformer.config == config
    
    def test_init_invalid_type(self):
        """Test initialization with invalid conversion type."""
        with pytest.raises(ValueError) as exc_info:
            PeriodConversionTransformer(conversion_type='invalid_type')
        assert "Invalid conversion type" in str(exc_info.value)
    
    def test_quarterly_to_annual_sum(self, quarterly_data):
        """Test converting quarterly data to annual with sum aggregation."""
        transformer = PeriodConversionTransformer(
            conversion_type='quarterly_to_annual',
            aggregation='sum'
        )
        
        result = transformer.transform(quarterly_data)
        
        # Check the output structure
        assert len(result) == 3  # 3 years of data
        assert list(result.index) == [2020, 2021, 2022]  # Year indices
        
        # Check that values were properly summed
        # For 2020: Q1 + Q2 + Q3 + Q4
        expected_2020_revenue = sum(quarterly_data['revenue'][:4])
        assert result.loc[2020, 'revenue'] == expected_2020_revenue
    
    def test_quarterly_to_annual_mean(self, quarterly_data):
        """Test converting quarterly data to annual with mean aggregation."""
        transformer = PeriodConversionTransformer(
            conversion_type='quarterly_to_annual',
            aggregation='mean'
        )
        
        result = transformer.transform(quarterly_data)
        
        # Check that values were properly averaged
        # For 2020: average of Q1, Q2, Q3, Q4
        expected_2020_revenue = quarterly_data['revenue'][:4].mean()
        assert result.loc[2020, 'revenue'] == expected_2020_revenue
    
    def test_monthly_to_quarterly_sum(self, monthly_data):
        """Test converting monthly data to quarterly with sum aggregation."""
        transformer = PeriodConversionTransformer(
            conversion_type='monthly_to_quarterly',
            aggregation='sum'
        )
        
        result = transformer.transform(monthly_data)
        
        # Check the output structure
        assert len(result) == 8  # 8 quarters over 2 years
        
        # Group by year and quarter to verify
        grouped = monthly_data.groupby([monthly_data.index.year, monthly_data.index.quarter]).sum()
        
        # Compare a specific quarter
        year_2020_q1_idx = (2020, 1)
        assert result.loc[(2020, 1), 'revenue'] == grouped.loc[year_2020_q1_idx, 'revenue']
    
    def test_monthly_to_annual_sum(self, monthly_data):
        """Test converting monthly data to annual with sum aggregation."""
        transformer = PeriodConversionTransformer(
            conversion_type='monthly_to_annual',
            aggregation='sum'
        )
        
        result = transformer.transform(monthly_data)
        
        # Check the output structure
        assert len(result) == 2  # 2 years of data
        assert list(result.index) == [2020, 2021]  # Year indices
        
        # Check that values were properly summed for one year
        expected_2020_revenue = monthly_data.loc['2020', 'revenue'].sum()
        assert result.loc[2020, 'revenue'] == expected_2020_revenue
    
    def test_annual_to_ttm(self, quarterly_data):
        """Test converting quarterly data to trailing twelve months."""
        transformer = PeriodConversionTransformer(
            conversion_type='annual_to_ttm',
            aggregation='sum'
        )
        
        result = transformer.transform(quarterly_data)
        
        # TTM is implemented as a rolling sum with window=4 for quarterly data
        expected = quarterly_data.rolling(window=4).sum()
        pd.testing.assert_frame_equal(result, expected)
    
    def test_annual_to_ttm_nonsumable(self, quarterly_data):
        """Test converting to TTM with non-sum aggregation."""
        transformer = PeriodConversionTransformer(
            conversion_type='annual_to_ttm',
            aggregation='mean'
        )
        
        with pytest.raises(ValueError) as exc_info:
            transformer.transform(quarterly_data)
        assert "annual_to_ttm conversion only supports 'sum' aggregation" in str(exc_info.value)
    
    def test_transform_non_dataframe(self):
        """Test transform with non-DataFrame input."""
        transformer = PeriodConversionTransformer(conversion_type='quarterly_to_annual')
        
        with pytest.raises(ValueError) as exc_info:
            transformer.transform({'not': 'a dataframe'})
        assert "requires a pandas DataFrame" in str(exc_info.value)
    
    def test_transform_non_datetime_index(self):
        """Test transform with non-datetime index."""
        transformer = PeriodConversionTransformer(conversion_type='quarterly_to_annual')
        
        # Create DataFrame with non-datetime index that can't be converted
        df = pd.DataFrame({
            'revenue': [100, 200, 300],
            'expenses': [60, 120, 180]
        }, index=['a', 'b', 'c'])  # String index
        
        with pytest.raises(ValueError) as exc_info:
            transformer.transform(df)
        assert "Index must be convertible to datetime" in str(exc_info.value)
    
    def test_transform_convertible_string_index(self):
        """Test transform with string index that can be converted to datetime."""
        transformer = PeriodConversionTransformer(conversion_type='quarterly_to_annual')
        
        # Create DataFrame with string index that can be converted to datetime
        df = pd.DataFrame({
            'revenue': [100, 200, 300, 400],
            'expenses': [60, 120, 180, 240]
        }, index=['2020-01-01', '2020-04-01', '2020-07-01', '2020-10-01'])
        
        result = transformer.transform(df)
        
        # Should successfully convert and aggregate
        assert len(result) == 1  # 1 year
        assert result.loc[2020, 'revenue'] == 1000  # 100 + 200 + 300 + 400
    
    def test_monthly_to_quarterly_different_aggregations(self, monthly_data):
        """Test different aggregation methods for monthly to quarterly conversion."""
        # Test mean aggregation
        transformer_mean = PeriodConversionTransformer(
            conversion_type='monthly_to_quarterly',
            aggregation='mean'
        )
        result_mean = transformer_mean.transform(monthly_data)
        
        # Test max aggregation
        transformer_max = PeriodConversionTransformer(
            conversion_type='monthly_to_quarterly',
            aggregation='max'
        )
        result_max = transformer_max.transform(monthly_data)
        
        # Check that mean and max give different results
        # The first quarter of 2020 should have different values for mean vs max
        assert result_mean.loc[(2020, 1), 'revenue'] != result_max.loc[(2020, 1), 'revenue']
        
        # Max should be higher than mean
        assert result_max.loc[(2020, 1), 'revenue'] > result_mean.loc[(2020, 1), 'revenue'] 