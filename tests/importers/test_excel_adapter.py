"""Unit tests for excel_adapter module.

This module contains test cases for the Excel adapter functionality
of the Financial Statement Model, implemented in the ExcelAdapter class.
"""
import pytest
import pandas as pd
import numpy as np
import os
from unittest.mock import patch, MagicMock, mock_open, ANY

from fin_statement_model.importers.excel_adapter import ExcelAdapter
from fin_statement_model.core.financial_statement import FinancialStatementGraph


class TestExcelAdapter:
    """Test cases for the ExcelAdapter class."""
    
    class ConcreteExcelAdapter(ExcelAdapter):
        """Concrete implementation of ExcelAdapter for testing."""
        
        def extract_periods(self, *args, **kwargs):
            """Implement abstract method."""
            return self.extract_time_periods(*args, **kwargs)
    
    @pytest.fixture
    def mock_excel_file(self):
        """Return a mock Excel file path."""
        return "test_file.xlsx"
    
    @pytest.fixture
    def adapter(self):
        """Return a basic ExcelAdapter instance."""
        return self.ConcreteExcelAdapter()
    
    @pytest.fixture
    def mock_df(self):
        """Create a mock DataFrame for testing."""
        data = {
            'Item': ['Revenue', 'Cost of Revenue', 'Gross Profit', 'Operating Expenses'],
            'Period': ['2020', '2020', '2020', '2020'],
            '2020': [1000, 600, 400, 200],
            '2021': [1200, 700, 500, 250],
        }
        return pd.DataFrame(data)
    
    @pytest.fixture
    def mock_statement_data(self):
        """Create mock statement data dictionary."""
        return {
            'Revenue': {'2020': 1000, '2021': 1200},
            'Cost of Revenue': {'2020': 600, '2021': 700},
            'Gross Profit': {'2020': 400, '2021': 500},
            'Operating Expenses': {'2020': 200, '2021': 250},
        }
    
    def test_init_default(self, adapter):
        """Test initialization with default parameters."""
        assert adapter.file_path is None
        assert adapter.sheet_name is None
        assert adapter.period_column is None
        assert adapter.data is None
        
        # Check default mappings are initialized
        assert len(adapter.income_statement_field_mapping) > 0
        assert len(adapter.balance_sheet_field_mapping) > 0
        assert len(adapter.cash_flow_field_mapping) > 0
    
    def test_init_with_mapping_config(self):
        """Test initialization with custom mapping configuration."""
        custom_mapping = {
            'income_statement': {'Custom Field': 'custom_field'},
            'balance_sheet': {'Custom Asset': 'custom_asset'},
            'cash_flow': {'Custom Flow': 'custom_flow'},
        }
        
        adapter = self.ConcreteExcelAdapter(mapping_config=custom_mapping)
        
        # Check custom mappings were applied
        assert adapter.income_statement_field_mapping['Custom Field'] == 'custom_field'
        assert adapter.balance_sheet_field_mapping['Custom Asset'] == 'custom_asset'
        assert adapter.cash_flow_field_mapping['Custom Flow'] == 'custom_flow'
        
        # Check original mappings are still present
        assert adapter.income_statement_field_mapping['Revenue'] == 'revenue'
        assert adapter.balance_sheet_field_mapping['Cash & Cash Equivalents'] == 'cash_and_cash_equivalents'
        assert adapter.cash_flow_field_mapping['Operating Cash Flow'] == 'operating_cash_flow'
    
    @patch('os.path.exists')
    def test_validate_file_not_found(self, mock_exists, adapter, mock_excel_file):
        """Test validation of non-existent file."""
        mock_exists.return_value = False
        
        with pytest.raises(ValueError) as excinfo:
            adapter.validate_file(mock_excel_file)
        
        assert "File not found" in str(excinfo.value)
    
    def test_validate_file_invalid_extension(self, adapter):
        """Test validation of file with invalid extension."""
        with patch('os.path.exists', return_value=True):
            with pytest.raises(ValueError) as excinfo:
                adapter.validate_file("test_file.txt")
            
            assert "Not an Excel file" in str(excinfo.value)
    
    @patch('os.path.exists')
    @patch('pandas.ExcelFile')
    def test_validate_file_pandas_error(self, mock_excel_file_class, mock_exists, adapter, mock_excel_file):
        """Test validation when pandas raises an error."""
        mock_exists.return_value = True
        mock_excel_file_class.side_effect = Exception("Test error")
        
        with pytest.raises(ValueError) as excinfo:
            adapter.validate_file(mock_excel_file)
        
        assert "Error validating Excel file" in str(excinfo.value)
    
    @patch('os.path.exists')
    @patch('pandas.ExcelFile')
    def test_validate_file_success(self, mock_excel_file_class, mock_exists, adapter, mock_excel_file):
        """Test successful file validation."""
        mock_exists.return_value = True
        mock_excel_file_class.return_value = MagicMock()
        
        result = adapter.validate_file(mock_excel_file)
        
        assert result is True
        mock_excel_file_class.assert_called_once_with(mock_excel_file)
    
    @patch('pandas.read_excel')
    def test_extract_time_periods_column_not_found(self, mock_read_excel, adapter, mock_excel_file):
        """Test extract_time_periods when period column doesn't exist."""
        mock_df = pd.DataFrame({'OtherColumn': [1, 2, 3]})
        mock_read_excel.return_value = mock_df
        
        with pytest.raises(ValueError) as excinfo:
            adapter.extract_time_periods(mock_excel_file, 'Sheet1', 'Period')
        
        assert "Period column 'Period' not found" in str(excinfo.value)
        mock_read_excel.assert_called_once_with(mock_excel_file, sheet_name='Sheet1')
    
    @patch('pandas.read_excel')
    def test_extract_time_periods_pandas_error(self, mock_read_excel, adapter, mock_excel_file):
        """Test extract_time_periods when pandas raises an error."""
        mock_read_excel.side_effect = Exception("Test error")
        
        with pytest.raises(ValueError) as excinfo:
            adapter.extract_time_periods(mock_excel_file, 'Sheet1', 'Period')
        
        assert "Error extracting time periods" in str(excinfo.value)
    
    @patch('pandas.read_excel')
    def test_extract_time_periods_success(self, mock_read_excel, adapter, mock_excel_file, mock_df):
        """Test successful extraction of time periods."""
        mock_read_excel.return_value = mock_df
        
        periods = adapter.extract_time_periods(mock_excel_file, 'Sheet1', 'Period')
        
        assert periods == ['2020']
        mock_read_excel.assert_called_once_with(mock_excel_file, sheet_name='Sheet1')
    
    def test_fetch_statement_invalid_type(self, adapter, mock_excel_file):
        """Test fetch_statement with invalid statement type."""
        with pytest.raises(ValueError) as excinfo:
            adapter.fetch_statement(mock_excel_file, 'Sheet1', 'Period', 'invalid_type')
        
        assert "Invalid statement type" in str(excinfo.value)
    
    @patch('tests.importers.test_excel_adapter.TestExcelAdapter.ConcreteExcelAdapter.validate_file')
    @patch('pandas.read_excel')
    def test_fetch_statement_pandas_error(self, mock_read_excel, mock_validate, adapter, mock_excel_file):
        """Test fetch_statement when pandas raises an error."""
        mock_validate.return_value = True
        mock_read_excel.side_effect = Exception("Test error")
        
        with pytest.raises(ValueError) as excinfo:
            adapter.fetch_statement(mock_excel_file, 'Sheet1', 'Period')
        
        assert "Error fetching data from Excel file" in str(excinfo.value)
        mock_validate.assert_called_once_with(mock_excel_file)
    
    @patch('tests.importers.test_excel_adapter.TestExcelAdapter.ConcreteExcelAdapter.validate_file')
    @patch('pandas.read_excel')
    def test_fetch_statement_success(self, mock_read_excel, mock_validate, adapter, mock_excel_file, mock_df, mock_statement_data):
        """Test successful fetching of statement data."""
        mock_validate.return_value = True
        mock_read_excel.return_value = mock_df
        
        result = adapter.fetch_statement(mock_excel_file, 'Sheet1', 'Period', 'income_statement')
        
        # Check properties were updated
        assert adapter.file_path == mock_excel_file
        assert adapter.sheet_name == 'Sheet1'
        assert adapter.period_column == 'Period'
        assert adapter.data is not None
        
        # Check result format
        assert 'Revenue' in result
        assert 'Cost of Revenue' in result
        assert 'Gross Profit' in result
        assert 'Operating Expenses' in result
        
        # Check a specific value
        assert '2020' in result['Revenue']
        assert result['Revenue']['2020'] == 1000
    
    def test_get_field_mapping_income_statement(self, adapter):
        """Test getting field mapping for income statement."""
        mapping = adapter.get_field_mapping('income_statement')
        assert mapping == adapter.income_statement_field_mapping
        assert 'Revenue' in mapping
        assert mapping['Revenue'] == 'revenue'
    
    def test_get_field_mapping_balance_sheet(self, adapter):
        """Test getting field mapping for balance sheet."""
        mapping = adapter.get_field_mapping('balance_sheet')
        assert mapping == adapter.balance_sheet_field_mapping
        assert 'Cash & Cash Equivalents' in mapping
        assert mapping['Cash & Cash Equivalents'] == 'cash_and_cash_equivalents'
    
    def test_get_field_mapping_cash_flow(self, adapter):
        """Test getting field mapping for cash flow."""
        mapping = adapter.get_field_mapping('cash_flow')
        assert mapping == adapter.cash_flow_field_mapping
        assert 'Operating Cash Flow' in mapping
        assert mapping['Operating Cash Flow'] == 'operating_cash_flow'
    
    def test_get_field_mapping_invalid_type(self, adapter):
        """Test getting field mapping with invalid statement type."""
        with pytest.raises(ValueError) as excinfo:
            adapter.get_field_mapping('invalid_type')
        
        assert "Invalid statement type" in str(excinfo.value)
    
    @patch('tests.importers.test_excel_adapter.TestExcelAdapter.ConcreteExcelAdapter.fetch_statement')
    @patch('tests.importers.test_excel_adapter.TestExcelAdapter.ConcreteExcelAdapter.get_field_mapping')
    @patch('tests.importers.test_excel_adapter.TestExcelAdapter.ConcreteExcelAdapter.extract_time_periods')
    @patch('tests.importers.test_excel_adapter.TestExcelAdapter.ConcreteExcelAdapter._add_common_calculations')
    def test_create_statement_graph_exception(self, mock_add_calcs, mock_extract, mock_mapping, mock_fetch, adapter, mock_excel_file):
        """Test create_statement_graph when an exception is raised."""
        mock_fetch.side_effect = Exception("Test error")
        
        with pytest.raises(ValueError) as excinfo:
            adapter.create_statement_graph(mock_excel_file, 'Sheet1', 'Period')
        
        assert "Error creating statement graph from Excel" in str(excinfo.value)
        mock_fetch.assert_called_once_with(mock_excel_file, 'Sheet1', 'Period', 'income_statement')
        mock_mapping.assert_not_called()
        mock_extract.assert_not_called()
        mock_add_calcs.assert_not_called()
    
    @patch('tests.importers.test_excel_adapter.TestExcelAdapter.ConcreteExcelAdapter.fetch_statement')
    @patch('tests.importers.test_excel_adapter.TestExcelAdapter.ConcreteExcelAdapter.get_field_mapping')
    @patch('tests.importers.test_excel_adapter.TestExcelAdapter.ConcreteExcelAdapter.extract_time_periods')
    @patch('tests.importers.test_excel_adapter.TestExcelAdapter.ConcreteExcelAdapter._add_common_calculations')
    def test_create_statement_graph_success(self, mock_add_calcs, mock_extract, mock_mapping, mock_fetch, adapter, mock_excel_file, mock_statement_data):
        """Test successful creation of statement graph."""
        # Mock the dependencies
        mock_fetch.return_value = mock_statement_data
        mock_mapping.return_value = {
            'Revenue': 'revenue',
            'Cost of Revenue': 'cost_of_goods_sold',
            'Gross Profit': 'gross_profit',
            'Operating Expenses': 'operating_expenses',
        }
        mock_extract.return_value = ['2020', '2021']
        
        # Call the method
        result = adapter.create_statement_graph(mock_excel_file, 'Sheet1', 'Period')
        
        # Check the result
        assert isinstance(result, FinancialStatementGraph)
        assert 'revenue' in result.graph.nodes
        assert 'cost_of_goods_sold' in result.graph.nodes
        assert 'gross_profit' in result.graph.nodes
        assert 'operating_expenses' in result.graph.nodes
        
        # Check the method calls
        mock_fetch.assert_called_once_with(mock_excel_file, 'Sheet1', 'Period', 'income_statement')
        mock_mapping.assert_called_once_with('income_statement')
        mock_extract.assert_called_once_with(mock_excel_file, 'Sheet1', 'Period')
        mock_add_calcs.assert_called_once_with(result, 'income_statement')
    
    @patch('tests.importers.test_excel_adapter.TestExcelAdapter.ConcreteExcelAdapter.fetch_statement')
    @patch('tests.importers.test_excel_adapter.TestExcelAdapter.ConcreteExcelAdapter.get_field_mapping')
    @patch('tests.importers.test_excel_adapter.TestExcelAdapter.ConcreteExcelAdapter.extract_time_periods')
    @patch('tests.importers.test_excel_adapter.TestExcelAdapter.ConcreteExcelAdapter._add_common_calculations')
    def test_create_statement_graph_with_nan_values(self, mock_add_calcs, mock_extract, mock_mapping, mock_fetch, adapter, mock_excel_file):
        """Test creation of statement graph with NaN values in the data."""
        # Create data with NaN values
        data_with_nan = {
            'Revenue': {'2020': 1000, '2021': np.nan},
            'Cost of Revenue': {'2020': 600, '2021': 700},
            'Gross Profit': {'2020': np.nan, '2021': 500},
            'Operating Expenses': {'2020': 200, '2021': 250},
        }
        
        # Mock the dependencies
        mock_fetch.return_value = data_with_nan
        mock_mapping.return_value = {
            'Revenue': 'revenue',
            'Cost of Revenue': 'cost_of_goods_sold',
            'Gross Profit': 'gross_profit',
            'Operating Expenses': 'operating_expenses',
        }
        mock_extract.return_value = ['2020', '2021']
        
        # Call the method
        result = adapter.create_statement_graph(mock_excel_file, 'Sheet1', 'Period')
        
        # Check that nodes were created
        assert 'revenue' in result.graph.nodes
        assert 'cost_of_goods_sold' in result.graph.nodes
        assert 'gross_profit' in result.graph.nodes
        assert 'operating_expenses' in result.graph.nodes
        
        # Check the fetch, mapping and extract calls were made
        mock_fetch.assert_called_once_with(mock_excel_file, 'Sheet1', 'Period', 'income_statement')
        mock_mapping.assert_called_once_with('income_statement')
        mock_extract.assert_called_once_with(mock_excel_file, 'Sheet1', 'Period')
    
    def test_add_common_calculations_income_statement(self, adapter):
        """Test adding common calculations for income statement."""
        # Create a minimal graph with income statement data
        fsg = FinancialStatementGraph(periods=['2020'])
        fsg.add_financial_statement_item('revenue', {'2020': 1000})
        fsg.add_financial_statement_item('cost_of_goods_sold', {'2020': 600})
        
        # Add common calculations
        adapter._add_common_calculations(fsg, 'income_statement')
        
        # Check calculations were added
        assert 'gross_profit' in fsg.graph.nodes
        # Just verify the node exists and is a calculation node
        assert hasattr(fsg.graph.nodes['gross_profit'], 'calculate')
    
    def test_add_common_calculations_balance_sheet(self, adapter):
        """Test adding common calculations for balance sheet."""
        # Create a minimal graph with balance sheet data
        fsg = FinancialStatementGraph(periods=['2020'])
        fsg.add_financial_statement_item('cash_and_cash_equivalents', {'2020': 500})
        fsg.add_financial_statement_item('short_term_investments', {'2020': 300})
        
        # Add common calculations
        adapter._add_common_calculations(fsg, 'balance_sheet')
        
        # Check calculations were added
        assert 'cash_and_short_term_investments' in fsg.graph.nodes
        # Just verify the node exists and is a calculation node
        assert hasattr(fsg.graph.nodes['cash_and_short_term_investments'], 'calculate')
    
    def test_add_common_calculations_cash_flow(self, adapter):
        """Test adding common calculations for cash flow."""
        # Create a minimal graph with cash flow data
        fsg = FinancialStatementGraph(periods=['2020'])
        fsg.add_financial_statement_item('operating_cash_flow', {'2020': 800})
        fsg.add_financial_statement_item('capital_expenditure', {'2020': -300})
        
        # Add common calculations
        adapter._add_common_calculations(fsg, 'cash_flow')
        
        # Check calculations were added
        assert 'free_cash_flow' in fsg.graph.nodes
        # Just verify the node exists and is a calculation node
        assert hasattr(fsg.graph.nodes['free_cash_flow'], 'calculate')
    
    def test_add_common_calculations_exception(self, adapter):
        """Test adding common calculations with exception handling."""
        # Create a graph
        fsg = FinancialStatementGraph(periods=['2020'])
        
        # Mock add_calculation to raise an exception
        with patch.object(FinancialStatementGraph, 'add_calculation', side_effect=Exception("Test error")):
            # This should not raise an exception
            adapter._add_common_calculations(fsg, 'income_statement')
    
    def test_add_common_calculations_exception_handling(self, adapter):
        """Test exception handling in _add_common_calculations."""
        # Create a test graph
        fsg = FinancialStatementGraph(periods=['2020'])
        
        # Patch _try_add_calculation to throw an exception when called with certain parameters
        with patch.object(adapter, '_try_add_calculation') as mock_try_add:
            # Set up the mock to throw an exception when called
            mock_try_add.side_effect = Exception("Test exception")
            
            # This should not raise an exception due to try-except block
            adapter._add_common_calculations(fsg, 'cash_flow')
            
            # Verify the method was called and exception was caught
            mock_try_add.assert_called()
    
    def test_try_add_calculation_success(self, adapter):
        """Test _try_add_calculation with successful calculation."""
        # Create a graph with valid inputs
        fsg = FinancialStatementGraph(periods=['2020'])
        fsg.add_financial_statement_item('input1', {'2020': 500})
        fsg.add_financial_statement_item('input2', {'2020': 300})
        
        # Try to add calculation
        result = adapter._try_add_calculation(fsg, 'output', ['input1', 'input2'], 'addition')
        
        # Check result
        assert result is True
        assert 'output' in fsg.graph.nodes
        # Just verify the node exists and is a calculation node
        assert hasattr(fsg.graph.nodes['output'], 'calculate')
    
    def test_try_add_calculation_missing_inputs(self, adapter):
        """Test _try_add_calculation with missing inputs."""
        # Create a graph with only some inputs
        fsg = FinancialStatementGraph(periods=['2020'])
        fsg.add_financial_statement_item('input1', {'2020': 500})
        
        # Try to add calculation with missing input
        result = adapter._try_add_calculation(fsg, 'output', ['input1', 'missing_input'], 'addition')
        
        # Check result - should still add using available inputs
        assert result is True
        assert 'output' in fsg.graph.nodes
        # Just verify the node exists and is a calculation node
        assert hasattr(fsg.graph.nodes['output'], 'calculate')
    
    def test_try_add_calculation_no_inputs(self, adapter):
        """Test _try_add_calculation with no valid inputs."""
        # Create an empty graph
        fsg = FinancialStatementGraph(periods=['2020'])
        
        # Try to add calculation with all inputs missing
        result = adapter._try_add_calculation(fsg, 'output', ['missing1', 'missing2'], 'addition')
        
        # Check result
        assert result is False
        assert 'output' not in fsg.graph.nodes
    
    def test_try_add_calculation_exception(self, adapter):
        """Test _try_add_calculation with exception handling."""
        # Create a graph with valid inputs
        fsg = FinancialStatementGraph(periods=['2020'])
        fsg.add_financial_statement_item('input1', {'2020': 500})
        
        # Mock add_calculation to raise an exception
        with patch.object(FinancialStatementGraph, 'add_calculation', side_effect=Exception("Test error")):
            # Try to add calculation
            result = adapter._try_add_calculation(fsg, 'output', ['input1'], 'invalid_operation')
            
            # Check result
            assert result is False
            assert 'output' not in fsg.graph.nodes
    
    def test_try_add_calculation_with_specific_operations(self, adapter):
        """Test _try_add_calculation with different operation types."""
        # Create a graph with valid inputs
        fsg = FinancialStatementGraph(periods=['2020'])
        fsg.add_financial_statement_item('input1', {'2020': 500})
        fsg.add_financial_statement_item('input2', {'2020': 100})
        
        # Test subtraction
        subtraction_result = adapter._try_add_calculation(fsg, 'subtraction_out', ['input1', 'input2'], 'subtraction')
        assert subtraction_result is True
        assert 'subtraction_out' in fsg.graph.nodes
        
        # Test multiplication
        multiplication_result = adapter._try_add_calculation(fsg, 'multiplication_out', ['input1', 'input2'], 'multiplication')
        assert multiplication_result is True
        assert 'multiplication_out' in fsg.graph.nodes
        
        # Test division
        division_result = adapter._try_add_calculation(fsg, 'division_out', ['input1', 'input2'], 'division')
        assert division_result is True
        assert 'division_out' in fsg.graph.nodes 