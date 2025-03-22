"""Unit tests for mapping_service module.

This module contains test cases for the MappingService which is responsible
for mapping non-standard metric names to standardized names in the Financial Statement Model.
"""
import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import difflib

from fin_statement_model.importers.mapping_service import MappingService
from fin_statement_model.importers.exceptions import MappingError


class TestMappingService:
    """Test cases for the MappingService class."""
    
    @pytest.fixture
    def metric_definitions(self):
        """Return sample metric definitions dictionary."""
        return {
            'revenue': {
                'description': 'Total company revenue',
                'type': 'income_statement',
                'aliases': ['sales', 'total_revenue']
            },
            'net_income': {
                'description': 'Net profit or loss',
                'type': 'income_statement',
                'aliases': ['profit', 'net_profit']
            },
            'total_assets': {
                'description': 'Total company assets',
                'type': 'balance_sheet',
                'aliases': ['assets']
            }
        }
    
    @pytest.fixture
    def mapping_service(self, metric_definitions):
        """Return a MappingService instance with mock metric definitions."""
        with patch('fin_statement_model.importers.mapping_service.LLMClient'):
            with patch('fin_statement_model.importers.mapping_service.Path.exists', return_value=False):
                service = MappingService(metric_definitions, similarity_threshold=0.85)
                return service
    
    @pytest.fixture
    def mapping_service_with_mappings(self, metric_definitions):
        """Return a MappingService instance with existing dynamic mappings."""
        with patch('fin_statement_model.importers.mapping_service.LLMClient'):
            with patch('fin_statement_model.importers.mapping_service.Path.exists', return_value=True):
                mock_mappings = '{"topline": "revenue", "profit_after_tax": "net_income"}'
                with patch('builtins.open', mock_open(read_data=mock_mappings)):
                    service = MappingService(metric_definitions)
                    return service
    
    def test_init(self, metric_definitions):
        """Test initialization of MappingService."""
        with patch('fin_statement_model.importers.mapping_service.LLMClient') as mock_llm:
            with patch('fin_statement_model.importers.mapping_service.Path.exists', return_value=False):
                service = MappingService(metric_definitions, similarity_threshold=0.9)
                
                assert service.metric_definitions == metric_definitions
                assert service.similarity_threshold == 0.9
                assert service.standard_metrics == set(metric_definitions.keys())
                assert service.dynamic_mappings == {}
                assert mock_llm.called
    
    def test_init_loads_dynamic_mappings(self):
        """Test that initialization loads dynamic mappings if they exist."""
        with patch('fin_statement_model.importers.mapping_service.LLMClient'):
            with patch('fin_statement_model.importers.mapping_service.Path.exists', return_value=True):
                mock_mappings = '{"topline": "revenue", "profit_after_tax": "net_income"}'
                with patch('builtins.open', mock_open(read_data=mock_mappings)):
                    service = MappingService({})
                    
                    assert service.dynamic_mappings == {
                        "topline": "revenue", 
                        "profit_after_tax": "net_income"
                    }
    
    def test_init_handles_load_error(self):
        """Test handling of errors during dynamic mappings loading."""
        with patch('fin_statement_model.importers.mapping_service.LLMClient'):
            with patch('fin_statement_model.importers.mapping_service.Path.exists', return_value=True):
                with patch('builtins.open', side_effect=Exception("Test error")):
                    with patch('fin_statement_model.importers.mapping_service.logging.getLogger') as mock_logger:
                        mock_logger_instance = MagicMock()
                        mock_logger.return_value = mock_logger_instance
                        
                        service = MappingService({})
                        
                        # Should log error but continue
                        mock_logger_instance.error.assert_called_once()
                        assert service.dynamic_mappings == {}
    
    def test_normalize_metric_name(self, mapping_service):
        """Test normalization of metric names."""
        assert mapping_service._normalize_metric_name("Revenue") == "revenue"
        assert mapping_service._normalize_metric_name("Net Income") == "net_income"
        assert mapping_service._normalize_metric_name(" Gross Profit ") == "_gross_profit_"
        assert mapping_service._normalize_metric_name("TOTAL_ASSETS") == "total_assets"
    
    def test_calculate_similarity(self, mapping_service):
        """Test similarity calculation between metric names."""
        # These examples should cover different similarity scores
        assert mapping_service._calculate_similarity("revenue", "revenue") == 1.0
        assert mapping_service._calculate_similarity("revenue", "total_revenue") < 1.0
        assert mapping_service._calculate_similarity("revenue", "total_revenue") > 0.5
        assert mapping_service._calculate_similarity("revenue", "completely_different") < 0.5
        
        # Ensure this matches the implementation of sequence matcher
        expected = difflib.SequenceMatcher(None, "revenue", "total_revenue").ratio()
        assert mapping_service._calculate_similarity("revenue", "total_revenue") == expected
    
    def test_is_ambiguous(self, mapping_service):
        """Test ambiguity detection in matches."""
        # Ambiguous matches with small score difference
        matches = [("revenue", 0.9), ("total_revenue", 0.89)]
        assert mapping_service._is_ambiguous(matches, threshold=0.05) is True
        
        # Non-ambiguous matches with large score difference
        matches = [("revenue", 0.9), ("total_revenue", 0.7)]
        assert mapping_service._is_ambiguous(matches, threshold=0.05) is False
        
        # Single match should never be ambiguous
        matches = [("revenue", 0.9)]
        assert mapping_service._is_ambiguous(matches, threshold=0.05) is False
    
    def test_map_metric_name_direct_match(self, mapping_service):
        """Test mapping with direct match to standard metric."""
        result, score = mapping_service.map_metric_name("revenue")
        
        assert result == "revenue"
        assert score == 1.0
    
    def test_map_metric_name_from_dynamic_mappings(self, mapping_service_with_mappings):
        """Test mapping using previously stored dynamic mappings."""
        result, score = mapping_service_with_mappings.map_metric_name("topline")
        
        assert result == "revenue"
        assert score == 1.0
    
    def test_map_metric_name_similarity_match(self, mapping_service):
        """Test mapping with similarity matching."""
        # Patch the similarity calculation to ensure we get a predictable result
        with patch.object(
            mapping_service, 
            '_calculate_similarity', 
            side_effect=lambda a, b: 0.9 if b == "revenue" else 0.5
        ):
            result, score = mapping_service.map_metric_name("top_line_sales")
            
            assert result == "revenue"
            assert score == 0.9
    
    def test_map_metric_name_ambiguous_warning(self, mapping_service):
        """Test handling of ambiguous matches."""
        # Patch to create ambiguous matches
        with patch.object(
            mapping_service, 
            '_calculate_similarity', 
            side_effect=lambda a, b: 0.9 if b == "revenue" else 0.89 if b == "net_income" else 0.5
        ):
            with patch.object(mapping_service.logger, 'warning') as mock_warning:
                result, score = mapping_service.map_metric_name("sales_figure")
                
                # Should still return the best match
                assert result == "revenue"
                assert score == 0.9
                
                # But should log a warning
                mock_warning.assert_called_once()
                assert "Ambiguous mapping" in mock_warning.call_args[0][0]
    
    def test_map_metric_name_llm_fallback(self, mapping_service):
        """Test fallback to LLM mapping when no similarity match found."""
        # No similarity matches
        with patch.object(mapping_service, '_calculate_similarity', return_value=0.5):
            # Mock LLM mapping to return a valid result
            with patch.object(
                mapping_service, 
                '_map_with_llm', 
                return_value=("revenue", 0.8)
            ) as mock_llm_map:
                result, score = mapping_service.map_metric_name("unusual_sales_term")
                
                assert result == "revenue"
                assert score == 0.8
                mock_llm_map.assert_called_once()
                # Note: _save_dynamic_mappings is called inside _map_with_llm, not directly in map_metric_name
    
    def test_map_metric_name_llm_error(self, mapping_service):
        """Test handling of LLM mapping errors."""
        # No similarity matches
        with patch.object(mapping_service, '_calculate_similarity', return_value=0.5):
            # Mock LLM mapping to raise an exception
            with patch.object(
                mapping_service, 
                '_map_with_llm', 
                side_effect=Exception("Test LLM error")
            ) as mock_llm_map:
                with patch.object(mapping_service.logger, 'error') as mock_error:
                    with pytest.raises(MappingError) as excinfo:
                        mapping_service.map_metric_name("unusual_sales_term")
                    
                    assert "No suitable mapping found" in str(excinfo.value)
                    mock_llm_map.assert_called_once()
                    mock_error.assert_called_once()
    
    def test_map_metric_names_multiple(self, mapping_service):
        """Test mapping of multiple metric names."""
        # Define behavior for each metric
        with patch.object(
            mapping_service, 
            'map_metric_name', 
            side_effect=[
                ("revenue", 1.0),
                ("net_income", 0.9),
                MappingError("No suitable mapping found for metric: unknown_term")
            ]
        ):
            with patch.object(mapping_service.logger, 'error') as mock_error:
                with patch.object(mapping_service.logger, 'warning') as mock_warning:
                    result = mapping_service.map_metric_names(
                        ["revenue", "net_profit", "unknown_term"]
                    )
                    
                    assert len(result) == 2
                    assert result["revenue"] == ("revenue", 1.0)
                    assert result["net_profit"] == ("net_income", 0.9)
                    assert "unknown_term" not in result
                    mock_error.assert_called_once()
                    mock_warning.assert_called_once()
    
    def test_validate_mapping_valid(self, mapping_service):
        """Test validation of metric mappings."""
        assert mapping_service.validate_mapping("sales", "revenue") is True
    
    def test_validate_mapping_invalid(self, mapping_service):
        """Test validation of invalid metric mappings."""
        assert mapping_service.validate_mapping("sales", "non_existent_metric") is False
    
    def test_get_metric_info_exists(self, mapping_service, metric_definitions):
        """Test retrieving metric info for existing metric."""
        info = mapping_service.get_metric_info("revenue")
        assert info == metric_definitions["revenue"]
    
    def test_get_metric_info_not_exists(self, mapping_service):
        """Test retrieving metric info for non-existent metric."""
        info = mapping_service.get_metric_info("non_existent_metric")
        assert info is None
    
    def test_map_with_llm_success(self, mapping_service):
        """Test LLM-based mapping with successful response."""
        llm_response = {
            "mapped_name": "revenue",
            "confidence": 0.85
        }
        
        with patch.object(mapping_service.llm_client, 'generate_mapping', return_value=llm_response):
            with patch.object(mapping_service, '_save_dynamic_mappings') as mock_save:
                result, confidence = mapping_service._map_with_llm(
                    "sales_figure", {"mapped_metrics": {}}
                )
                
                assert result == "revenue"
                assert confidence == 0.85
                assert mapping_service.dynamic_mappings["sales_figure"] == "revenue"
                mock_save.assert_called_once()
    
    def test_map_with_llm_invalid_mapping(self, mapping_service):
        """Test LLM-based mapping with invalid result."""
        llm_response = {
            "mapped_name": "non_existent_metric",
            "confidence": 0.85
        }
        
        with patch.object(mapping_service.llm_client, 'generate_mapping', return_value=llm_response):
            with pytest.raises(MappingError) as excinfo:
                mapping_service._map_with_llm(
                    "sales_figure", {"mapped_metrics": {}}
                )
            
            assert "LLM suggested invalid mapping" in str(excinfo.value)
    
    def test_map_with_llm_error(self, mapping_service):
        """Test LLM-based mapping with API error."""
        with patch.object(
            mapping_service.llm_client, 
            'generate_mapping', 
            side_effect=Exception("LLM API error")
        ):
            with pytest.raises(MappingError) as excinfo:
                mapping_service._map_with_llm(
                    "sales_figure", {"mapped_metrics": {}}
                )
            
            assert "LLM mapping failed" in str(excinfo.value)
    
    def test_generate_mapping_prompt(self, mapping_service):
        """Test generation of mapping prompt."""
        context = {
            "mapped_metrics": {
                "topline": "revenue",
                "profit_after_tax": "net_income"
            }
        }
        
        prompt = mapping_service._generate_mapping_prompt("sales_figure", context)
        
        assert "sales_figure" in prompt
        assert "revenue" in prompt
        assert "net_income" in prompt
        assert "total_assets" in prompt
        assert "topline" in prompt
        assert "profit_after_tax" in prompt
    
    def test_save_dynamic_mappings_success(self, mapping_service):
        """Test successful saving of dynamic mappings."""
        mapping_service.dynamic_mappings = {"sales": "revenue"}
        
        with patch('builtins.open', mock_open()) as mock_file:
            mapping_service._save_dynamic_mappings()
            
            mock_file.assert_called_once_with(mapping_service.dynamic_mappings_path, 'w')
            # json.dump writes multiple times, not just once
            assert mock_file().write.call_count > 0
    
    def test_save_dynamic_mappings_error(self, mapping_service):
        """Test error handling when saving dynamic mappings fails."""
        mapping_service.dynamic_mappings = {"sales": "revenue"}
        
        with patch('builtins.open', side_effect=Exception("Write error")):
            with patch.object(mapping_service.logger, 'error') as mock_error:
                mapping_service._save_dynamic_mappings()
                
                mock_error.assert_called_once()
                assert "Failed to save dynamic mappings" in mock_error.call_args[0][0]
    
    def test_load_dynamic_mappings_error(self):
        """Test error handling when loading dynamic mappings fails with corrupted JSON."""
        with patch('fin_statement_model.importers.mapping_service.LLMClient'):
            with patch('fin_statement_model.importers.mapping_service.Path.exists', return_value=True):
                corrupted_json = '{invalid-json'
                with patch('builtins.open', mock_open(read_data=corrupted_json)):
                    with patch('fin_statement_model.importers.mapping_service.logging.getLogger') as mock_logger:
                        mock_logger_instance = MagicMock()
                        mock_logger.return_value = mock_logger_instance
                        
                        service = MappingService({})
                        
                        # Should log error but continue
                        mock_logger_instance.error.assert_called_once()
                        assert service.dynamic_mappings == {}
    
    def test_thread_safety(self, mapping_service):
        """Test thread safety of mapping service with dynamic mappings."""
        # Mock the lock to check it's used correctly
        mock_lock = MagicMock()
        mapping_service._lock = mock_lock
        
        # Set up mocks for the LLM client and saving
        llm_response = {
            "mapped_name": "revenue",
            "confidence": 0.85
        }
        
        with patch.object(mapping_service.llm_client, 'generate_mapping', return_value=llm_response):
            with patch.object(mapping_service, '_save_dynamic_mappings'):
                mapping_service._map_with_llm("sales_figure", {"mapped_metrics": {}})
                
                # Verify lock was acquired and released
                mock_lock.__enter__.assert_called_once()
                mock_lock.__exit__.assert_called_once() 