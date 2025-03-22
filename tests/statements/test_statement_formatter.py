"""Unit tests for the statement_formatter module.

This module contains tests for the StatementFormatter class which is responsible
for formatting financial statement data into various representations such as
DataFrames and HTML.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, Mock

from fin_statement_model.statements.statement_formatter import StatementFormatter
from fin_statement_model.statements.statement_structure import (
    StatementStructure, 
    Section, 
    LineItem, 
    CalculatedLineItem, 
    SubtotalLineItem,
    StatementItemType
)
from fin_statement_model.core.errors import DataValidationError


class TestStatementFormatter:
    """Tests for the StatementFormatter class."""
    
    @pytest.fixture
    def simple_statement(self):
        """Fixture providing a simple statement structure."""
        # Create a simple statement structure
        statement = StatementStructure(
            id="income_statement",
            name="Income Statement",
            description="Test income statement"
        )
        
        # Create sections
        revenue_section = Section(
            id="revenue_section",
            name="Revenue"
        )
        
        expense_section = Section(
            id="expense_section",
            name="Expenses"
        )
        
        profit_section = Section(
            id="profit_section",
            name="Profit"
        )
        
        # Create line items
        revenue_item = LineItem(
            id="revenue",
            name="Total Revenue",
            node_id="revenue"
        )
        
        cogs_item = LineItem(
            id="cogs",
            name="Cost of Goods Sold",
            node_id="cogs",
            sign_convention=-1
        )
        
        opex_item = LineItem(
            id="opex",
            name="Operating Expenses",
            node_id="opex",
            sign_convention=-1
        )
        
        # Create subtotal
        expenses_subtotal = SubtotalLineItem(
            id="total_expenses",
            name="Total Expenses",
            item_ids=["cogs", "opex"],
            sign_convention=-1
        )
        
        # Create calculated items
        gross_profit = CalculatedLineItem(
            id="gross_profit",
            name="Gross Profit",
            calculation={
                "type": "addition",
                "inputs": ["revenue", "cogs"]
            }
        )
        
        operating_profit = CalculatedLineItem(
            id="operating_profit",
            name="Operating Profit",
            calculation={
                "type": "addition",
                "inputs": ["gross_profit", "opex"]
            }
        )
        
        # Build structure
        revenue_section.add_item(revenue_item)
        expense_section.add_item(cogs_item)
        expense_section.add_item(opex_item)
        expense_section.add_item(expenses_subtotal)
        profit_section.add_item(gross_profit)
        profit_section.add_item(operating_profit)
        
        statement.add_section(revenue_section)
        statement.add_section(expense_section)
        statement.add_section(profit_section)
        
        return statement
    
    @pytest.fixture
    def sample_data(self):
        """Fixture providing sample financial data."""
        return {
            "revenue": {"2021": 1000.0, "2022": 1200.0},
            "cogs": {"2021": 600.0, "2022": 700.0},
            "opex": {"2021": 200.0, "2022": 250.0},
            "total_expenses": {"2021": 800.0, "2022": 950.0},
            "gross_profit": {"2021": 400.0, "2022": 500.0},
            "operating_profit": {"2021": 200.0, "2022": 250.0}
        }
    
    def test_init(self, simple_statement):
        """Test StatementFormatter initialization."""
        formatter = StatementFormatter(simple_statement)
        assert formatter.statement == simple_statement
    
    def test_generate_dataframe(self, simple_statement, sample_data):
        """Test generating a DataFrame from statement data."""
        formatter = StatementFormatter(simple_statement)
        
        # Mock validate_calculations to avoid dependency issues
        with patch.object(formatter, 'validate_calculations'):
            df = formatter.generate_dataframe(sample_data)
        
        # Check DataFrame structure
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["Item", "Name", "2021", "2022"]
        
        # Check number of rows
        # Statement + 3 sections + 6 items = 10 rows
        assert len(df) == 10
        
        # Check specific values
        revenue_row = df[df["Item"].str.contains("revenue$")].iloc[0]
        assert revenue_row["Name"] == "Total Revenue"
        assert revenue_row["2021"] == 1000.0
        assert revenue_row["2022"] == 1200.0
        
        # Check COGS with sign convention
        cogs_row = df[df["Item"].str.contains("cogs$")].iloc[0]
        assert cogs_row["2021"] == -600.0  # Sign inverted
        assert cogs_row["2022"] == -700.0  # Sign inverted
    
    def test_generate_dataframe_no_sign_convention(self, simple_statement, sample_data):
        """Test generating a DataFrame without applying sign conventions."""
        formatter = StatementFormatter(simple_statement)
        
        # Mock validate_calculations to avoid dependency issues
        with patch.object(formatter, 'validate_calculations'):
            df = formatter.generate_dataframe(sample_data, apply_sign_convention=False)
        
        # Check COGS without sign convention
        cogs_row = df[df["Item"].str.contains("cogs$")].iloc[0]
        assert cogs_row["2021"] == 600.0  # Original sign
        assert cogs_row["2022"] == 700.0  # Original sign
    
    def test_generate_dataframe_include_empty(self, simple_statement, sample_data):
        """Test generating a DataFrame including empty items."""
        formatter = StatementFormatter(simple_statement)
        
        # Create data with missing values
        partial_data = {
            "revenue": {"2021": 1000.0, "2022": 1200.0},
            "cogs": {"2021": 600.0, "2022": 700.0},
            # opex missing
            "gross_profit": {"2021": 400.0, "2022": 500.0},
            # operating_profit missing
        }
        
        # Mock validate_calculations to avoid dependency issues
        with patch.object(formatter, 'validate_calculations'):
            df = formatter.generate_dataframe(partial_data, include_empty_items=True)
        
        # Check that all items are included
        # Statement + 3 sections + 6 items = 10 rows
        assert len(df) == 10
        
        # Check that missing items have empty values
        opex_row = df[df["Item"].str.contains("opex$")].iloc[0]
        assert opex_row["2021"] == ""
        assert opex_row["2022"] == ""
    
    def test_generate_dataframe_exclude_empty(self, simple_statement, sample_data):
        """Test generating a DataFrame excluding empty items."""
        formatter = StatementFormatter(simple_statement)
        
        # Create data with missing values
        partial_data = {
            "revenue": {"2021": 1000.0, "2022": 1200.0},
            "cogs": {"2021": 600.0, "2022": 700.0},
            # opex missing
            "gross_profit": {"2021": 400.0, "2022": 500.0},
            # operating_profit missing
        }
        
        # Mock validate_calculations to avoid dependency issues
        with patch.object(formatter, 'validate_calculations'):
            df = formatter.generate_dataframe(partial_data, include_empty_items=False)
        
        # Check that only items with data are included
        # Statement + 3 sections + 3 items with data = 7 rows
        assert len(df) == 7
        
        # Check that missing items are excluded
        assert len(df[df["Item"].str.contains("opex$")]) == 0
    
    def test_generate_dataframe_validation_error(self, simple_statement, sample_data):
        """Test that validation errors are properly raised."""
        formatter = StatementFormatter(simple_statement)
        
        # Mock validate_calculations to raise an error
        with patch.object(formatter, 'validate_calculations', 
                        side_effect=DataValidationError("Test error")):
            with pytest.raises(DataValidationError) as excinfo:
                formatter.generate_dataframe(sample_data)
            
            assert "Test error" in str(excinfo.value)
    
    def test_generate_dataframe_other_exception(self, simple_statement, sample_data):
        """Test handling of non-validation exceptions."""
        formatter = StatementFormatter(simple_statement)
        
        # Mock method to create proper exception with validation_errors parameter
        def create_validation_error(message, validation_errors):
            return DataValidationError(message=message, validation_errors=validation_errors)
        
        # Patch StatementFormatter.generate_dataframe with our mock method
        with patch('fin_statement_model.core.errors.DataValidationError', side_effect=create_validation_error):
            # Mock validate_calculations to raise a different error
            with patch.object(formatter, 'validate_calculations', 
                            side_effect=ValueError("Unexpected error")):
                with pytest.raises(DataValidationError) as excinfo:
                    formatter.generate_dataframe(sample_data)
                
                assert "Statement data validation failed" in str(excinfo.value)
                assert "Unexpected error" in str(excinfo.value)
    
    def test_format_html(self, simple_statement, sample_data):
        """Test generating HTML from statement data."""
        formatter = StatementFormatter(simple_statement)
        
        # Create a mock DataFrame to return
        mock_df = pd.DataFrame({
            "Item": ["revenue", "cogs"],
            "Name": ["Revenue", "COGS"],
            "2021": [1000, -600],
            "2022": [1200, -700]
        })
        
        # Mock generate_dataframe to return our mock DataFrame
        with patch.object(formatter, 'generate_dataframe', return_value=mock_df):
            html = formatter.format_html(sample_data)
        
        # Check that HTML was generated
        assert isinstance(html, str)
        assert "<style>" in html
        assert "<h2>Income Statement</h2>" in html
        assert "<table" in html
        assert "Revenue" in html
        assert "COGS" in html
    
    def test_format_html_with_custom_styles(self, simple_statement, sample_data):
        """Test generating HTML with custom CSS styles."""
        formatter = StatementFormatter(simple_statement)
        
        # Create a mock DataFrame to return
        mock_df = pd.DataFrame({
            "Item": ["revenue"],
            "Name": ["Revenue"],
            "2021": [1000],
            "2022": [1200]
        })
        
        # Custom CSS styles
        custom_styles = {
            "table": "background-color: #f5f5f5;",
            "th": "color: blue;"
        }
        
        # Mock generate_dataframe to return our mock DataFrame
        with patch.object(formatter, 'generate_dataframe', return_value=mock_df):
            html = formatter.format_html(sample_data, css_styles=custom_styles)
        
        # Check that custom styles were applied
        assert "background-color: #f5f5f5" in html
        assert "color: blue" in html
    
    def test_format_html_error(self, simple_statement, sample_data):
        """Test handling errors in HTML generation."""
        formatter = StatementFormatter(simple_statement)
        
        # Mock method to create proper exception with validation_errors parameter
        def create_validation_error(message, validation_errors):
            return DataValidationError(message=message, validation_errors=validation_errors)
        
        # Patch DataValidationError with our mock method
        with patch('fin_statement_model.core.errors.DataValidationError', side_effect=create_validation_error):
            # Mock generate_dataframe to raise an error
            with patch.object(formatter, 'generate_dataframe', 
                            side_effect=ValueError("Test error")):
                with pytest.raises(DataValidationError) as excinfo:
                    formatter.format_html(sample_data)
                
                assert "Failed to format statement as HTML" in str(excinfo.value)
                assert "Test error" in str(excinfo.value)
    
    def test_get_calculation_dependencies(self, simple_statement):
        """Test getting calculation dependencies."""
        formatter = StatementFormatter(simple_statement)
        dependencies = formatter.get_calculation_dependencies()
        
        # Check that dependencies are correct
        assert "gross_profit" in dependencies
        assert "operating_profit" in dependencies
        assert "total_expenses" in dependencies
        
        assert set(dependencies["gross_profit"]) == {"revenue", "cogs"}
        assert set(dependencies["operating_profit"]) == {"gross_profit", "opex"}
        assert set(dependencies["total_expenses"]) == {"cogs", "opex"}
    
    def test_validate_calculations_valid(self, simple_statement, sample_data):
        """Test validating calculations with valid data."""
        formatter = StatementFormatter(simple_statement)
        
        # Mock get_calculation_dependencies
        dependencies = {
            "gross_profit": {"revenue", "cogs"},
            "operating_profit": {"gross_profit", "opex"},
            "total_expenses": {"cogs", "opex"}
        }
        with patch.object(formatter, 'get_calculation_dependencies', return_value=dependencies):
            # This should not raise an exception
            formatter.validate_calculations(sample_data)
    
    def test_validate_calculations_missing_result(self, simple_statement, sample_data):
        """Test validating calculations with missing result."""
        formatter = StatementFormatter(simple_statement)
        
        # Create data with missing calculation result
        incomplete_data = sample_data.copy()
        del incomplete_data["gross_profit"]
        
        # Mock method to create proper exception with validation_errors parameter
        def create_validation_error(message, validation_errors):
            return DataValidationError(message=message, validation_errors=validation_errors)
        
        # Mock get_calculation_dependencies
        dependencies = {
            "gross_profit": {"revenue", "cogs"},
            "operating_profit": {"gross_profit", "opex"}
        }
        
        # Patch DataValidationError with our mock method
        with patch('fin_statement_model.core.errors.DataValidationError', side_effect=create_validation_error):
            with patch.object(formatter, 'get_calculation_dependencies', return_value=dependencies):
                with pytest.raises(DataValidationError) as excinfo:
                    formatter.validate_calculations(incomplete_data)
                
                assert "Statement calculation validation failed" in str(excinfo.value)
                assert "Calculation result 'gross_profit' is missing" in str(excinfo.value)
    
    def test_validate_calculations_missing_dependency(self, simple_statement, sample_data):
        """Test validating calculations with missing dependency."""
        formatter = StatementFormatter(simple_statement)
        
        # Create data with missing dependency
        incomplete_data = sample_data.copy()
        del incomplete_data["cogs"]
        
        # Mock method to create proper exception with validation_errors parameter
        def create_validation_error(message, validation_errors):
            return DataValidationError(message=message, validation_errors=validation_errors)
        
        # Mock get_calculation_dependencies
        dependencies = {
            "gross_profit": {"revenue", "cogs"},
            "operating_profit": {"gross_profit", "opex"}
        }
        
        # Patch DataValidationError with our mock method
        with patch('fin_statement_model.core.errors.DataValidationError', side_effect=create_validation_error):
            with patch.object(formatter, 'get_calculation_dependencies', return_value=dependencies):
                with pytest.raises(DataValidationError) as excinfo:
                    formatter.validate_calculations(incomplete_data)
                
                assert "Statement calculation validation failed" in str(excinfo.value)
                assert "Missing dependencies for calculation 'gross_profit': cogs" in str(excinfo.value) 