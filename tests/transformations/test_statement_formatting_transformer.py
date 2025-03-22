"""Unit tests for the StatementFormattingTransformer.

This module contains tests for the StatementFormattingTransformer class from
financial_transformers.py.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

from fin_statement_model.transformations.financial_transformers import StatementFormattingTransformer


class TestStatementFormattingTransformer:
    """Tests for the StatementFormattingTransformer class."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample financial data."""
        # Using a DataFrame with rows as line items to match the implementation
        df = pd.DataFrame({
            2020: [1000000, -600000, 400000, -200000, 200000, -50000, 150000, -30000, 120000],
            2021: [1200000, -720000, 480000, -220000, 260000, -60000, 200000, -40000, 160000],
            2022: [1500000, -900000, 600000, -250000, 350000, -70000, 280000, -56000, 224000]
        }, index=['revenue', 'cost_of_goods_sold', 'gross_profit', 'operating_expenses', 
                 'operating_income', 'interest_expense', 'income_before_taxes', 'income_tax', 'net_income'])
        return df
    
    @pytest.fixture
    def sample_balance_sheet(self):
        """Create sample balance sheet data."""
        df = pd.DataFrame({
            2020: [100000, 80000, 120000, 300000, 500000, 800000, 70000, 50000, 120000, 300000, 
                  420000, 380000, 800000],
            2021: [120000, 95000, 140000, 355000, 480000, 835000, 85000, 60000, 145000, 280000,
                  425000, 410000, 835000],
            2022: [150000, 110000, 160000, 420000, 460000, 880000, 100000, 70000, 170000, 260000,
                  430000, 450000, 880000]
        }, index=['cash_and_equivalents', 'accounts_receivable', 'inventory', 'current_assets',
                 'property_plant_equipment', 'total_assets', 'accounts_payable', 'short_term_debt',
                 'current_liabilities', 'long_term_debt', 'total_liabilities', 'total_equity',
                 'total_liabilities_and_equity'])
        return df
    
    def test_init_default(self):
        """Test initialization with default values."""
        transformer = StatementFormattingTransformer()
        assert transformer.statement_type == 'income_statement'
        assert transformer.add_subtotals is True
        assert transformer.apply_sign_convention is True
        assert transformer.config == {}
    
    def test_init_custom(self):
        """Test initialization with custom values."""
        transformer = StatementFormattingTransformer(
            statement_type='balance_sheet',
            add_subtotals=False,
            apply_sign_convention=False,
            config={'custom_option': True}
        )
        assert transformer.statement_type == 'balance_sheet'
        assert transformer.add_subtotals is False
        assert transformer.apply_sign_convention is False
        assert transformer.config == {'custom_option': True}
    
    def test_get_standard_order(self):
        """Test getting standard order for different statement types."""
        # Income statement
        transformer_income = StatementFormattingTransformer(statement_type='income_statement')
        income_order = transformer_income._get_standard_order()
        assert 'revenue' in income_order
        assert 'gross_profit' in income_order
        assert 'net_income' in income_order
        
        # Balance sheet
        transformer_balance = StatementFormattingTransformer(statement_type='balance_sheet')
        balance_order = transformer_balance._get_standard_order()
        assert 'cash_and_equivalents' in balance_order
        assert 'total_assets' in balance_order
        assert 'total_liabilities_and_equity' in balance_order
        
        # Cash flow
        transformer_cash = StatementFormattingTransformer(statement_type='cash_flow')
        cash_order = transformer_cash._get_standard_order()
        assert 'net_income' in cash_order
        assert 'cash_from_operating_activities' in cash_order
        assert 'net_change_in_cash' in cash_order
    
    def test_apply_sign_convention(self, sample_data):
        """Test applying sign conventions to line items."""
        # Create a sample with positive values for items that should be negative
        df = sample_data.copy()
        df.loc['cost_of_goods_sold'] = abs(df.loc['cost_of_goods_sold'])  # Make positive
        df.loc['operating_expenses'] = abs(df.loc['operating_expenses'])  # Make positive
        
        transformer = StatementFormattingTransformer(statement_type='income_statement')
        result = transformer._apply_sign_convention(df)
        
        # Check that the values were converted to negative
        assert (result.loc['cost_of_goods_sold'] < 0).all()
        assert (result.loc['operating_expenses'] < 0).all()
        
        # Check that other values remain unchanged
        assert (result.loc['revenue'] == df.loc['revenue']).all()
        assert (result.loc['gross_profit'] == df.loc['gross_profit']).all()
    
    def test_add_subtotals_income_statement(self):
        """Test adding subtotals to income statement."""
        # Create a dataframe without subtotals - remove rows rather than setting to None
        # because the implementation checks if the index exists, not if the value is None
        df = pd.DataFrame({
            2020: [1000000, -600000, -200000, -50000, -30000],
            2021: [1200000, -720000, -220000, -60000, -40000]
        }, index=['revenue', 'cost_of_goods_sold', 'operating_expenses', 
                 'interest_expense', 'income_tax'])
        
        transformer = StatementFormattingTransformer(statement_type='income_statement')
        result = transformer._add_subtotals(df)
        
        # Check that subtotals were added correctly
        # First check if the subtotal rows were added
        assert 'gross_profit' in result.index
        assert 'operating_income' in result.index
        assert 'income_before_taxes' in result.index
        assert 'net_income' in result.index
        
        # Then check the calculations
        assert result.loc['gross_profit', 2020] == 400000  # 1000000 + (-600000)
        assert result.loc['operating_income', 2020] == 200000  # 400000 + (-200000)
        assert result.loc['income_before_taxes', 2020] == 150000  # 200000 + (-50000)
        assert result.loc['net_income', 2020] == 120000  # 150000 + (-30000)
    
    def test_add_subtotals_balance_sheet(self):
        """Test adding subtotals to balance sheet."""
        # Create a dataframe without subtotals - omit the subtotal rows completely
        df = pd.DataFrame({
            2020: [100000, 80000, 120000, 500000, 70000, 50000, 300000],
            2021: [120000, 95000, 140000, 480000, 85000, 60000, 280000]
        }, index=['cash_and_equivalents', 'accounts_receivable', 'inventory',
                 'property_plant_equipment', 'accounts_payable', 'short_term_debt',
                 'long_term_debt'])
        
        transformer = StatementFormattingTransformer(statement_type='balance_sheet')
        result = transformer._add_subtotals(df)
        
        # Check that subtotals were added correctly
        assert 'current_assets' in result.index
        assert 'total_assets' in result.index
        assert 'current_liabilities' in result.index
        assert 'total_liabilities' in result.index
        
        # The implementation doesn't seem to add total_equity or total_liabilities_and_equity
        # because our test data doesn't have the required input items
        
        # Check calculations
        assert result.loc['current_assets', 2020] == 300000  # 100000 + 80000 + 120000
        assert result.loc['total_assets', 2020] == 800000  # 300000 + 500000
        assert result.loc['current_liabilities', 2020] == 120000  # 70000 + 50000
        assert result.loc['total_liabilities', 2020] == 420000  # 120000 + 300000
    
    def test_reorder_items(self, sample_data):
        """Test reordering items according to standard format."""
        # Shuffle the index to create a disordered DataFrame
        df = sample_data.copy()
        shuffled_index = ['net_income', 'revenue', 'operating_income', 'cost_of_goods_sold', 
                         'income_before_taxes', 'income_tax', 'interest_expense', 'gross_profit', 
                         'operating_expenses']
        df = df.reindex(shuffled_index)
        
        transformer = StatementFormattingTransformer(statement_type='income_statement')
        result = transformer._reorder_items(df)
        
        # Check that the order follows the standard
        standard_order = transformer.item_order
        result_order = list(result.index)
        
        # Check the positions of key items relative to each other
        assert result_order.index('revenue') < result_order.index('cost_of_goods_sold')
        assert result_order.index('cost_of_goods_sold') < result_order.index('gross_profit')
        assert result_order.index('gross_profit') < result_order.index('operating_income')
        assert result_order.index('operating_income') < result_order.index('net_income')
    
    def test_transform_complete(self, sample_data):
        """Test the complete transformation process."""
        # Create a dataframe with positive expense values and shuffled order
        df = sample_data.copy()
        df.loc['cost_of_goods_sold'] = abs(df.loc['cost_of_goods_sold'])
        df.loc['operating_expenses'] = abs(df.loc['operating_expenses'])
        shuffled_index = ['net_income', 'revenue', 'operating_income', 'cost_of_goods_sold', 
                         'income_before_taxes', 'income_tax', 'interest_expense', 'gross_profit', 
                         'operating_expenses']
        df = df.reindex(shuffled_index)
        
        transformer = StatementFormattingTransformer(statement_type='income_statement')
        result = transformer.transform(df)
        
        # Check that sign conventions were applied
        assert (result.loc['cost_of_goods_sold'] < 0).all()
        assert (result.loc['operating_expenses'] < 0).all()
        
        # Check that the order follows the standard
        result_order = list(result.index)
        assert result_order.index('revenue') < result_order.index('cost_of_goods_sold')
        assert result_order.index('gross_profit') < result_order.index('operating_income')
    
    def test_transform_non_dataframe(self):
        """Test transform with non-DataFrame input."""
        transformer = StatementFormattingTransformer()
        
        with pytest.raises(AttributeError):
            transformer.transform({'not': 'a dataframe'})
    
    def test_transform_empty_dataframe(self):
        """Test transform with empty DataFrame."""
        transformer = StatementFormattingTransformer()
        empty_df = pd.DataFrame()
        
        result = transformer.transform(empty_df)
        assert result.empty
    
    def test_without_sign_convention(self, sample_data):
        """Test transformation without applying sign conventions."""
        # Create a dataframe with positive expense values
        df = sample_data.copy()
        df.loc['cost_of_goods_sold'] = abs(df.loc['cost_of_goods_sold'])
        df.loc['operating_expenses'] = abs(df.loc['operating_expenses'])
        
        transformer = StatementFormattingTransformer(
            statement_type='income_statement',
            apply_sign_convention=False
        )
        result = transformer.transform(df)
        
        # Check that values remain positive (unchanged)
        assert (result.loc['cost_of_goods_sold'] > 0).all()
        assert (result.loc['operating_expenses'] > 0).all()
    
    def test_without_subtotals(self):
        """Test transformation without adding subtotals."""
        # Create a dataframe without subtotals
        df = pd.DataFrame({
            2020: [1000000, -600000, None, -200000],
            2021: [1200000, -720000, None, -220000]
        }, index=['revenue', 'cost_of_goods_sold', 'gross_profit', 'operating_expenses'])
        
        transformer = StatementFormattingTransformer(
            statement_type='income_statement',
            add_subtotals=False
        )
        result = transformer.transform(df)
        
        # Check that gross_profit remains None
        assert pd.isna(result.loc['gross_profit', 2020])
    
    def test_preserve_original_dataframe(self, sample_data):
        """Test that the original DataFrame is not modified."""
        original = sample_data.copy()
        
        transformer = StatementFormattingTransformer()
        result = transformer.transform(sample_data)
        
        # The result should be different but the original should be unchanged
        assert id(result) != id(sample_data)
        pd.testing.assert_frame_equal(sample_data, original) 