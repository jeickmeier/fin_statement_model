"""Unit tests for create_financial_statement utility function.

This module contains test cases for the financial statement creation utility
functions in fin_statement_model/utils/create_financial_statement.py.
"""
import pytest
from unittest.mock import Mock, patch, call

from fin_statement_model.utils.create_financial_statement import create_financial_statement
from fin_statement_model.core.financial_statement import FinancialStatementGraph


class TestCreateFinancialStatement:
    """Test cases for the create_financial_statement function."""

    def test_empty_cells_list(self):
        """Test creating a financial statement with an empty cells list."""
        # Execute
        result = create_financial_statement([])
        
        # Verify
        assert isinstance(result, FinancialStatementGraph)
        assert len(result.graph.nodes) == 0
        assert len(result.graph.periods) == 0

    def test_cells_with_missing_data(self):
        """Test creating a financial statement with cells missing required data."""
        # Setup - cells with missing row_name, column_name, or value
        cells_info = [
            {
                'cell_location': 'A1',
                'value': 100
                # Missing row_name and column_name
            },
            {
                'cell_location': 'B1',
                'row_name': 'Revenue',
                # Missing column_name
                'value': 200
            },
            {
                'cell_location': 'C1',
                'column_name': '2022',
                # Missing row_name
                'value': 300
            },
            {
                'cell_location': 'D1',
                'row_name': 'Expenses',
                'column_name': '2022'
                # Missing value
            }
        ]
        
        # Execute
        result = create_financial_statement(cells_info)
        
        # Verify
        assert isinstance(result, FinancialStatementGraph)
        # Only second and third cells should be processed (and might not be processed completely)
        assert len(result.graph.nodes) <= 2  # Could be 0, 1, or 2 depending on implementation

    def test_single_item_single_period(self):
        """Test creating a financial statement with a single item and period."""
        # Setup
        cells_info = [
            {
                'cell_location': 'B2',
                'row_name': 'Revenue',
                'column_name': '2022',
                'value': 1000
            }
        ]
        
        # Execute
        result = create_financial_statement(cells_info)
        
        # Verify
        assert isinstance(result, FinancialStatementGraph)
        assert len(result.graph.periods) == 1
        assert '2022' in result.graph.periods
        assert len(result.graph.nodes) == 1
        assert 'Revenue' in [node.name for node in result.graph.nodes.values()]
        
        # Retrieve the revenue node and check its value
        revenue_node = None
        for node in result.graph.nodes.values():
            if node.name == 'Revenue':
                revenue_node = node
                break
        
        assert revenue_node is not None
        assert revenue_node.values['2022'] == 1000

    def test_multiple_items_multiple_periods(self):
        """Test creating a financial statement with multiple items and periods."""
        # Setup
        cells_info = [
            {
                'cell_location': 'B2',
                'row_name': 'Revenue',
                'column_name': '2021',
                'value': 1000
            },
            {
                'cell_location': 'C2',
                'row_name': 'Revenue',
                'column_name': '2022',
                'value': 1100
            },
            {
                'cell_location': 'B3',
                'row_name': 'Expenses',
                'column_name': '2021',
                'value': 600
            },
            {
                'cell_location': 'C3',
                'row_name': 'Expenses',
                'column_name': '2022',
                'value': 660
            }
        ]
        
        # Execute
        result = create_financial_statement(cells_info)
        
        # Verify
        assert isinstance(result, FinancialStatementGraph)
        assert len(result.graph.periods) == 2
        assert set(result.graph.periods) == {'2021', '2022'}
        assert len(result.graph.nodes) == 2
        
        # Check node names
        node_names = [node.name for node in result.graph.nodes.values()]
        assert 'Revenue' in node_names
        assert 'Expenses' in node_names
        
        # Check node values
        for node in result.graph.nodes.values():
            if node.name == 'Revenue':
                assert node.values['2021'] == 1000
                assert node.values['2022'] == 1100
            elif node.name == 'Expenses':
                assert node.values['2021'] == 600
                assert node.values['2022'] == 660

    def test_whitespace_in_names(self):
        """Test creating a financial statement with whitespace in row and column names."""
        # Setup
        cells_info = [
            {
                'cell_location': 'B2',
                'row_name': '  Revenue  ',  # Extra whitespace
                'column_name': '  2022  ',  # Extra whitespace
                'value': 1000
            }
        ]
        
        # Execute
        result = create_financial_statement(cells_info)
        
        # Verify
        assert isinstance(result, FinancialStatementGraph)
        assert len(result.graph.periods) == 1
        assert '2022' in result.graph.periods  # Whitespace should be stripped
        
        # Check node name (whitespace should be stripped)
        node_names = [node.name for node in result.graph.nodes.values()]
        assert 'Revenue' in node_names
        
        # Check node value
        for node in result.graph.nodes.values():
            if node.name == 'Revenue':
                assert node.values['2022'] == 1000

    def test_period_sorting(self):
        """Test that periods are correctly sorted in the financial statement."""
        # Setup - provide periods in non-chronological order
        cells_info = [
            {
                'cell_location': 'C2',
                'row_name': 'Revenue',
                'column_name': '2023',
                'value': 1200
            },
            {
                'cell_location': 'B2',
                'row_name': 'Revenue',
                'column_name': '2021',
                'value': 1000
            },
            {
                'cell_location': 'D2',
                'row_name': 'Revenue',
                'column_name': '2022',
                'value': 1100
            }
        ]
        
        # Execute
        result = create_financial_statement(cells_info)
        
        # Verify
        assert isinstance(result, FinancialStatementGraph)
        assert len(result.graph.periods) == 3
        # Periods should be sorted chronologically
        assert list(result.graph.periods) == ['2021', '2022', '2023']

    def test_financial_statement_graph_initialization(self):
        """Test that FinancialStatementGraph is initialized with the correct periods."""
        # Setup
        cells_info = [
            {
                'cell_location': 'B2',
                'row_name': 'Revenue',
                'column_name': '2021',
                'value': 1000
            },
            {
                'cell_location': 'C2',
                'row_name': 'Revenue',
                'column_name': '2022',
                'value': 1100
            }
        ]
        
        # Execute
        result = create_financial_statement(cells_info)
        
        # Verify
        assert isinstance(result, FinancialStatementGraph)
        assert result.graph.periods == ['2021', '2022']

    def test_add_financial_statement_item_integration(self):
        """Test add_financial_statement_item integration using real instances."""
        # Setup
        cells_info = [
            {
                'cell_location': 'B2',
                'row_name': 'Revenue',
                'column_name': '2021',
                'value': 1000
            },
            {
                'cell_location': 'C2',
                'row_name': 'Revenue',
                'column_name': '2022',
                'value': 1100
            },
            {
                'cell_location': 'B3',
                'row_name': 'Expenses',
                'column_name': '2021',
                'value': 600
            }
        ]
        
        # Execute
        result = create_financial_statement(cells_info)
        
        # Verify
        assert isinstance(result, FinancialStatementGraph)
        
        # Check that nodes were created with correct values
        node_names = [node.name for node in result.graph.nodes.values()]
        assert 'Revenue' in node_names
        assert 'Expenses' in node_names
        
        # Check node values
        revenue_node = None
        expenses_node = None
        
        for node in result.graph.nodes.values():
            if node.name == 'Revenue':
                revenue_node = node
            elif node.name == 'Expenses':
                expenses_node = node
        
        assert revenue_node is not None
        assert expenses_node is not None
        
        assert revenue_node.values['2021'] == 1000
        assert revenue_node.values['2022'] == 1100
        assert expenses_node.values['2021'] == 600
        assert '2022' not in expenses_node.values
        
    def test_cells_with_formula_information(self):
        """Test creating a financial statement with cells that include formula information."""
        # Setup - cells including formula and precedent information
        cells_info = [
            {
                'cell_location': 'B2',
                'row_name': 'Revenue',
                'column_name': '2021',
                'value': 1000,
                'formula': None  # No formula
            },
            {
                'cell_location': 'B3',
                'row_name': 'Expenses',
                'column_name': '2021',
                'value': 600,
                'formula': None  # No formula
            },
            {
                'cell_location': 'B4',
                'row_name': 'Profit',
                'column_name': '2021',
                'value': 400,
                'formula': '=B2-B3',  # Formula
                'precedents': ['B2', 'B3'],
                'formula_with_row_names': '=Revenue-Expenses',
                'precedents_names': ['Revenue', 'Expenses']
            }
        ]
        
        # Execute
        result = create_financial_statement(cells_info)
        
        # Verify
        assert isinstance(result, FinancialStatementGraph)
        assert len(result.graph.periods) == 1
        assert '2021' in result.graph.periods
        assert len(result.graph.nodes) == 3
        
        # Check node names
        node_names = [node.name for node in result.graph.nodes.values()]
        assert 'Revenue' in node_names
        assert 'Expenses' in node_names
        assert 'Profit' in node_names
        
        # Check node values
        for node in result.graph.nodes.values():
            if node.name == 'Revenue':
                assert node.values['2021'] == 1000
            elif node.name == 'Expenses':
                assert node.values['2021'] == 600
            elif node.name == 'Profit':
                assert node.values['2021'] == 400 