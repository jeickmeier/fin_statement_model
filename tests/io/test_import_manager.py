"""Unit tests for import_manager module.

This module contains test cases for the import management functionality
of the Financial Statement Model, implemented in the ImportManager class.
"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from fin_statement_model.io.import_manager import ImportManager
from fin_statement_model.core.financial_statement import FinancialStatementGraph
from fin_statement_model.importers.adapter_base import DataSourceAdapter


class TestImportManager:
    """Test cases for the ImportManager class."""
    
    @pytest.fixture
    def import_manager(self):
        """Create an ImportManager instance for testing."""
        with patch('fin_statement_model.io.import_manager.AdapterFactory') as mock_factory, \
             patch('fin_statement_model.io.import_manager.AdapterRegistry') as mock_registry:
            # Setup the mock factory
            factory_instance = mock_factory.return_value
            factory_instance.discover_adapters.return_value = None
            factory_instance.list_adapters.return_value = ["FMPAdapter", "ExcelAdapter", "CSVAdapter"]
            
            # Setup the mock registry
            registry_instance = mock_registry.return_value
            registry_instance.get.return_value = None
            registry_instance.register.return_value = None
            registry_instance.list_instances.return_value = ["FMPAdapter_1", "ExcelAdapter_1"]
            
            manager = ImportManager()
            
            # Verify initialization behavior
            factory_instance.discover_adapters.assert_called_once_with('fin_statement_model.importers')
            
            # Reset mock counts from initialization to clean state for tests
            factory_instance.list_adapters.reset_mock()
            factory_instance.discover_adapters.reset_mock()
            registry_instance.get.reset_mock()
            registry_instance.register.reset_mock()
            
            return manager
    
    def test_init(self, import_manager):
        """Test ImportManager initialization."""
        assert isinstance(import_manager, ImportManager)
        # Initialization verification is now done in the fixture
    
    def test_get_adapter_new_adapter(self, import_manager):
        """Test getting a new adapter that isn't in the registry."""
        # Setup
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        import_manager.adapter_factory.create_adapter.return_value = mock_adapter
        import_manager.adapter_registry.get.return_value = None
        
        # Execute
        adapter = import_manager.get_adapter("TestAdapter", api_key="test_key")
        
        # Verify
        assert adapter == mock_adapter
        import_manager.adapter_factory.create_adapter.assert_called_once_with("TestAdapter", api_key="test_key")
        import_manager.adapter_registry.register.assert_called_once()
    
    def test_get_adapter_existing_adapter(self, import_manager):
        """Test getting an existing adapter from the registry."""
        # Setup
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        import_manager.adapter_registry.get.return_value = mock_adapter
        
        # Execute
        adapter = import_manager.get_adapter("TestAdapter", api_key="test_key")
        
        # Verify
        assert adapter == mock_adapter
        import_manager.adapter_factory.create_adapter.assert_not_called()
    
    def test_get_adapter_error(self, import_manager):
        """Test error handling when getting an adapter."""
        # Setup
        import_manager.adapter_registry.get.return_value = None
        import_manager.adapter_factory.create_adapter.side_effect = ValueError("Test error")
        
        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            import_manager.get_adapter("InvalidAdapter")
        
        assert "Error getting adapter InvalidAdapter" in str(excinfo.value)
    
    @patch('fin_statement_model.io.import_manager.logger')
    def test_import_from_api_known_source(self, mock_logger, import_manager):
        """Test importing from a known API source."""
        # Setup
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        mock_graph = MagicMock(spec=FinancialStatementGraph)
        mock_adapter.create_statement_graph.return_value = mock_graph
        
        # Configure the get_adapter to return our mock
        import_manager.get_adapter = MagicMock(return_value=mock_adapter)
        
        # Execute
        result = import_manager.import_from_api(
            source="FMP",
            identifier="AAPL",
            period_type="FY",
            limit=5,
            statement_type="income_statement",
            api_key="test_key"
        )
        
        # Verify
        assert result == mock_graph
        import_manager.get_adapter.assert_called_once_with("FMPAdapter", api_key="test_key")
        mock_adapter.create_statement_graph.assert_called_once_with(
            identifier="AAPL",
            period_type="FY",
            limit=5,
            statement_type="income_statement"
        )
        mock_logger.info.assert_called_once()
    
    def test_import_from_api_unknown_source(self, import_manager):
        """Test error handling for unknown API source."""
        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            import_manager.import_from_api(
                source="UnknownAPI",
                identifier="AAPL"
            )
        
        assert "Unknown API source: UnknownAPI" in str(excinfo.value)
    
    @patch('fin_statement_model.io.import_manager.logger')
    def test_import_from_api_adapter_error(self, mock_logger, import_manager):
        """Test error handling when the API adapter raises an error."""
        # Setup
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        mock_adapter.create_statement_graph.side_effect = Exception("API error")
        
        # Configure the get_adapter to return our mock
        import_manager.get_adapter = MagicMock(return_value=mock_adapter)
        
        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            import_manager.import_from_api(
                source="FMP",
                identifier="AAPL"
            )
        
        assert "Error importing data from API FMP" in str(excinfo.value)
        mock_logger.error.assert_called_once()
    
    @patch('fin_statement_model.io.import_manager.logger')
    def test_import_from_excel(self, mock_logger, import_manager):
        """Test importing from Excel file."""
        # Setup
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        mock_graph = MagicMock(spec=FinancialStatementGraph)
        mock_adapter.create_statement_graph.return_value = mock_graph
        
        # Configure the get_adapter to return our mock
        import_manager.get_adapter = MagicMock(return_value=mock_adapter)
        
        # Execute
        result = import_manager.import_from_excel(
            file_path="test.xlsx",
            sheet_name="Sheet1",
            period_column="Year",
            statement_type="balance_sheet",
            mapping_config={"Revenue": "revenue"}
        )
        
        # Verify
        assert result == mock_graph
        import_manager.get_adapter.assert_called_once_with('ExcelAdapter', mapping_config={"Revenue": "revenue"})
        mock_adapter.create_statement_graph.assert_called_once_with(
            file_path="test.xlsx",
            sheet_name="Sheet1",
            period_column="Year",
            statement_type="balance_sheet"
        )
        mock_logger.info.assert_called_once()
    
    @patch('fin_statement_model.io.import_manager.logger')
    def test_import_from_excel_error(self, mock_logger, import_manager):
        """Test error handling when importing from Excel."""
        # Setup
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        mock_adapter.create_statement_graph.side_effect = Exception("Excel error")
        
        # Configure the get_adapter to return our mock
        import_manager.get_adapter = MagicMock(return_value=mock_adapter)
        
        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            import_manager.import_from_excel(
                file_path="test.xlsx",
                sheet_name="Sheet1",
                period_column="Year"
            )
        
        assert "Error importing data from Excel file test.xlsx" in str(excinfo.value)
        mock_logger.error.assert_called_once()
    
    @patch('fin_statement_model.io.import_manager.logger')
    def test_import_from_csv(self, mock_logger, import_manager):
        """Test importing from CSV file."""
        # Setup
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        mock_graph = MagicMock(spec=FinancialStatementGraph)
        mock_adapter.create_statement_graph.return_value = mock_graph
        
        # Configure the get_adapter to return our mock
        import_manager.get_adapter = MagicMock(return_value=mock_adapter)
        
        # Execute
        result = import_manager.import_from_csv(
            file_path="test.csv",
            date_column="Date",
            value_column="Value",
            item_column="Item",
            statement_type="cash_flow",
            mapping_config={"Cash": "cash"}
        )
        
        # Verify
        assert result == mock_graph
        import_manager.get_adapter.assert_called_once_with('CSVAdapter', mapping_config={"Cash": "cash"})
        mock_adapter.create_statement_graph.assert_called_once_with(
            file_path="test.csv",
            date_column="Date",
            value_column="Value",
            item_column="Item",
            statement_type="cash_flow"
        )
        mock_logger.info.assert_called_once()
    
    @patch('fin_statement_model.io.import_manager.logger')
    def test_import_from_csv_error(self, mock_logger, import_manager):
        """Test error handling when importing from CSV."""
        # Setup
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        mock_adapter.create_statement_graph.side_effect = Exception("CSV error")
        
        # Configure the get_adapter to return our mock
        import_manager.get_adapter = MagicMock(return_value=mock_adapter)
        
        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            import_manager.import_from_csv(
                file_path="test.csv",
                date_column="Date",
                value_column="Value",
                item_column="Item"
            )
        
        assert "Error importing data from CSV file test.csv" in str(excinfo.value)
        mock_logger.error.assert_called_once()
    
    @patch('fin_statement_model.io.import_manager.logger')
    def test_import_from_dataframe(self, mock_logger, import_manager):
        """Test importing from DataFrame."""
        # Setup
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        mock_graph = MagicMock(spec=FinancialStatementGraph)
        mock_adapter.create_statement_graph.return_value = mock_graph
        mock_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        
        # Configure the get_adapter to return our mock
        import_manager.get_adapter = MagicMock(return_value=mock_adapter)
        
        # Execute
        result = import_manager.import_from_dataframe(
            df=mock_df,
            statement_type="income_statement",
            mapping_config={"A": "revenue"}
        )
        
        # Verify
        assert result == mock_graph
        import_manager.get_adapter.assert_called_once_with('DataFrameAdapter', mapping_config={"A": "revenue"})
        mock_adapter.create_statement_graph.assert_called_once_with(
            df=mock_df,
            statement_type="income_statement"
        )
        mock_logger.info.assert_called_once()
    
    @patch('fin_statement_model.io.import_manager.logger')
    def test_import_from_dataframe_error(self, mock_logger, import_manager):
        """Test error handling when importing from DataFrame."""
        # Setup
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        mock_adapter.create_statement_graph.side_effect = Exception("DataFrame error")
        mock_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        
        # Configure the get_adapter to return our mock
        import_manager.get_adapter = MagicMock(return_value=mock_adapter)
        
        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            import_manager.import_from_dataframe(df=mock_df)
        
        assert "Error importing data from DataFrame" in str(excinfo.value)
        mock_logger.error.assert_called_once()
    
    @patch('fin_statement_model.io.import_manager.logger')
    def test_register_custom_adapter(self, mock_logger, import_manager):
        """Test registering a custom adapter."""
        # Setup
        mock_adapter_class = MagicMock(spec=type)
        
        # Execute
        import_manager.register_custom_adapter("CustomAdapter", mock_adapter_class)
        
        # Verify
        import_manager.adapter_factory.register_adapter.assert_called_once_with("CustomAdapter", mock_adapter_class)
        mock_logger.info.assert_called_once_with("Registered custom adapter: CustomAdapter")
    
    @patch('fin_statement_model.io.import_manager.logger')
    def test_register_custom_adapter_error(self, mock_logger, import_manager):
        """Test error handling when registering a custom adapter."""
        # Setup
        mock_adapter_class = MagicMock(spec=type)
        import_manager.adapter_factory.register_adapter.side_effect = Exception("Registration error")
        
        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            import_manager.register_custom_adapter("CustomAdapter", mock_adapter_class)
        
        assert "Error registering custom adapter CustomAdapter" in str(excinfo.value)
        mock_logger.error.assert_called_once()
    
    def test_list_available_adapters(self, import_manager):
        """Test listing available adapters."""
        # Setup
        expected_adapters = ["FMPAdapter", "ExcelAdapter", "CSVAdapter"]
        import_manager.adapter_factory.list_adapters.return_value = expected_adapters
        
        # Execute
        result = import_manager.list_available_adapters()
        
        # Verify
        assert result == expected_adapters
        assert import_manager.adapter_factory.list_adapters.called
    
    def test_get_adapter_instances(self, import_manager):
        """Test getting adapter instances."""
        # Setup
        expected_instances = ["FMPAdapter_1", "ExcelAdapter_1"]
        import_manager.adapter_registry.list_instances.return_value = expected_instances
        
        # Execute
        result = import_manager.get_adapter_instances()
        
        # Verify
        assert result == expected_instances
        import_manager.adapter_registry.list_instances.assert_called_once() 