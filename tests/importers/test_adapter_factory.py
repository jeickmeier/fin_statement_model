"""Unit tests for adapter_factory module.

This module contains test cases for the adapter factory functionality
of the Financial Statement Model, implemented in the AdapterFactory class.
"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
import importlib
import sys
import types
from pathlib import Path
import inspect

from fin_statement_model.importers.adapter_factory import AdapterFactory
from fin_statement_model.importers.adapter_base import (
    DataSourceAdapter, 
    FileDataSourceAdapter, 
    APIDataSourceAdapter
)


class TestAdapterFactory:
    """Test cases for the AdapterFactory class."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Set up before and clean up after each test."""
        # Store original adapters registry
        self.original_adapters = AdapterFactory._adapters.copy()
        
        # Clear the registry before each test
        AdapterFactory._adapters.clear()
        
        # Execute the test
        yield
        
        # Reset the registry after each test
        AdapterFactory._adapters.clear()
        AdapterFactory._adapters.update(self.original_adapters)
    
    def test_register_adapter(self):
        """Test registering an adapter."""
        # Create a mock adapter class
        mock_adapter_class = type('MockAdapter', (DataSourceAdapter,), {
            'fetch_statement': lambda *args, **kwargs: None,
            'create_statement_graph': lambda *args, **kwargs: None,
            'get_field_mapping': lambda *args, **kwargs: None
        })
        
        # Register the adapter
        AdapterFactory.register_adapter('test_adapter', mock_adapter_class)
        
        # Verify it was registered
        assert 'test_adapter' in AdapterFactory._adapters
        assert AdapterFactory._adapters['test_adapter'] == mock_adapter_class
    
    def test_register_adapter_duplicate(self):
        """Test registering an adapter with an existing type name."""
        # Create mock adapter classes
        mock_adapter_class1 = type('MockAdapter1', (DataSourceAdapter,), {
            'fetch_statement': lambda *args, **kwargs: None,
            'create_statement_graph': lambda *args, **kwargs: None,
            'get_field_mapping': lambda *args, **kwargs: None
        })
        
        mock_adapter_class2 = type('MockAdapter2', (DataSourceAdapter,), {
            'fetch_statement': lambda *args, **kwargs: None,
            'create_statement_graph': lambda *args, **kwargs: None,
            'get_field_mapping': lambda *args, **kwargs: None
        })
        
        # Register the first adapter
        AdapterFactory.register_adapter('duplicate', mock_adapter_class1)
        
        # Register the second adapter with the same type
        with patch('fin_statement_model.importers.adapter_factory.logger') as mock_logger:
            AdapterFactory.register_adapter('duplicate', mock_adapter_class2)
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            assert "already registered" in mock_logger.warning.call_args[0][0]
        
        # Verify the adapter was overwritten
        assert AdapterFactory._adapters['duplicate'] == mock_adapter_class2
    
    def test_create_adapter_success(self):
        """Test creating an adapter successfully."""
        # Create a mock adapter class with parameter recording
        mock_adapter_class = MagicMock()
        mock_adapter_instance = MagicMock()
        mock_adapter_class.return_value = mock_adapter_instance
        
        # Register the adapter
        AdapterFactory.register_adapter('test_adapter', mock_adapter_class)
        
        # Create an adapter instance
        result = AdapterFactory.create_adapter('test_adapter', param1='value1', param2='value2')
        
        # Verify correct adapter was instantiated with parameters
        assert result == mock_adapter_instance
        mock_adapter_class.assert_called_once_with(param1='value1', param2='value2')
    
    def test_create_adapter_not_registered(self):
        """Test creating an adapter that isn't registered."""
        with pytest.raises(ValueError) as excinfo:
            AdapterFactory.create_adapter('unknown_adapter')
        
        # Verify error message contains useful information
        assert "not registered" in str(excinfo.value)
        assert "Available types" in str(excinfo.value)
    
    def test_get_adapter_class_success(self):
        """Test getting an adapter class successfully."""
        # Create a mock adapter class
        mock_adapter_class = type('MockAdapter', (DataSourceAdapter,), {
            'fetch_statement': lambda *args, **kwargs: None,
            'create_statement_graph': lambda *args, **kwargs: None,
            'get_field_mapping': lambda *args, **kwargs: None
        })
        
        # Register the adapter
        AdapterFactory.register_adapter('test_adapter', mock_adapter_class)
        
        # Get the adapter class
        result = AdapterFactory.get_adapter_class('test_adapter')
        
        # Verify correct class was returned
        assert result == mock_adapter_class
    
    def test_get_adapter_class_not_registered(self):
        """Test getting an adapter class that isn't registered."""
        with pytest.raises(ValueError) as excinfo:
            AdapterFactory.get_adapter_class('unknown_adapter')
        
        # Verify error message contains useful information
        assert "not registered" in str(excinfo.value)
        assert "Available types" in str(excinfo.value)
    
    def test_list_adapters(self):
        """Test listing all registered adapters."""
        # Create mock adapter classes
        mock_adapter_class1 = type('MockAdapter1', (DataSourceAdapter,), {
            'fetch_statement': lambda *args, **kwargs: None,
            'create_statement_graph': lambda *args, **kwargs: None,
            'get_field_mapping': lambda *args, **kwargs: None
        })
        
        mock_adapter_class2 = type('MockAdapter2', (DataSourceAdapter,), {
            'fetch_statement': lambda *args, **kwargs: None,
            'create_statement_graph': lambda *args, **kwargs: None,
            'get_field_mapping': lambda *args, **kwargs: None
        })
        
        # Register the adapters
        AdapterFactory.register_adapter('adapter1', mock_adapter_class1)
        AdapterFactory.register_adapter('adapter2', mock_adapter_class2)
        
        # List the adapters
        result = AdapterFactory.list_adapters()
        
        # Verify result contains both adapters
        assert 'adapter1' in result
        assert 'adapter2' in result
        assert result['adapter1'] == mock_adapter_class1
        assert result['adapter2'] == mock_adapter_class2
    
    @patch('importlib.import_module')
    @patch('pkgutil.iter_modules')
    def test_discover_adapters_success(self, mock_iter_modules, mock_import_module):
        """Test successfully discovering adapters in a package."""
        # Create mock modules and classes
        mock_package = MagicMock()
        mock_package.__path__ = ['fake_path']
        mock_import_module.return_value = mock_package
        
        # Mock a module with two adapter classes
        mock_module = types.ModuleType('mock_module')
        # Create a valid adapter class
        mock_adapter_class = type('TestAdapter', (DataSourceAdapter,), {
            'fetch_statement': lambda *args, **kwargs: None,
            'create_statement_graph': lambda *args, **kwargs: None,
            'get_field_mapping': lambda *args, **kwargs: None
        })
        # Create a non-adapter class
        mock_non_adapter_class = type('NonAdapter', (), {})
        # Create a base class adapter (should be ignored)
        mock_file_adapter_class = FileDataSourceAdapter
        
        # Add classes to module
        mock_module.__dict__['TestAdapter'] = mock_adapter_class
        mock_module.__dict__['NonAdapter'] = mock_non_adapter_class
        mock_module.__dict__['FileDataSourceAdapter'] = mock_file_adapter_class
        
        # Set up module discovery
        mock_iter_modules.return_value = [
            (None, 'mock_module', False)
        ]
        
        # Set up module import
        def side_effect(name):
            if name == 'test_package':
                return mock_package
            elif name == 'test_package.mock_module':
                return mock_module
            else:
                raise ImportError(f"No module named '{name}'")
                
        mock_import_module.side_effect = side_effect
        
        # Call discover_adapters
        with patch('fin_statement_model.importers.adapter_factory.logger') as mock_logger:
            AdapterFactory.discover_adapters('test_package')
            
            # Verify adapters were discovered and registered
            assert 'test' in AdapterFactory._adapters
            assert AdapterFactory._adapters['test'] == mock_adapter_class
            
            # Verify non-adapters were not registered
            assert 'non' not in AdapterFactory._adapters
            
            # Verify base adapters were not registered
            assert 'filedatasource' not in AdapterFactory._adapters
            
            # Verify logging
            mock_logger.info.assert_called()
    
    @patch('importlib.import_module')
    def test_discover_adapters_package_error(self, mock_import_module):
        """Test error handling when the package cannot be imported."""
        # Setup package import to raise an exception
        mock_import_module.side_effect = ImportError("No module named 'bad_package'")
        
        # Call discover_adapters with error-prone package
        with patch('fin_statement_model.importers.adapter_factory.logger') as mock_logger:
            AdapterFactory.discover_adapters('bad_package')
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            assert "Error discovering adapters in package" in mock_logger.error.call_args[0][0]
    
    @patch('importlib.import_module')
    @patch('pkgutil.iter_modules')
    def test_discover_adapters_module_error(self, mock_iter_modules, mock_import_module):
        """Test error handling when a module cannot be imported."""
        # Create mock package
        mock_package = MagicMock()
        mock_package.__path__ = ['fake_path']
        
        # Set up package import to succeed
        mock_import_module.return_value = mock_package
        
        # Set up module discovery
        mock_iter_modules.return_value = [
            (None, 'bad_module', False)
        ]
        
        # Set up module import to fail
        def side_effect(name):
            if name == 'test_package':
                return mock_package
            elif name == 'test_package.bad_module':
                raise ImportError(f"No module named '{name}'")
            else:
                raise ImportError(f"No module named '{name}'")
                
        mock_import_module.side_effect = side_effect
        
        # Call discover_adapters
        with patch('fin_statement_model.importers.adapter_factory.logger') as mock_logger:
            AdapterFactory.discover_adapters('test_package')
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            assert "Error discovering adapters in module" in mock_logger.error.call_args[0][0]
    
    def test_module_import(self):
        """Test that discover_adapters is called when the module is imported."""
        # The module contains a line that automatically calls discover_adapters at import time
        # This functionality is difficult to test directly in a unit test since the module
        # has already been imported earlier.
        
        # We can verify that the auto-discovery code exists in the module
        factory_module = importlib.import_module('fin_statement_model.importers.adapter_factory')
        module_content = inspect.getsource(factory_module)
        
        # Check that the module ends with the auto-discovery call
        assert "AdapterFactory.discover_adapters()" in module_content 