"""Unit tests for the TransformerFactory class.

This module contains tests for the TransformerFactory class in transformer_factory.py,
which provides a factory for creating and managing data transformers.
"""
import pytest
import sys
from unittest.mock import patch, Mock, MagicMock

from fin_statement_model.transformations.transformer_factory import TransformerFactory
from fin_statement_model.transformations.base_transformer import DataTransformer, CompositeTransformer


class TestTransformerFactory:
    """Tests for the TransformerFactory class."""
    
    @pytest.fixture
    def reset_registry(self):
        """Fixture to reset the TransformerFactory registry before and after tests."""
        # Store original registry
        original_registry = TransformerFactory._transformers.copy()
        
        # Clear registry
        TransformerFactory._transformers.clear()
        
        yield
        
        # Restore original registry
        TransformerFactory._transformers.clear()
        TransformerFactory._transformers.update(original_registry)
    
    @pytest.fixture
    def mock_transformer_class(self):
        """Fixture to create a mock transformer class for testing."""
        class MockTransformer(DataTransformer):
            def transform(self, data):
                return data
        
        return MockTransformer
    
    @pytest.fixture
    def another_mock_transformer_class(self):
        """Fixture to create another mock transformer class for testing."""
        class AnotherMockTransformer(DataTransformer):
            def transform(self, data):
                return data * 2
        
        return AnotherMockTransformer
    
    def test_register_transformer(self, reset_registry, mock_transformer_class):
        """Test registering a transformer with the factory."""
        # Register a transformer
        TransformerFactory.register_transformer('mock', mock_transformer_class)
        
        # Verify the transformer was registered
        assert 'mock' in TransformerFactory._transformers
        assert TransformerFactory._transformers['mock'] == mock_transformer_class
    
    def test_register_transformer_already_registered(self, reset_registry, mock_transformer_class):
        """Test registering a transformer with a name that's already registered."""
        # Register a transformer
        TransformerFactory.register_transformer('mock', mock_transformer_class)
        
        # Try to register another transformer with the same name
        with pytest.raises(ValueError) as excinfo:
            TransformerFactory.register_transformer('mock', mock_transformer_class)
        
        assert "Transformer name 'mock' is already registered" in str(excinfo.value)
    
    def test_register_transformer_invalid_class(self, reset_registry):
        """Test registering a class that's not a DataTransformer subclass."""
        # Create a class that's not a DataTransformer subclass
        class NotATransformer:
            pass
        
        # Try to register it
        with pytest.raises(TypeError) as excinfo:
            TransformerFactory.register_transformer('invalid', NotATransformer)
        
        assert "Transformer class must be a subclass of DataTransformer" in str(excinfo.value)
    
    def test_create_transformer(self, reset_registry, mock_transformer_class):
        """Test creating a transformer instance by name."""
        # Register a transformer
        TransformerFactory.register_transformer('mock', mock_transformer_class)
        
        # Create an instance
        transformer = TransformerFactory.create_transformer('mock')
        
        # Verify the instance is of the correct type
        assert isinstance(transformer, mock_transformer_class)
    
    def test_create_transformer_with_kwargs(self, reset_registry, mock_transformer_class):
        """Test creating a transformer instance with keyword arguments."""
        # Mock the __init__ method to accept and store kwargs
        original_init = mock_transformer_class.__init__
        
        def patched_init(self, config=None, custom_arg=None):
            self.custom_arg = custom_arg
            original_init(self, config)
        
        mock_transformer_class.__init__ = patched_init
        
        try:
            # Register a transformer
            TransformerFactory.register_transformer('mock', mock_transformer_class)
            
            # Create an instance with kwargs
            transformer = TransformerFactory.create_transformer('mock', custom_arg='test_value')
            
            # Verify the instance has the correct kwargs
            assert transformer.custom_arg == 'test_value'
        finally:
            # Restore original __init__
            mock_transformer_class.__init__ = original_init
    
    def test_create_transformer_not_registered(self, reset_registry):
        """Test creating a transformer that's not registered."""
        # Try to create an instance of a transformer that's not registered
        with pytest.raises(ValueError) as excinfo:
            TransformerFactory.create_transformer('not_registered')
        
        assert "No transformer registered with name 'not_registered'" in str(excinfo.value)
    
    def test_list_transformers(self, reset_registry, mock_transformer_class, another_mock_transformer_class):
        """Test listing registered transformers."""
        # Register transformers
        TransformerFactory.register_transformer('mock1', mock_transformer_class)
        TransformerFactory.register_transformer('mock2', another_mock_transformer_class)
        
        # List transformers
        transformers = TransformerFactory.list_transformers()
        
        # Verify the list contains the registered transformers
        assert set(transformers) == {'mock1', 'mock2'}
    
    def test_list_transformers_empty(self, reset_registry):
        """Test listing transformers when none are registered."""
        # List transformers
        transformers = TransformerFactory.list_transformers()
        
        # Verify the list is empty
        assert transformers == []
    
    def test_get_transformer_class(self, reset_registry, mock_transformer_class):
        """Test getting a transformer class by name."""
        # Register a transformer
        TransformerFactory.register_transformer('mock', mock_transformer_class)
        
        # Get the class
        cls = TransformerFactory.get_transformer_class('mock')
        
        # Verify the class is correct
        assert cls == mock_transformer_class
    
    def test_get_transformer_class_not_registered(self, reset_registry):
        """Test getting a transformer class that's not registered."""
        # Try to get a class that's not registered
        with pytest.raises(ValueError) as excinfo:
            TransformerFactory.get_transformer_class('not_registered')
        
        assert "No transformer registered with name 'not_registered'" in str(excinfo.value)
    
    def test_discover_transformers(self, reset_registry):
        """Test discovering transformers in a package."""
        # Create a mock package with modules containing transformers
        mock_package = MagicMock()
        mock_package.__path__ = ['mock_path']
        
        # Create mock modules with transformer classes
        mock_module1 = MagicMock()
        mock_module2 = MagicMock()
        
        # Create transformer classes
        class MockTransformer1(DataTransformer):
            def transform(self, data):
                return data
        
        class MockTransformer2(DataTransformer):
            def transform(self, data):
                return data * 2
        
        # Add transformer classes to mock modules
        mock_module1.MockTransformer1 = MockTransformer1
        mock_module2.MockTransformer2 = MockTransformer2
        
        # Mock importlib.import_module to return our mock package and modules
        def mock_import_module(name):
            if name == 'mock_package':
                return mock_package
            elif name == 'mock_package.module1':
                return mock_module1
            elif name == 'mock_package.module2':
                return mock_module2
            raise ImportError(f"No module named '{name}'")
        
        # Mock pkgutil.iter_modules to return our mock modules
        mock_iter_modules = [
            (None, 'module1', None),
            (None, 'module2', None)
        ]
        
        # Mock inspect.getmembers to return our transformer classes
        def mock_getmembers(module):
            if module == mock_module1:
                return [('MockTransformer1', MockTransformer1)]
            elif module == mock_module2:
                return [('MockTransformer2', MockTransformer2)]
            return []
        
        # Patch the required functions
        with patch('importlib.import_module', side_effect=mock_import_module), \
             patch('pkgutil.iter_modules', return_value=mock_iter_modules), \
             patch('inspect.getmembers', side_effect=mock_getmembers), \
             patch('inspect.isclass', return_value=True):
            
            # Discover transformers
            TransformerFactory.discover_transformers('mock_package')
            
            # Verify the transformers were registered
            assert 'MockTransformer1' in TransformerFactory._transformers
            assert 'MockTransformer2' in TransformerFactory._transformers
            assert TransformerFactory._transformers['MockTransformer1'] == MockTransformer1
            assert TransformerFactory._transformers['MockTransformer2'] == MockTransformer2
    
    def test_discover_transformers_import_error(self, reset_registry):
        """Test discovering transformers when there's an import error."""
        # Mock importlib.import_module to raise ImportError
        with patch('importlib.import_module', side_effect=ImportError("No module named 'mock_package'")):
            # Discover transformers
            TransformerFactory.discover_transformers('mock_package')
            
            # Verify no transformers were registered
            assert not TransformerFactory._transformers
    
    def test_create_composite_transformer(self, reset_registry, mock_transformer_class, another_mock_transformer_class):
        """Test creating a composite transformer from a list of transformer names."""
        # Register transformers
        TransformerFactory.register_transformer('mock1', mock_transformer_class)
        TransformerFactory.register_transformer('mock2', another_mock_transformer_class)
        
        # Mock CompositeTransformer to verify it's called with the correct transformers
        with patch('fin_statement_model.transformations.base_transformer.CompositeTransformer') as mock_composite:
            # Create a composite transformer
            # Note: create_composite_transformer applies the same kwargs to all transformers in the pipeline
            TransformerFactory.create_composite_transformer(['mock1', 'mock2'])
            
            # Verify CompositeTransformer was called with instances of our transformers
            args = mock_composite.call_args[0][0]
            assert len(args) == 2
            assert isinstance(args[0], mock_transformer_class)
            assert isinstance(args[1], another_mock_transformer_class)
    
    def test_create_composite_transformer_invalid_name(self, reset_registry, mock_transformer_class):
        """Test creating a composite transformer with an invalid transformer name."""
        # Register a transformer
        TransformerFactory.register_transformer('mock', mock_transformer_class)
        
        # Create a composite transformer with an invalid name
        with pytest.raises(ValueError) as excinfo:
            TransformerFactory.create_composite_transformer(['mock', 'invalid'])
        
        assert "No transformer registered with name 'invalid'" in str(excinfo.value)
    
    def test_create_composite_transformer_with_kwargs(self, reset_registry, mock_transformer_class):
        """Test creating a composite transformer with kwargs passed to transformers."""
        # Mock the __init__ method to accept and store kwargs
        original_init = mock_transformer_class.__init__
        
        def patched_init(self, config=None, custom_arg=None):
            self.custom_arg = custom_arg
            original_init(self, config)
        
        mock_transformer_class.__init__ = patched_init
        
        try:
            # Register a transformer
            TransformerFactory.register_transformer('mock', mock_transformer_class)
            
            # Create a composite transformer with kwargs
            with patch('fin_statement_model.transformations.base_transformer.CompositeTransformer') as mock_composite:
                TransformerFactory.create_composite_transformer(['mock'], custom_arg='test_value')
                
                # Verify the transformer was created with the correct kwargs
                args = mock_composite.call_args[0][0]
                assert len(args) == 1
                assert args[0].custom_arg == 'test_value'
        finally:
            # Restore original __init__
            mock_transformer_class.__init__ = original_init


class TestTransformerFactoryIntegration:
    """Integration tests for the TransformerFactory class."""
    
    @pytest.fixture
    def reset_registry(self):
        """Fixture to reset the TransformerFactory registry before and after tests."""
        # Store original registry
        original_registry = TransformerFactory._transformers.copy()
        
        # Clear registry
        TransformerFactory._transformers.clear()
        
        yield
        
        # Restore original registry
        TransformerFactory._transformers.clear()
        TransformerFactory._transformers.update(original_registry)
    
    @pytest.fixture
    def test_transformer_class(self):
        """Fixture to create a real transformer class for testing."""
        class TestTransformer(DataTransformer):
            def __init__(self, config=None, multiplier=1):
                super().__init__(config)
                self.multiplier = multiplier
            
            def transform(self, data):
                if isinstance(data, (int, float)):
                    return data * self.multiplier
                return data
        
        return TestTransformer
    
    def test_full_lifecycle(self, reset_registry, test_transformer_class):
        """Test the full lifecycle of registering, creating, and using a transformer."""
        # Register the transformer
        TransformerFactory.register_transformer('test', test_transformer_class)
        
        # Check it's in the list
        assert 'test' in TransformerFactory.list_transformers()
        
        # Get the class
        cls = TransformerFactory.get_transformer_class('test')
        assert cls == test_transformer_class
        
        # Create an instance
        transformer = TransformerFactory.create_transformer('test', multiplier=2)
        assert isinstance(transformer, test_transformer_class)
        assert transformer.multiplier == 2
        
        # Use the transformer
        result = transformer.execute(5)
        assert result == 10
    
    def test_create_composite_transformer_integration(self, reset_registry, test_transformer_class):
        """Test creating and using a composite transformer with real transformers."""
        # Create a second transformer class
        class SecondTransformer(DataTransformer):
            def __init__(self, config=None, increment=0):
                super().__init__(config)
                self.increment = increment
            
            def transform(self, data):
                if isinstance(data, (int, float)):
                    return data + self.increment
                return data
        
        # Register the transformers
        TransformerFactory.register_transformer('test', test_transformer_class)
        TransformerFactory.register_transformer('second', SecondTransformer)
        
        # Create individual transformers with correct parameters since TransformerFactory.create_composite_transformer
        # applies the same kwargs to all transformers
        transformer1 = TransformerFactory.create_transformer('test', multiplier=2)
        transformer2 = TransformerFactory.create_transformer('second', increment=3)
        
        # Create a composite transformer manually
        composite = CompositeTransformer([transformer1, transformer2])
        
        # Verify it's a CompositeTransformer
        assert isinstance(composite, CompositeTransformer)
        
        # Use the composite transformer
        # Input: 5
        # First transformer (multiplier=2): 5 * 2 = 10
        # Second transformer (increment=3): 10 + 3 = 13
        result = composite.execute(5)
        assert result == 13 