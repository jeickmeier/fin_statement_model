"""Unit tests for StatementFormattingTransformer coverage.

This module specifically targets untested code paths in the StatementFormattingTransformer
class to achieve 100% code coverage.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

from fin_statement_model.transformations.financial_transformers import StatementFormattingTransformer


class TestStatementFormattingCoverage:
    """Tests for achieving full coverage of StatementFormattingTransformer class."""
    
    @pytest.fixture
    def sample_cash_flow(self):
        """Create sample cash flow statement data."""
        # Create a fresh dataframe with only the base values, not the calculated ones
        df = pd.DataFrame({
            2020: [120000, 50000, 30000, -80000, -20000, 50000, -30000, -20000],
            2021: [160000, 60000, 40000, -90000, -30000, 60000, -35000, -25000],
            2022: [224000, 70000, 50000, -100000, -40000, 70000, -40000, -30000]
        }, index=[
            'net_income', 
            'depreciation_amortization', 
            'changes_in_working_capital',
            'capital_expenditures', 
            'investments',
            'debt_issuance', 
            'debt_repayment', 
            'dividends'
        ])
        return df
    
    def test_cash_flow_add_subtotals(self, sample_cash_flow):
        """Test add_subtotals method with cash flow statement data."""
        transformer = StatementFormattingTransformer(
            statement_type='cash_flow',
            add_subtotals=True
        )
        
        # Create a copy of the dataframe to avoid modifying the fixture
        input_df = sample_cash_flow.copy()
        result = transformer._add_subtotals(input_df)
        
        # Verify all expected rows are present
        expected_rows = list(sample_cash_flow.index) + [
            'cash_from_operating_activities',
            'cash_from_investing_activities',
            'cash_from_financing_activities',
            'net_change_in_cash'
        ]
        for row in expected_rows:
            assert row in result.index
        
        # Check that subtotals were correctly calculated
        for year in sample_cash_flow.columns:
            # Cash from operating activities
            expected_operating = (
                sample_cash_flow.loc['net_income', year] + 
                sample_cash_flow.loc['depreciation_amortization', year] + 
                sample_cash_flow.loc['changes_in_working_capital', year]
            )
            assert result.loc['cash_from_operating_activities', year] == expected_operating
            
            # Cash from investing activities
            expected_investing = (
                sample_cash_flow.loc['capital_expenditures', year] + 
                sample_cash_flow.loc['investments', year]
            )
            assert result.loc['cash_from_investing_activities', year] == expected_investing
            
            # Cash from financing activities
            expected_financing = (
                sample_cash_flow.loc['debt_issuance', year] + 
                sample_cash_flow.loc['debt_repayment', year] + 
                sample_cash_flow.loc['dividends', year]
            )
            assert result.loc['cash_from_financing_activities', year] == expected_financing
            
            # Net change in cash
            expected_net_change = (
                result.loc['cash_from_operating_activities', year] + 
                result.loc['cash_from_investing_activities', year] + 
                result.loc['cash_from_financing_activities', year]
            )
            assert result.loc['net_change_in_cash', year] == expected_net_change
    
    def test_apply_sign_convention_cash_flow(self, sample_cash_flow):
        """Test apply_sign_convention method with cash flow statement."""
        # Make sure some values are positive that should be negative
        positive_df = sample_cash_flow.copy()
        positive_df.loc['capital_expenditures'] = positive_df.loc['capital_expenditures'].abs()
        positive_df.loc['investments'] = positive_df.loc['investments'].abs()
        
        transformer = StatementFormattingTransformer(
            statement_type='cash_flow',
            apply_sign_convention=True
        )
        
        result = transformer._apply_sign_convention(positive_df)
        
        # Check that values were converted to negative
        assert all(result.loc['capital_expenditures'] < 0), "Capital expenditures should be negative"
        assert all(result.loc['investments'] < 0), "Investments should be negative"
        
        # Check that other values were not affected
        pd.testing.assert_series_equal(result.loc['net_income'], positive_df.loc['net_income'])
    
    def test_add_subtotals_partial_items(self):
        """Test add_subtotals with only some financial statement items present."""
        # Create income statement with only revenue and cost_of_goods_sold
        df = pd.DataFrame({
            2020: [1000000, -600000],
            2021: [1200000, -720000]
        }, index=['revenue', 'cost_of_goods_sold'])
        
        transformer = StatementFormattingTransformer(
            statement_type='income_statement',
            add_subtotals=True
        )
        
        result = transformer._add_subtotals(df.copy())
        
        # Should add gross_profit
        expected_gross_profit = df.loc['revenue'] + df.loc['cost_of_goods_sold']
        
        # Compare values directly
        for col in df.columns:
            assert abs(result.loc['gross_profit', col] - expected_gross_profit[col]) < 1e-10
        
        # But should not add other subtotals that require missing items
        assert 'operating_income' not in result.index
        assert 'income_before_taxes' not in result.index
        assert 'net_income' not in result.index
    
    def test_add_subtotals_balance_sheet_partial(self):
        """Test add_subtotals for balance sheet with partial items."""
        # Create balance sheet with only some items
        df = pd.DataFrame({
            2020: [100000, 80000, 300000, 70000, 50000],
            2021: [120000, 95000, 320000, 85000, 60000]
        }, index=[
            'cash_and_equivalents', 
            'accounts_receivable', 
            'property_plant_equipment',
            'accounts_payable', 
            'short_term_debt'
        ])
        
        transformer = StatementFormattingTransformer(
            statement_type='balance_sheet',
            add_subtotals=True
        )
        
        result = transformer._add_subtotals(df.copy())
        
        # Should add current_assets and current_liabilities
        expected_current_assets = df.loc['cash_and_equivalents'] + df.loc['accounts_receivable']
        
        # Compare values directly
        for col in df.columns:
            assert abs(result.loc['current_assets', col] - expected_current_assets[col]) < 1e-10
        
        expected_current_liabilities = df.loc['accounts_payable'] + df.loc['short_term_debt']
        for col in df.columns:
            assert abs(result.loc['current_liabilities', col] - expected_current_liabilities[col]) < 1e-10
    
    def test_transform_cash_flow(self, sample_cash_flow):
        """Test complete transform method with cash flow statement."""
        transformer = StatementFormattingTransformer(
            statement_type='cash_flow',
            add_subtotals=True,
            apply_sign_convention=True
        )
        
        result = transformer.transform(sample_cash_flow)
        
        # Check that the transform was applied correctly
        assert 'cash_from_operating_activities' in result.index
        assert 'cash_from_investing_activities' in result.index
        assert 'cash_from_financing_activities' in result.index
        assert 'net_change_in_cash' in result.index
        
        # Items should be in the standard order
        standard_order = transformer.item_order
        for i, item in enumerate(result.index):
            if item in standard_order and i > 0:
                prev_item = result.index[i-1]
                if prev_item in standard_order:
                    assert standard_order.index(item) >= standard_order.index(prev_item), \
                        f"{item} should come after {prev_item} in the standard order" 