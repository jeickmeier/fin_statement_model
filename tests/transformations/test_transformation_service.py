"""Unit tests for the TransformationService class.

This module contains tests for the TransformationService class in transformation_service.py,
which provides a high-level service for managing and applying data transformations.
"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock

from fin_statement_model.transformations.transformation_service import TransformationService
from fin_statement_model.transformations.base_transformer import DataTransformer, CompositeTransformer
from fin_statement_model.transformations.transformer_factory import TransformerFactory
from fin_statement_model.transformations.financial_transformers import (
    NormalizationTransformer,
    TimeSeriesTransformer,
    PeriodConversionTransformer,
    StatementFormattingTransformer
)


class TestTransformationService:
    """Tests for the TransformationService class."""
    
    @pytest.fixture
    def service(self):
        """Fixture to create a TransformationService instance with mocked transformer factory."""
        with patch('fin_statement_model.transformations.transformation_service.TransformerFactory') as mock_factory:
            # Mock list_transformers to return empty list for testing registration
            mock_factory.list_transformers.return_value = []
            service = TransformationService()
            yield service
    
    @pytest.fixture
    def sample_df(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            'revenue': [1000, 1200, 1500],
            'expenses': [600, 700, 900],
            'profit': [400, 500, 600]
        })
    
    @pytest.fixture
    def sample_dict(self):
        """Create a sample dictionary for testing."""
        return {
            'revenue': 1000,
            'expenses': 600,
            'profit': 400
        }
    
    def test_init(self):
        """Test initialization registers built-in transformers."""
        with patch('fin_statement_model.transformations.transformation_service.TransformerFactory') as mock_factory:
            # Mock list_transformers to return empty list so registration will occur
            mock_factory.list_transformers.return_value = []
            
            service = TransformationService()
            
            # Verify that all built-in transformers were registered
            assert mock_factory.register_transformer.call_count == 4
            
            # Check specific registrations
            mock_factory.register_transformer.assert_any_call('normalization', NormalizationTransformer)
            mock_factory.register_transformer.assert_any_call('time_series', TimeSeriesTransformer)
            mock_factory.register_transformer.assert_any_call('period_conversion', PeriodConversionTransformer)
            mock_factory.register_transformer.assert_any_call('statement_formatting', StatementFormattingTransformer)
    
    def test_init_already_registered(self):
        """Test initialization doesn't re-register transformers that are already registered."""
        with patch('fin_statement_model.transformations.transformation_service.TransformerFactory') as mock_factory:
            # Mock list_transformers to return all transformer names
            mock_factory.list_transformers.return_value = [
                'normalization', 'time_series', 'period_conversion', 'statement_formatting'
            ]
            
            service = TransformationService()
            
            # Verify that no transformers were registered
            mock_factory.register_transformer.assert_not_called()
    
    def test_normalize_data_dataframe(self, service, sample_df):
        """Test normalize_data method with DataFrame input."""
        # Mock the transformer and factory
        mock_transformer = Mock()
        mock_transformer.execute.return_value = "normalized_data"
        
        with patch('fin_statement_model.transformations.transformation_service.TransformerFactory') as mock_factory:
            mock_factory.create_transformer.return_value = mock_transformer
            
            # Call the method with DataFrame
            result = service.normalize_data(
                sample_df, 
                normalization_type='percent_of', 
                reference='revenue'
            )
            
            # Verify transformer was created with correct parameters
            mock_factory.create_transformer.assert_called_once_with(
                'normalization',
                normalization_type='percent_of',
                reference='revenue',
                scale_factor=None
            )
            
            # Verify transformer.execute was called with the input data
            mock_transformer.execute.assert_called_once_with(sample_df)
            
            # Verify the result is what the transformer returned
            assert result == "normalized_data"
    
    def test_normalize_data_dict(self, service, sample_dict):
        """Test normalize_data method with dictionary input."""
        # Mock the transformer and factory
        mock_transformer = Mock()
        mock_transformer.execute.return_value = "normalized_dict"
        
        with patch('fin_statement_model.transformations.transformation_service.TransformerFactory') as mock_factory:
            mock_factory.create_transformer.return_value = mock_transformer
            
            # Call the method with dictionary
            result = service.normalize_data(
                sample_dict, 
                normalization_type='scale_by', 
                scale_factor=0.001
            )
            
            # Verify transformer was created with correct parameters
            mock_factory.create_transformer.assert_called_once_with(
                'normalization',
                normalization_type='scale_by',
                reference=None,
                scale_factor=0.001
            )
            
            # Verify transformer.execute was called with the input data
            mock_transformer.execute.assert_called_once_with(sample_dict)
            
            # Verify the result is what the transformer returned
            assert result == "normalized_dict"
    
    def test_transform_time_series(self, service, sample_df):
        """Test transform_time_series method."""
        # Mock the transformer and factory
        mock_transformer = Mock()
        mock_transformer.execute.return_value = "transformed_time_series"
        
        with patch('fin_statement_model.transformations.transformation_service.TransformerFactory') as mock_factory:
            mock_factory.create_transformer.return_value = mock_transformer
            
            # Call the method
            result = service.transform_time_series(
                sample_df, 
                transformation_type='growth_rate', 
                periods=2,
                window_size=4
            )
            
            # Verify transformer was created with correct parameters
            mock_factory.create_transformer.assert_called_once_with(
                'time_series',
                transformation_type='growth_rate',
                periods=2,
                window_size=4
            )
            
            # Verify transformer.execute was called with the input data
            mock_transformer.execute.assert_called_once_with(sample_df)
            
            # Verify the result is what the transformer returned
            assert result == "transformed_time_series"
    
    def test_convert_periods(self, service, sample_df):
        """Test convert_periods method."""
        # Mock the transformer and factory
        mock_transformer = Mock()
        mock_transformer.execute.return_value = "converted_periods"
        
        with patch('fin_statement_model.transformations.transformation_service.TransformerFactory') as mock_factory:
            mock_factory.create_transformer.return_value = mock_transformer
            
            # Call the method
            result = service.convert_periods(
                sample_df, 
                conversion_type='quarterly_to_annual', 
                aggregation='mean'
            )
            
            # Verify transformer was created with correct parameters
            mock_factory.create_transformer.assert_called_once_with(
                'period_conversion',
                conversion_type='quarterly_to_annual',
                aggregation='mean'
            )
            
            # Verify transformer.execute was called with the input data
            mock_transformer.execute.assert_called_once_with(sample_df)
            
            # Verify the result is what the transformer returned
            assert result == "converted_periods"
    
    def test_format_statement(self, service, sample_df):
        """Test format_statement method."""
        # Mock the transformer and factory
        mock_transformer = Mock()
        mock_transformer.execute.return_value = "formatted_statement"
        
        with patch('fin_statement_model.transformations.transformation_service.TransformerFactory') as mock_factory:
            mock_factory.create_transformer.return_value = mock_transformer
            
            # Call the method
            result = service.format_statement(
                sample_df, 
                statement_type='income_statement',
                add_subtotals=True,
                apply_sign_convention=True
            )
            
            # Verify transformer was created with correct parameters
            mock_factory.create_transformer.assert_called_once_with(
                'statement_formatting',
                statement_type='income_statement',
                add_subtotals=True,
                apply_sign_convention=True
            )
            
            # Verify transformer.execute was called with the input data
            mock_transformer.execute.assert_called_once_with(sample_df)
            
            # Verify the result is what the transformer returned
            assert result == "formatted_statement"
    
    def test_create_transformation_pipeline(self, service):
        """Test create_transformation_pipeline method."""
        # Mock the transformer factory and transformers
        mock_transformer1 = Mock(spec=DataTransformer)
        mock_transformer2 = Mock(spec=DataTransformer)
        
        with patch('fin_statement_model.transformations.transformation_service.TransformerFactory') as mock_factory, \
             patch('fin_statement_model.transformations.transformation_service.CompositeTransformer') as mock_composite:
            
            # Setup the factory to return our mock transformers
            mock_factory.create_transformer.side_effect = [mock_transformer1, mock_transformer2]
            
            # Create test config
            transformer_configs = [
                {'name': 'normalization', 'normalization_type': 'percent_of', 'reference': 'revenue'},
                {'name': 'time_series', 'transformation_type': 'growth_rate'}
            ]
            
            # Call the method
            service.create_transformation_pipeline(transformer_configs)
            
            # Verify transformer factory was called with correct parameters for each config
            mock_factory.create_transformer.assert_any_call(
                'normalization',
                normalization_type='percent_of',
                reference='revenue'
            )
            mock_factory.create_transformer.assert_any_call(
                'time_series',
                transformation_type='growth_rate'
            )
            
            # Verify CompositeTransformer was created with the list of transformers
            mock_composite.assert_called_once_with([mock_transformer1, mock_transformer2])
    
    def test_create_transformation_pipeline_missing_name(self, service):
        """Test create_transformation_pipeline with missing name in config."""
        # Create test config with missing name
        transformer_configs = [
            {'normalization_type': 'percent_of', 'reference': 'revenue'}  # Missing 'name'
        ]
        
        # Verify it raises ValueError
        with pytest.raises(ValueError) as excinfo:
            service.create_transformation_pipeline(transformer_configs)
        
        assert "Each transformer configuration must have a 'name' field" in str(excinfo.value)
    
    def test_apply_transformation_pipeline(self, service, sample_df):
        """Test apply_transformation_pipeline method."""
        # Mock the pipeline creation and execution
        mock_pipeline = Mock()
        mock_pipeline.execute.return_value = "pipeline_result"
        
        with patch.object(service, 'create_transformation_pipeline', return_value=mock_pipeline):
            # Create test config
            transformer_configs = [
                {'name': 'normalization', 'normalization_type': 'percent_of', 'reference': 'revenue'},
                {'name': 'time_series', 'transformation_type': 'growth_rate'}
            ]
            
            # Call the method
            result = service.apply_transformation_pipeline(sample_df, transformer_configs)
            
            # Verify pipeline was created with the config
            service.create_transformation_pipeline.assert_called_once_with(transformer_configs)
            
            # Verify pipeline.execute was called with the input data
            mock_pipeline.execute.assert_called_once_with(sample_df)
            
            # Verify the result is what the pipeline returned
            assert result == "pipeline_result"
    
    def test_register_custom_transformer(self, service):
        """Test register_custom_transformer method."""
        # Create a mock transformer class
        mock_transformer_class = Mock(spec=DataTransformer)
        
        with patch('fin_statement_model.transformations.transformation_service.TransformerFactory') as mock_factory:
            # Call the method
            service.register_custom_transformer('custom_transformer', mock_transformer_class)
            
            # Verify transformer factory was called with correct parameters
            mock_factory.register_transformer.assert_called_once_with('custom_transformer', mock_transformer_class)
    
    def test_list_available_transformers(self, service):
        """Test list_available_transformers method."""
        with patch('fin_statement_model.transformations.transformation_service.TransformerFactory') as mock_factory:
            # Setup the factory to return a list of transformers
            mock_factory.list_transformers.return_value = ['normalization', 'time_series']
            
            # Call the method
            result = service.list_available_transformers()
            
            # Verify transformer factory was called
            mock_factory.list_transformers.assert_called_once()
            
            # Verify the result is what the factory returned
            assert result == ['normalization', 'time_series']


class TestTransformationServiceIntegration:
    """Integration tests for the TransformationService class."""
    
    @pytest.fixture
    def reset_factory(self):
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
    def sample_df(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            'revenue': [1000, 1200, 1500],
            'expenses': [600, 700, 900],
            'profit': [400, 500, 600]
        })
    
    def test_normalization_integration(self, reset_factory, sample_df):
        """Test normalize_data integration with actual transformer."""
        # Create a service and normalize data
        service = TransformationService()
        
        # Perform normalization
        result = service.normalize_data(
            sample_df, 
            normalization_type='percent_of', 
            reference='revenue'
        )
        
        # Verify the result is a DataFrame with correct values
        assert isinstance(result, pd.DataFrame)
        # Check specific values: expenses should be expenses/revenue * 100
        assert result.loc[0, 'expenses'] == (600 / 1000) * 100
    
    def test_pipeline_integration(self, reset_factory, sample_df):
        """Test transformation pipeline integration with actual transformers."""
        # Create a service
        service = TransformationService()
        
        # Create pipeline configuration
        config = [
            {'name': 'normalization', 'normalization_type': 'percent_of', 'reference': 'revenue'},
            {'name': 'time_series', 'transformation_type': 'growth_rate'}
        ]
        
        # Apply pipeline
        result = service.apply_transformation_pipeline(sample_df, config)
        
        # Verify the result is a DataFrame
        assert isinstance(result, pd.DataFrame)
        
        # Check that normalization occurred (expenses as percentage of revenue)
        # and then growth rate was calculated on the normalized values
        # Original: [600/1000*100, 700/1200*100, 900/1500*100] = [60, 58.33, 60]
        # Growth rate: [NaN, (58.33-60)/60*100, (60-58.33)/58.33*100] ≈ [NaN, -2.78, 2.86]
        
        # We can't check exact values due to floating point precision, but we can check signs
        assert 'expenses_growth' in result.columns
        assert pd.isna(result.loc[0, 'expenses_growth'])  # First row is NaN (no previous period)
        
        # Check that expenses as percentage of revenue exists
        assert result.loc[0, 'expenses'] == 60  # First row expenses = 60% of revenue 