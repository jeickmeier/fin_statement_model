"""Unit tests for the base transformer module.

This module contains tests for the abstract DataTransformer class and the 
CompositeTransformer implementation.
"""
import pytest
from unittest.mock import Mock, patch, call
import logging

from fin_statement_model.transformations.base_transformer import DataTransformer, CompositeTransformer


class ConcreteTransformer(DataTransformer):
    """A concrete implementation of DataTransformer for testing."""
    
    def transform(self, data):
        """Simple transformation that adds 1 to the input value."""
        return data + 1


class TestDataTransformer:
    """Tests for the base DataTransformer abstract class."""
    
    def test_init_default_config(self):
        """Test initialization with default config."""
        transformer = ConcreteTransformer()
        assert transformer.config == {}
    
    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = {"key": "value", "multiplier": 2}
        transformer = ConcreteTransformer(config)
        assert transformer.config == config
    
    def test_validate_input_default(self):
        """Test the default validate_input method."""
        transformer = ConcreteTransformer()
        result = transformer.validate_input(42)
        assert result is True
    
    def test_pre_transform_hook_default(self):
        """Test the default _pre_transform_hook method."""
        transformer = ConcreteTransformer()
        data = "test_data"
        result = transformer._pre_transform_hook(data)
        assert result == data  # Should return unchanged data
    
    def test_post_transform_hook_default(self):
        """Test the default _post_transform_hook method."""
        transformer = ConcreteTransformer()
        data = "test_data"
        result = transformer._post_transform_hook(data)
        assert result == data  # Should return unchanged data
    
    def test_execute_success(self):
        """Test a successful execution of the transformation pipeline."""
        transformer = ConcreteTransformer()
        result = transformer.execute(5)
        assert result == 6  # 5 + 1
    
    def test_execute_with_validation_failure(self):
        """Test execution with validation failure."""
        transformer = ConcreteTransformer()
        # Override validate_input to always return False
        transformer.validate_input = Mock(return_value=False)
        
        with pytest.raises(ValueError) as exc_info:
            transformer.execute(5)
        
        assert "Invalid input data" in str(exc_info.value)
        transformer.validate_input.assert_called_once_with(5)
    
    def test_execute_with_transform_error(self):
        """Test execution with transformation error."""
        transformer = ConcreteTransformer()
        # Override transform to raise an exception
        transformer.transform = Mock(side_effect=Exception("Transform error"))
        
        with pytest.raises(ValueError) as exc_info:
            transformer.execute(5)
        
        assert "Error transforming data" in str(exc_info.value)
        transformer.transform.assert_called_once()
    
    def test_execute_calls_hooks(self):
        """Test that execute calls the pre and post hooks."""
        transformer = ConcreteTransformer()
        # Mock the hooks
        transformer._pre_transform_hook = Mock(return_value=5)
        transformer.transform = Mock(return_value=6)
        transformer._post_transform_hook = Mock(return_value=7)
        
        result = transformer.execute("original_data")
        
        # Verify calls
        transformer._pre_transform_hook.assert_called_once_with("original_data")
        transformer.transform.assert_called_once_with(5)  # Should get data from pre-hook
        transformer._post_transform_hook.assert_called_once_with(6)  # Should get data from transform
        assert result == 7  # Should get final result from post-hook
    
    def test_custom_validation(self):
        """Test a custom validation implementation."""
        class ValidatingTransformer(ConcreteTransformer):
            def validate_input(self, data):
                return isinstance(data, int) and data > 0
        
        transformer = ValidatingTransformer()
        
        # Valid data
        assert transformer.execute(5) == 6
        
        # Invalid data
        with pytest.raises(ValueError):
            transformer.execute(-1)
        
        with pytest.raises(ValueError):
            transformer.execute("not an int")
    
    def test_custom_hooks(self):
        """Test custom pre and post hook implementations."""
        class HookTransformer(ConcreteTransformer):
            def _pre_transform_hook(self, data):
                return data * 2
                
            def _post_transform_hook(self, data):
                return data + 10
        
        transformer = HookTransformer()
        # (5 * 2) + 1 + 10 = 21
        assert transformer.execute(5) == 21


class TestCompositeTransformer:
    """Tests for the CompositeTransformer class."""
    
    @pytest.fixture
    def transformers(self):
        """Create a list of mock transformers for testing."""
        t1 = Mock(spec=DataTransformer)
        t1.execute.return_value = 2
        
        t2 = Mock(spec=DataTransformer)
        t2.execute.return_value = 3
        
        t3 = Mock(spec=DataTransformer)
        t3.execute.return_value = 4
        
        return [t1, t2, t3]
    
    def test_init(self, transformers):
        """Test initialization with transformers."""
        config = {"key": "value"}
        composite = CompositeTransformer(transformers, config)
        
        assert composite.transformers == transformers
        assert composite.config == config
    
    def test_transform(self, transformers):
        """Test the transform method."""
        composite = CompositeTransformer(transformers)
        result = composite.transform(1)
        
        # Last transformer's result should be returned
        assert result == 4
        
        # Each transformer should be called with the result of the previous one
        transformers[0].execute.assert_called_once_with(1)
        transformers[1].execute.assert_called_once_with(2)
        transformers[2].execute.assert_called_once_with(3)
    
    def test_add_transformer(self, transformers):
        """Test adding a transformer."""
        composite = CompositeTransformer(transformers[:2])  # Start with first 2
        
        # Add the third transformer
        composite.add_transformer(transformers[2])
        
        assert len(composite.transformers) == 3
        assert composite.transformers[2] == transformers[2]
    
    def test_remove_transformer_valid_index(self, transformers):
        """Test removing a transformer with a valid index."""
        # Store references to the transformers before creating the composite
        first_transformer = transformers[0]
        second_transformer = transformers[1]
        third_transformer = transformers[2]
        
        # Create the composite transformer
        composite = CompositeTransformer(transformers)
        
        # Remove the second transformer
        removed = composite.remove_transformer(1)
        
        # Check that the correct transformer was removed
        assert removed is second_transformer
        
        # Check that the list now has one less transformer
        assert len(composite.transformers) == 2
        
        # Check that the transformer is no longer in the list
        assert second_transformer not in composite.transformers
        
        # Check that the remaining transformers are in the expected order
        assert composite.transformers == [first_transformer, third_transformer]
    
    def test_remove_transformer_invalid_index(self, transformers):
        """Test removing a transformer with an invalid index."""
        composite = CompositeTransformer(transformers)
        
        # Try to remove with invalid index
        removed = composite.remove_transformer(5)
        
        assert removed is None
        assert len(composite.transformers) == 3
        assert composite.transformers == transformers
    
    def test_execute_pipeline(self):
        """Test executing a pipeline of actual transformers."""
        class AddTransformer(DataTransformer):
            def transform(self, data):
                return data + 1
        
        class MultiplyTransformer(DataTransformer):
            def transform(self, data):
                return data * 2
        
        class SquareTransformer(DataTransformer):
            def transform(self, data):
                return data ** 2
        
        transformers = [
            AddTransformer(),        # 5 + 1 = 6
            MultiplyTransformer(),   # 6 * 2 = 12 
            SquareTransformer()      # 12 ^ 2 = 144
        ]
        
        pipeline = CompositeTransformer(transformers)
        result = pipeline.execute(5)
        
        assert result == 144
    
    def test_nested_composite_transformers(self):
        """Test nesting composite transformers."""
        # Define simple transformers
        class AddTransformer(DataTransformer):
            def __init__(self, amount, config=None):
                super().__init__(config)
                self.amount = amount
            
            def transform(self, data):
                return data + self.amount
        
        # Create inner composite
        inner = CompositeTransformer([
            AddTransformer(1),
            AddTransformer(2)
        ])
        
        # Create outer composite
        outer = CompositeTransformer([
            AddTransformer(5),
            inner,
            AddTransformer(10)
        ])
        
        # Starting with 0:
        # 0 + 5 = 5 (first transformer)
        # 5 + 1 = 6 (inner first)
        # 6 + 2 = 8 (inner second)
        # 8 + 10 = 18 (final transformer)
        result = outer.execute(0)
        
        assert result == 18
    
    def test_validation_in_pipeline(self):
        """Test that validation works within a pipeline."""
        class ValidatingTransformer(DataTransformer):
            def validate_input(self, data):
                return isinstance(data, int)
                
            def transform(self, data):
                return data + 1
        
        class StringTransformer(DataTransformer):
            def transform(self, data):
                return str(data)
        
        transformers = [
            ValidatingTransformer(),  # Expects int
            StringTransformer()       # Converts to string
        ]
        
        pipeline = CompositeTransformer(transformers)
        
        # Valid input
        assert pipeline.execute(5) == "6"
        
        # Invalid input to second transformer - string not int
        second_pipeline = CompositeTransformer([
            StringTransformer(),      # Returns string
            ValidatingTransformer()   # Expects int but gets string -> fail
        ])
        
        with pytest.raises(ValueError) as exc_info:
            second_pipeline.execute(5)
            
        assert "Invalid input data" in str(exc_info.value) 