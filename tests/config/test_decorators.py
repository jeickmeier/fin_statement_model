"""Tests for configuration decorators."""

import pytest
import warnings
from typing import Optional
from fin_statement_model.config import update_config, reset_config
from fin_statement_model.config.decorators import (
    uses_config_default,
    migrate_to_config,
    config_aware_init,
    warn_hardcoded_default,
)


class TestUsesConfigDefault:
    """Test the uses_config_default decorator."""
    
    def setup_method(self):
        """Reset config before each test."""
        reset_config()
    
    def teardown_method(self):
        """Reset config after each test."""
        reset_config()
    
    def test_uses_config_when_none(self):
        """Test decorator uses config value when parameter is None."""
        @uses_config_default("delimiter", "io.default_csv_delimiter")
        def process_data(data: str, delimiter: Optional[str] = None) -> str:
            return f"Processing with delimiter: {delimiter}"
        
        # Test with None (should use config)
        result = process_data("data", delimiter=None)
        assert result == "Processing with delimiter: ,"
        
        # Test with explicit value
        result = process_data("data", delimiter=";")
        assert result == "Processing with delimiter: ;"
    
    def test_uses_config_when_not_provided(self):
        """Test decorator uses config when parameter not provided."""
        @uses_config_default("periods", "forecasting.default_periods")
        def forecast(data: str, periods: Optional[int] = None) -> str:
            return f"Forecasting {periods} periods"
        
        # Call without providing the parameter
        result = forecast("data")
        assert result == "Forecasting 5 periods"
    
    def test_respects_explicit_values(self):
        """Test decorator respects explicitly provided values."""
        @uses_config_default("scale", "display.scale_factor")
        def scale_data(value: float, scale: Optional[float] = None) -> float:
            return value * scale
        
        # Test with explicit value
        assert scale_data(10.0, scale=2.0) == 20.0
        
        # Test with config default
        assert scale_data(10.0) == 10.0  # scale_factor default is 1.0
    
    def test_deprecated_warning(self):
        """Test decorator warns when deprecated=True."""
        @uses_config_default("delimiter", "io.default_csv_delimiter", deprecated=True)
        def process_data(data: str, delimiter: Optional[str] = None) -> str:
            return f"Processing with delimiter: {delimiter}"
        
        # Should warn when None is passed
        with pytest.warns(DeprecationWarning, match="Passing None for 'delimiter' is deprecated"):
            process_data("data", delimiter=None)
        
        # Should not warn with explicit value
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            process_data("data", delimiter=";")
    
    def test_updates_docstring(self):
        """Test decorator updates function docstring."""
        @uses_config_default("periods", "forecasting.default_periods")
        def forecast(data: str, periods: Optional[int] = None) -> str:
            """Forecast future values."""
            return f"Forecasting {periods} periods"
        
        assert "Note: Parameter 'periods' uses config default" in forecast.__doc__
    
    def test_with_updated_config(self):
        """Test decorator uses updated config values."""
        @uses_config_default("periods", "forecasting.default_periods")
        def forecast(data: str, periods: Optional[int] = None) -> str:
            return f"Forecasting {periods} periods"
        
        # Use default config
        assert forecast("data") == "Forecasting 5 periods"
        
        # Update config
        update_config({"forecasting": {"default_periods": 10}})
        
        # Should use new value
        assert forecast("data") == "Forecasting 10 periods"


class TestMigrateToConfig:
    """Test the migrate_to_config decorator."""
    
    def setup_method(self):
        """Reset config before each test."""
        reset_config()
    
    def test_multiple_parameters(self):
        """Test decorator handles multiple parameters."""
        @migrate_to_config(
            ("periods", "forecasting.default_periods"),
            ("growth_rate", "forecasting.default_growth_rate"),
            ("method", "forecasting.default_method")
        )
        def forecast(data: str, periods=None, growth_rate=None, method=None) -> dict:
            return {
                "periods": periods,
                "growth_rate": growth_rate,
                "method": method
            }
        
        # All parameters should use config defaults
        result = forecast("data")
        assert result == {
            "periods": 5,
            "growth_rate": 0.0,
            "method": "simple"
        }
        
        # Override some parameters
        result = forecast("data", periods=10, method="complex")
        assert result == {
            "periods": 10,
            "growth_rate": 0.0,
            "method": "complex"
        }
    
    def test_grace_period_false(self):
        """Test decorator with grace_period=False warns about None values."""
        @migrate_to_config(
            ("delimiter", "io.default_csv_delimiter"),
            grace_period=False
        )
        def process_data(data: str, delimiter=None) -> str:
            return f"Processing with {delimiter}"
        
        # Should warn when None is passed
        with pytest.warns(DeprecationWarning):
            process_data("data", delimiter=None)


class TestConfigAwareInit:
    """Test the config_aware_init class decorator."""
    
    def setup_method(self):
        """Reset config before each test."""
        reset_config()
    
    def test_class_init_with_config_defaults(self):
        """Test class decorator applies config defaults to __init__."""
        @config_aware_init
        class DataProcessor:
            def __init__(self, delimiter=None, validate_on_read=None):
                self.delimiter = delimiter
                self.validate = validate_on_read
        
        # Create instance without parameters
        processor = DataProcessor()
        assert processor.delimiter == ","  # From config
        assert processor.validate is True  # From config
        
        # Create instance with explicit values
        processor = DataProcessor(delimiter=";", validate_on_read=False)
        assert processor.delimiter == ";"
        assert processor.validate is False
    
    def test_only_applies_to_none_defaults(self):
        """Test decorator only applies to parameters with None defaults."""
        @config_aware_init
        class Forecaster:
            def __init__(self, periods=None, fixed_value=10):
                self.periods = periods
                self.fixed_value = fixed_value
        
        forecaster = Forecaster()
        assert forecaster.periods == 5  # From config
        assert forecaster.fixed_value == 10  # Not overridden
    
    def test_handles_missing_config_gracefully(self):
        """Test decorator handles missing config keys gracefully."""
        @config_aware_init
        class TestClass:
            def __init__(self, unknown_param=None, delimiter=None):
                self.unknown = unknown_param
                self.delimiter = delimiter
        
        # Should not raise error for unknown parameter
        instance = TestClass()
        assert instance.unknown is None
        assert instance.delimiter == ","


class TestWarnHardcodedDefault:
    """Test the warn_hardcoded_default decorator."""
    
    def test_warns_on_hardcoded_usage(self):
        """Test decorator warns when hard-coded default is used."""
        @warn_hardcoded_default("periods", "forecasting.default_periods", 5)
        def forecast(data: str, periods: int = 5) -> str:
            return f"Forecasting {periods} periods"
        
        # Should warn when using the hard-coded default
        with pytest.warns(FutureWarning, match="using hard-coded default periods=5"):
            # Not passing periods, so it uses default of 5
            forecast("data")
        
        # Should not warn with different value
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            forecast("data", periods=10)
    
    def test_warns_when_explicitly_passed(self):
        """Test decorator warns even when hard-coded value is explicitly passed."""
        @warn_hardcoded_default("scale", "display.scale_factor", 1.0)
        def scale_value(value: float, scale: float = 1.0) -> float:
            return value * scale
        
        # Should warn when explicitly passing the hard-coded value
        with pytest.warns(FutureWarning):
            scale_value(10.0, scale=1.0)
        
        # Should not warn with different value
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            scale_value(10.0, scale=2.0) 