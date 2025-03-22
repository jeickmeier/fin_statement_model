"""Unit tests for fmp module.

This module contains test cases for the FMP adapter functionality
of the Financial Statement Model, implemented in the FMPAdapter class.
"""
import pytest
import os
import pandas as pd
from unittest.mock import patch, MagicMock, call
import requests

from fin_statement_model.importers.fmp import FMPAdapter
from fin_statement_model.core.financial_statement import FinancialStatementGraph


class TestFMPAdapter:
    """Test cases for the FMPAdapter class."""
    
    @pytest.fixture
    def adapter(self):
        """Return a basic FMPAdapter instance with a mock API key."""
        with patch('fin_statement_model.importers.fmp.FMPAdapter.authenticate') as mock_auth:
            # Mock the authenticate method to avoid actual authentication
            mock_auth.return_value = True
            adapter = FMPAdapter(api_key="test_api_key")
            return adapter
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock response for API requests."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                "date": "2021-12-31",
                "revenue": 1000,
                "costOfRevenue": 600,
                "grossProfit": 400,
                "netIncome": 200
            },
            {
                "date": "2020-12-31",
                "revenue": 800,
                "costOfRevenue": 500,
                "grossProfit": 300,
                "netIncome": 150
            }
        ]
        return mock_resp
    
    @pytest.fixture
    def mock_empty_response(self):
        """Create a mock empty response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        return mock_resp
    
    @pytest.fixture
    def mock_error_response(self):
        """Create a mock error response for API requests."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"error": "Unauthorized"}
        return mock_resp
    
    def test_init_with_api_key(self):
        """Test initialization with API key."""
        with patch('fin_statement_model.importers.fmp.FMPAdapter.authenticate') as mock_auth:
            mock_auth.return_value = True
            adapter = FMPAdapter(api_key="test_api_key")
            
            assert adapter.api_key == "test_api_key"
            assert adapter.base_url == "https://financialmodelingprep.com/api/v3"
            mock_auth.assert_called_once()
            
            # Check that field mappings are initialized
            assert len(adapter.income_statement_field_mapping) > 0
            assert len(adapter.balance_sheet_field_mapping) > 0
            assert len(adapter.cash_flow_field_mapping) > 0
    
    def test_init_without_api_key(self):
        """Test initialization without API key."""
        with patch('fin_statement_model.importers.fmp.FMPAdapter.authenticate') as mock_auth:
            mock_auth.return_value = True
            adapter = FMPAdapter()
            
            assert adapter.api_key is None
            assert adapter.base_url == "https://financialmodelingprep.com/api/v3"
            assert not mock_auth.called
    
    def test_init_field_mappings(self, adapter):
        """Test initialization of field mappings."""
        # Income statement mappings
        assert adapter.income_statement_field_mapping["revenue"] == "revenue"
        assert adapter.income_statement_field_mapping["grossProfit"] == "gross_profit"
        
        # Balance sheet mappings
        assert adapter.balance_sheet_field_mapping["cashAndCashEquivalents"] == "cash_and_cash_equivalents"
        assert adapter.balance_sheet_field_mapping["totalAssets"] == "total_assets"
        
        # Cash flow mappings
        assert adapter.cash_flow_field_mapping["netIncome"] == "net_income"
        assert adapter.cash_flow_field_mapping["operatingCashFlow"] == "operating_cash_flow"
    
    @patch('requests.get')
    def test_authenticate_with_api_key(self, mock_get):
        """Test authentication with API key."""
        # Create fresh adapter without using the fixture
        adapter = FMPAdapter(api_key="new_test_api_key")
        
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Reset the mock to clear any previous calls
        mock_get.reset_mock()
        
        result = adapter.authenticate()
        
        assert result is True
        mock_get.assert_called_once_with(
            "https://financialmodelingprep.com/api/v3/stock/list?apikey=new_test_api_key",
            timeout=10
        )
    
    @patch('os.environ.get')
    @patch('requests.get')
    def test_authenticate_with_environment_variable(self, mock_get, mock_environ_get):
        """Test authentication using environment variable."""
        mock_environ_get.return_value = "env_api_key"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        adapter = FMPAdapter()  # No API key provided
        result = adapter.authenticate()
        
        assert result is True
        assert adapter.api_key == "env_api_key"
        mock_environ_get.assert_called_once_with('FMP_API_KEY')
        mock_get.assert_called_with(
            "https://financialmodelingprep.com/api/v3/stock/list?apikey=env_api_key",
            timeout=10
        )
    
    @patch('os.environ.get')
    def test_authenticate_no_api_key(self, mock_environ_get):
        """Test authentication failure when no API key is available."""
        mock_environ_get.return_value = None
        
        adapter = FMPAdapter()  # No API key provided
        
        with pytest.raises(ValueError) as excinfo:
            adapter.authenticate()
        
        assert "No API key provided" in str(excinfo.value)
        mock_environ_get.assert_called_once_with('FMP_API_KEY')
    
    @patch('requests.get')
    def test_authenticate_failed_request(self, mock_get):
        """Test authentication when the API request fails."""
        # Create fresh adapter without using the fixture
        adapter = FMPAdapter(api_key="test_api_key")
        
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 401  # Unauthorized
        mock_get.return_value = mock_response
        
        # Reset the mock to clear any previous calls
        mock_get.reset_mock()
        
        result = adapter.authenticate()
        
        assert result is False
        mock_get.assert_called_once_with(
            "https://financialmodelingprep.com/api/v3/stock/list?apikey=test_api_key",
            timeout=10
        )
    
    @patch('requests.get')
    def test_authenticate_exception(self, mock_get):
        """Test authentication when the request raises an exception."""
        # Create fresh adapter without using the fixture
        adapter = FMPAdapter(api_key="test_api_key")
        
        # Configure mock to raise exception
        mock_get.side_effect = Exception("Connection error")
        
        # Reset the mock to clear any previous calls
        mock_get.reset_mock()
        
        result = adapter.authenticate()
        
        assert result is False
        mock_get.assert_called_once_with(
            "https://financialmodelingprep.com/api/v3/stock/list?apikey=test_api_key",
            timeout=10
        )
    
    def test_validate_response_valid(self, adapter, mock_response):
        """Test validating a valid API response."""
        data = mock_response.json()
        result = adapter.validate_response(data)
        
        assert result is True
    
    def test_validate_response_not_list(self, adapter):
        """Test validating a response that's not a list."""
        data = {"error": "Not a list"}
        result = adapter.validate_response(data)
        
        assert result is False
    
    def test_validate_response_empty(self, adapter):
        """Test validating an empty response."""
        data = []
        result = adapter.validate_response(data)
        
        assert result is False
    
    def test_validate_response_missing_field(self, adapter):
        """Test validating a response missing expected fields."""
        data = [{"symbol": "AAPL", "name": "Apple Inc."}]  # Missing 'date' field
        result = adapter.validate_response(data)
        
        assert result is False
    
    @patch('requests.get')
    def test_fetch_statement_success(self, mock_get, adapter, mock_response):
        """Test successfully fetching a financial statement."""
        mock_get.return_value = mock_response
        
        result = adapter.fetch_statement("AAPL", "FY", 5, "income_statement")
        
        assert result == mock_response.json()
        mock_get.assert_called_once_with(
            "https://financialmodelingprep.com/api/v3/income-statement/AAPL?apikey=test_api_key&period=FY&limit=5",
            timeout=10
        )
    
    @patch('requests.get')
    def test_fetch_statement_balance_sheet(self, mock_get, adapter, mock_response):
        """Test fetching a balance sheet statement."""
        mock_get.return_value = mock_response
        
        adapter.fetch_statement("AAPL", "FY", 5, "balance_sheet")
        
        mock_get.assert_called_once_with(
            "https://financialmodelingprep.com/api/v3/balance-sheet-statement/AAPL?apikey=test_api_key&period=FY&limit=5",
            timeout=10
        )
    
    @patch('requests.get')
    def test_fetch_statement_cash_flow(self, mock_get, adapter, mock_response):
        """Test fetching a cash flow statement."""
        mock_get.return_value = mock_response
        
        adapter.fetch_statement("AAPL", "FY", 5, "cash_flow")
        
        mock_get.assert_called_once_with(
            "https://financialmodelingprep.com/api/v3/cash-flow-statement/AAPL?apikey=test_api_key&period=FY&limit=5",
            timeout=10
        )
    
    def test_fetch_statement_invalid_type(self, adapter):
        """Test fetching a statement with an invalid type."""
        with pytest.raises(ValueError) as excinfo:
            adapter.fetch_statement("AAPL", "FY", 5, "invalid_type")
        
        assert "Invalid statement type" in str(excinfo.value)
    
    @patch('requests.get')
    def test_fetch_statement_request_error(self, mock_get, adapter):
        """Test fetching a statement when the request fails."""
        mock_response = MagicMock()
        mock_response.status_code = 404  # Not found
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError) as excinfo:
            adapter.fetch_statement("AAPL", "FY", 5, "income_statement")
        
        assert "Failed to fetch data" in str(excinfo.value)
    
    @patch('requests.get')
    @patch('fin_statement_model.importers.fmp.FMPAdapter.validate_response')
    def test_fetch_statement_invalid_response(self, mock_validate, mock_get, adapter, mock_response):
        """Test fetching a statement with an invalid response."""
        mock_get.return_value = mock_response
        mock_validate.return_value = False
        
        with pytest.raises(ValueError) as excinfo:
            adapter.fetch_statement("AAPL", "FY", 5, "income_statement")
        
        assert "Invalid response from FMP API" in str(excinfo.value)
    
    @patch('requests.get')
    def test_fetch_statement_request_exception(self, mock_get, adapter):
        """Test fetching a statement when the request raises an exception."""
        # Use side_effect to raise a requests exception specifically
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        # Use pytest.raises to catch the ValueError that should be raised
        with pytest.raises(ValueError) as excinfo:
            adapter.fetch_statement("AAPL", "FY", 5, "income_statement")
        
        # Check that the error message contains the expected text
        assert "Error fetching data from FMP API" in str(excinfo.value)
        assert "Connection error" in str(excinfo.value)
    
    @patch('requests.get')
    def test_fetch_statement_json_parse_exception(self, mock_get, adapter):
        """Test fetching a statement when JSON parsing fails."""
        # Mock a successful response but make json() raise an exception
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        # Use pytest.raises to catch the ValueError that should be raised
        with pytest.raises(ValueError) as excinfo:
            adapter.fetch_statement("AAPL", "FY", 5, "income_statement")
        
        # Check that the error message contains the expected text
        assert "Error fetching data from FMP API" in str(excinfo.value)
        assert "Invalid JSON" in str(excinfo.value)
    
    def test_get_field_mapping_income_statement(self, adapter):
        """Test getting field mapping for income statement."""
        mapping = adapter.get_field_mapping("income_statement")
        
        assert mapping == adapter.income_statement_field_mapping
        assert "revenue" in mapping
    
    def test_get_field_mapping_balance_sheet(self, adapter):
        """Test getting field mapping for balance sheet."""
        mapping = adapter.get_field_mapping("balance_sheet")
        
        assert mapping == adapter.balance_sheet_field_mapping
        assert "cashAndCashEquivalents" in mapping
    
    def test_get_field_mapping_cash_flow(self, adapter):
        """Test getting field mapping for cash flow."""
        mapping = adapter.get_field_mapping("cash_flow")
        
        assert mapping == adapter.cash_flow_field_mapping
        assert "operatingCashFlow" in mapping
    
    def test_get_field_mapping_invalid_type(self, adapter):
        """Test getting field mapping with an invalid type."""
        with pytest.raises(ValueError) as excinfo:
            adapter.get_field_mapping("invalid_type")
        
        assert "Invalid statement type" in str(excinfo.value)
    
    @patch('fin_statement_model.importers.fmp.FMPAdapter.fetch_statement')
    @patch('fin_statement_model.importers.fmp.FMPAdapter._add_common_calculations')
    def test_create_statement_graph_success(self, mock_add_calcs, mock_fetch, adapter):
        """Test successfully creating a statement graph."""
        mock_fetch.return_value = [
            {
                "date": "2021-12-31",
                "revenue": 1000,
                "costOfRevenue": 600,
                "grossProfit": 400,
                "netIncome": 200
            },
            {
                "date": "2020-12-31",
                "revenue": 800,
                "costOfRevenue": 500,
                "grossProfit": 300,
                "netIncome": 150
            }
        ]
        
        result = adapter.create_statement_graph("AAPL", "FY", 5, "income_statement")
        
        assert isinstance(result, FinancialStatementGraph)
        assert sorted(result.graph.periods) == ["FY2020", "FY2021"]
        assert len(result.graph.nodes) >= 4  # At least the fields in the mock data
        assert "revenue" in result.graph.nodes
        assert "gross_profit" in result.graph.nodes
        mock_fetch.assert_called_once_with("AAPL", "FY", 5, "income_statement")
        mock_add_calcs.assert_called_once_with(result, "income_statement")
    
    @patch('fin_statement_model.importers.fmp.FMPAdapter.fetch_statement')
    @patch('fin_statement_model.importers.fmp.FMPAdapter._add_common_calculations')
    def test_create_statement_graph_quarterly(self, mock_add_calcs, mock_fetch, adapter):
        """Test creating a statement graph with quarterly data."""
        mock_fetch.return_value = [
            {
                "date": "2021-12-31",
                "revenue": 1000,
                "costOfRevenue": 600
            },
            {
                "date": "2021-09-30",
                "revenue": 900,
                "costOfRevenue": 550
            }
        ]
        
        result = adapter.create_statement_graph("AAPL", "QTR", 5, "income_statement")
        
        assert isinstance(result, FinancialStatementGraph)
        assert sorted(result.graph.periods) == ["2021Q3", "2021Q4"]
        assert "revenue" in result.graph.nodes
        mock_fetch.assert_called_once_with("AAPL", "QTR", 5, "income_statement")
        mock_add_calcs.assert_called_once_with(result, "income_statement")
    
    @patch('fin_statement_model.importers.fmp.FMPAdapter.fetch_statement')
    def test_create_statement_graph_empty_value(self, mock_fetch, adapter):
        """Test creating a statement graph with some empty values."""
        mock_fetch.return_value = [
            {
                "date": "2021-12-31",
                "revenue": 1000,
                "costOfRevenue": None,  # None value
                "grossProfit": 400
            }
        ]
        
        result = adapter.create_statement_graph("AAPL", "FY", 5, "income_statement")
        
        assert isinstance(result, FinancialStatementGraph)
        assert "revenue" in result.graph.nodes
        assert "gross_profit" in result.graph.nodes
        # costOfRevenue should be skipped due to None value
        assert "revenue" in result.graph.nodes
        assert result.graph.calculate("revenue", "FY2021") == 1000
    
    @patch('fin_statement_model.importers.fmp.FMPAdapter.fetch_statement')
    def test_create_statement_graph_exception(self, mock_fetch, adapter):
        """Test creating a statement graph when an exception occurs."""
        mock_fetch.side_effect = ValueError("Test error")
        
        with pytest.raises(ValueError) as excinfo:
            adapter.create_statement_graph("AAPL", "FY", 5, "income_statement")
        
        assert "Error creating statement graph for AAPL" in str(excinfo.value)
    
    def test_add_common_calculations_income_statement(self, adapter):
        """Test adding common calculations to an income statement graph."""
        # Create a simple financial statement graph with income statement items
        fsg = FinancialStatementGraph(periods=["FY2021"])
        fsg.add_financial_statement_item("revenue", {"FY2021": 1000})
        fsg.add_financial_statement_item("cost_of_goods_sold", {"FY2021": -600})
        
        # Mock the _try_add_calculation method
        with patch.object(adapter, '_try_add_calculation') as mock_try_add:
            mock_try_add.return_value = True
            
            adapter._add_common_calculations(fsg, "income_statement")
            
            # Check that the expected calculations were attempted
            expected_calls = [
                call(fsg, "gross_profit", ["revenue", "cost_of_goods_sold"], "subtraction"),
                call(fsg, "operating_expenses", 
                    ["research_and_development_expenses", 
                     "general_and_administrative_expenses",
                     "selling_and_marketing_expenses",
                     "selling_general_and_administrative_expenses"], 
                    "addition"),
                call(fsg, "operating_income", ["gross_profit", "operating_expenses"], "subtraction"),
                call(fsg, "ebit", ["operating_income"], "addition"),
                call(fsg, "ebitda", ["ebit", "depreciation_and_amortization"], "addition"),
                call(fsg, "net_income_margin", ["net_income", "revenue"], "division")
            ]
            mock_try_add.assert_has_calls(expected_calls, any_order=True)
    
    def test_add_common_calculations_balance_sheet(self, adapter):
        """Test adding common calculations to a balance sheet graph."""
        # Create a simple financial statement graph with balance sheet items
        fsg = FinancialStatementGraph(periods=["FY2021"])
        fsg.add_financial_statement_item("cash_and_cash_equivalents", {"FY2021": 1000})
        fsg.add_financial_statement_item("short_term_investments", {"FY2021": 500})
        
        # Mock the _try_add_calculation method
        with patch.object(adapter, '_try_add_calculation') as mock_try_add:
            mock_try_add.return_value = True
            
            adapter._add_common_calculations(fsg, "balance_sheet")
            
            # Check that at least one of the expected calculations was attempted
            mock_try_add.assert_any_call(fsg, "cash_and_short_term_investments", 
                                      ["cash_and_cash_equivalents", "short_term_investments"], 
                                      "addition")
    
    def test_add_common_calculations_cash_flow(self, adapter):
        """Test adding common calculations to a cash flow graph."""
        # Create a simple financial statement graph with cash flow items
        fsg = FinancialStatementGraph(periods=["FY2021"])
        fsg.add_financial_statement_item("operating_cash_flow", {"FY2021": 1000})
        fsg.add_financial_statement_item("capital_expenditure", {"FY2021": -600})
        
        # Mock the _try_add_calculation method
        with patch.object(adapter, '_try_add_calculation') as mock_try_add:
            mock_try_add.return_value = True
            
            adapter._add_common_calculations(fsg, "cash_flow")
            
            # Check that the expected calculations were attempted
            mock_try_add.assert_any_call(fsg, "free_cash_flow", 
                                      ["operating_cash_flow", "capital_expenditure"], 
                                      "addition")
    
    def test_add_common_calculations_exception(self, adapter):
        """Test exception handling in _add_common_calculations."""
        fsg = FinancialStatementGraph(periods=["FY2021"])
        
        # Mock _try_add_calculation to raise an exception
        with patch.object(adapter, '_try_add_calculation', side_effect=Exception("Test error")):
            # This should log a warning but not raise the exception
            adapter._add_common_calculations(fsg, "income_statement")
            # The test passes if no exception is raised
    
    def test_try_add_calculation_success(self, adapter):
        """Test successfully adding a calculation."""
        fsg = FinancialStatementGraph(periods=["FY2021"])
        fsg.add_financial_statement_item("revenue", {"FY2021": 1000})
        fsg.add_financial_statement_item("cost_of_goods_sold", {"FY2021": -600})
        
        result = adapter._try_add_calculation(fsg, "gross_profit", 
                                           ["revenue", "cost_of_goods_sold"], 
                                           "addition")
        
        assert result is True
        assert "gross_profit" in fsg.graph.nodes
    
    def test_try_add_calculation_missing_inputs(self, adapter):
        """Test adding a calculation with some missing inputs."""
        fsg = FinancialStatementGraph(periods=["FY2021"])
        fsg.add_financial_statement_item("revenue", {"FY2021": 1000})
        # cost_of_goods_sold is missing, but we still have one valid input
        
        result = adapter._try_add_calculation(fsg, "partial_calc", 
                                           ["revenue", "cost_of_goods_sold"], 
                                           "addition")
        
        assert result is True
        assert "partial_calc" in fsg.graph.nodes
    
    def test_try_add_calculation_no_inputs(self, adapter):
        """Test adding a calculation with no valid inputs."""
        fsg = FinancialStatementGraph(periods=["FY2021"])
        # None of the inputs exist
        
        result = adapter._try_add_calculation(fsg, "failed_calc", 
                                           ["non_existent1", "non_existent2"], 
                                           "addition")
        
        assert result is False
        assert "failed_calc" not in fsg.graph.nodes
    
    def test_try_add_calculation_exception(self, adapter):
        """Test adding a calculation that raises an exception."""
        fsg = FinancialStatementGraph(periods=["FY2021"])
        fsg.add_financial_statement_item("revenue", {"FY2021": 1000})
        
        # Mock add_calculation to raise an exception
        with patch.object(fsg, 'add_calculation', side_effect=Exception("Test error")):
            result = adapter._try_add_calculation(fsg, "error_calc", 
                                               ["revenue"], 
                                               "addition")
            
            assert result is False
            assert "error_calc" not in fsg.graph.nodes 