"""Unit tests for adapter_registry module.

This module contains test cases for the adapter registry functionality
of the Financial Statement Model, implemented in the AdapterRegistry class.
"""
import pytest
from unittest.mock import patch, MagicMock

from fin_statement_model.importers.adapter_registry import AdapterRegistry
from fin_statement_model.importers.adapter_base import DataSourceAdapter


class TestAdapterRegistry:
    """Test cases for the AdapterRegistry class."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Set up before and clean up after each test."""
        # Store original instances registry
        self.original_instances = AdapterRegistry._instances.copy()
        
        # Clear the registry before each test
        AdapterRegistry._instances.clear()
        
        # Execute the test
        yield
        
        # Reset the registry after each test
        AdapterRegistry._instances.clear()
        AdapterRegistry._instances.update(self.original_instances)
    
    def test_register(self):
        """Test registering an adapter instance."""
        # Create a mock adapter instance
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        
        # Register the adapter
        AdapterRegistry.register('test_type', 'test_config', mock_adapter)
        
        # Verify it was registered
        assert 'test_type' in AdapterRegistry._instances
        assert 'test_config' in AdapterRegistry._instances['test_type']
        assert AdapterRegistry._instances['test_type']['test_config'] == mock_adapter
    
    def test_register_new_type(self):
        """Test registering an adapter instance with a new type."""
        # Create a mock adapter instance
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        
        # Register the adapter
        AdapterRegistry.register('new_type', 'test_config', mock_adapter)
        
        # Verify it was registered
        assert 'new_type' in AdapterRegistry._instances
        assert 'test_config' in AdapterRegistry._instances['new_type']
        assert AdapterRegistry._instances['new_type']['test_config'] == mock_adapter
    
    def test_get_success(self):
        """Test getting an adapter instance successfully."""
        # Create a mock adapter instance
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        
        # Register the adapter
        AdapterRegistry.register('test_type', 'test_config', mock_adapter)
        
        # Get the adapter
        result = AdapterRegistry.get('test_type', 'test_config')
        
        # Verify correct instance was returned
        assert result == mock_adapter
    
    def test_get_type_not_found(self):
        """Test getting an adapter instance with type not found."""
        # Get an adapter with type not in registry
        result = AdapterRegistry.get('nonexistent_type', 'test_config')
        
        # Verify None was returned
        assert result is None
    
    def test_get_config_not_found(self):
        """Test getting an adapter instance with config not found."""
        # Create a mock adapter instance
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        
        # Register the adapter
        AdapterRegistry.register('test_type', 'test_config', mock_adapter)
        
        # Get an adapter with config not in registry
        result = AdapterRegistry.get('test_type', 'nonexistent_config')
        
        # Verify None was returned
        assert result is None
    
    @patch('fin_statement_model.importers.adapter_registry.AdapterFactory')
    def test_get_or_create_existing(self, mock_factory):
        """Test getting or creating an adapter instance that already exists."""
        # Create a mock adapter instance
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        
        # Register the adapter
        AdapterRegistry.register('test_type', 'test_config', mock_adapter)
        
        # Get or create the adapter
        result = AdapterRegistry.get_or_create('test_type', 'test_config', param1='value1')
        
        # Verify correct instance was returned
        assert result == mock_adapter
        
        # Verify factory was not called
        mock_factory.create_adapter.assert_not_called()
    
    @patch('fin_statement_model.importers.adapter_registry.AdapterFactory')
    def test_get_or_create_new(self, mock_factory):
        """Test getting or creating an adapter instance that doesn't exist."""
        # Create a mock adapter instance
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        
        # Configure factory to return the mock adapter
        mock_factory.create_adapter.return_value = mock_adapter
        
        # Get or create a new adapter
        result = AdapterRegistry.get_or_create('test_type', 'test_config', param1='value1')
        
        # Verify factory was called with correct parameters
        mock_factory.create_adapter.assert_called_once_with('test_type', param1='value1')
        
        # Verify correct instance was returned
        assert result == mock_adapter
        
        # Verify instance was registered
        assert 'test_type' in AdapterRegistry._instances
        assert 'test_config' in AdapterRegistry._instances['test_type']
        assert AdapterRegistry._instances['test_type']['test_config'] == mock_adapter
    
    def test_remove_success(self):
        """Test removing an adapter instance successfully."""
        # Create a mock adapter instance
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        mock_adapter2 = MagicMock(spec=DataSourceAdapter)
        
        # Register the adapters
        AdapterRegistry.register('test_type', 'test_config', mock_adapter)
        AdapterRegistry.register('test_type', 'other_config', mock_adapter2)
        
        # Remove the adapter
        result = AdapterRegistry.remove('test_type', 'test_config')
        
        # Verify it was removed
        assert result is True
        assert 'test_config' not in AdapterRegistry._instances['test_type']
        assert 'other_config' in AdapterRegistry._instances['test_type']
    
    def test_remove_cleans_empty_type(self):
        """Test removing the last adapter of a type cleans up the type key."""
        # Create a mock adapter instance
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        
        # Register the adapter
        AdapterRegistry.register('test_type', 'test_config', mock_adapter)
        
        # Remove the adapter
        result = AdapterRegistry.remove('test_type', 'test_config')
        
        # Verify it was removed and type was cleaned up
        assert result is True
        assert 'test_type' not in AdapterRegistry._instances
    
    def test_remove_type_not_found(self):
        """Test removing an adapter instance with type not found."""
        # Remove an adapter with type not in registry
        result = AdapterRegistry.remove('nonexistent_type', 'test_config')
        
        # Verify False was returned
        assert result is False
    
    def test_remove_config_not_found(self):
        """Test removing an adapter instance with config not found."""
        # Create a mock adapter instance
        mock_adapter = MagicMock(spec=DataSourceAdapter)
        
        # Register the adapter
        AdapterRegistry.register('test_type', 'test_config', mock_adapter)
        
        # Remove an adapter with config not in registry
        result = AdapterRegistry.remove('test_type', 'nonexistent_config')
        
        # Verify False was returned
        assert result is False
    
    def test_clear(self):
        """Test clearing all adapter instances."""
        # Create mock adapter instances
        mock_adapter1 = MagicMock(spec=DataSourceAdapter)
        mock_adapter2 = MagicMock(spec=DataSourceAdapter)
        
        # Register the adapters
        AdapterRegistry.register('type1', 'config1', mock_adapter1)
        AdapterRegistry.register('type2', 'config2', mock_adapter2)
        
        # Verify they were registered
        assert len(AdapterRegistry._instances) == 2
        
        # Clear the registry
        AdapterRegistry.clear()
        
        # Verify it was cleared
        assert len(AdapterRegistry._instances) == 0
    
    def test_list_instances(self):
        """Test listing all adapter instances."""
        # Create mock adapter instances
        mock_adapter1 = MagicMock(spec=DataSourceAdapter)
        mock_adapter2 = MagicMock(spec=DataSourceAdapter)
        
        # Register the adapters
        AdapterRegistry.register('type1', 'config1', mock_adapter1)
        AdapterRegistry.register('type2', 'config2', mock_adapter2)
        
        # List the instances
        result = AdapterRegistry.list_instances()
        
        # Verify result contains both adapters
        assert 'type1' in result
        assert 'type2' in result
        assert 'config1' in result['type1']
        assert 'config2' in result['type2']
        assert result['type1']['config1'] == mock_adapter1
        assert result['type2']['config2'] == mock_adapter2
        
        # Verify the result is a copy
        assert result is not AdapterRegistry._instances 