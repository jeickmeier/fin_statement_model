# Centralized Configuration Architecture

## Executive Summary

The `fin_statement_model` library now features a centralized configuration system that consolidates all user-configurable settings into a single, unified interface. This architecture replaces the previous scattered configuration approach with a hierarchical, validated, and easily discoverable system.

## Architecture Overview

### Core Components

1. **Configuration Models** (`fin_statement_model/config/models.py`)
   - Pydantic-based models providing type safety and validation
   - Hierarchical structure organized by functional areas
   - Comprehensive documentation for each setting

2. **Configuration Manager** (`fin_statement_model/config/manager.py`)
   - Handles loading and merging configurations from multiple sources
   - Implements precedence rules for configuration sources
   - Thread-safe configuration access

3. **Public API** (`fin_statement_model/config/__init__.py`)
   - Simple functions: `get_config()`, `update_config()`, `reset_config()`
   - Centralized access point for all configuration needs

## Configuration Hierarchy

```
Config (root)
├── logging
│   ├── level
│   ├── format
│   ├── detailed
│   ├── log_to_file
│   └── log_file_path
├── io
│   ├── default_excel_sheet
│   ├── default_csv_delimiter
│   ├── auto_create_output_dirs
│   ├── validate_on_read
│   └── default_mapping_configs_dir
├── forecasting
│   ├── default_method
│   ├── default_periods
│   ├── default_growth_rate
│   ├── min_historical_periods
│   └── allow_negative_forecasts
├── preprocessing
│   ├── auto_clean_data
│   ├── fill_missing_with_zero
│   ├── remove_empty_periods
│   ├── standardize_period_format
│   └── default_normalization_type
├── display
│   ├── default_number_format
│   ├── default_currency_format
│   ├── default_percentage_format
│   ├── hide_zero_rows
│   ├── contra_display_style
│   ├── scale_factor
│   └── default_units
├── api
│   ├── fmp_api_key
│   ├── fmp_base_url
│   ├── api_timeout
│   ├── api_retry_count
│   ├── cache_api_responses
│   └── cache_ttl_hours
├── metrics
│   ├── custom_metrics_dir
│   ├── validate_metric_inputs
│   └── auto_register_metrics
└── validation
    ├── strict_mode
    ├── check_balance_sheet_equation
    ├── max_acceptable_variance
    ├── warn_on_negative_assets
    └── validate_sign_conventions
```

## Configuration Sources & Precedence

Configuration is loaded from multiple sources in order of precedence (highest to lowest):

1. **Runtime Updates** - Programmatic changes via `update_config()`
2. **Environment Variables** - `FSM_*` prefixed variables
3. **User Config File** - `fsm_config.yaml` in current directory or home
4. **Project Config File** - `.fsm_config.yaml` in project root
5. **Default Configuration** - Built-in defaults

## Key Benefits

### 1. **Discoverability**
- All configuration options in one place
- Comprehensive documentation via Pydantic models
- Example configuration file provided

### 2. **Type Safety**
- Pydantic validation ensures configuration correctness
- Type hints throughout for IDE support
- Runtime validation of configuration values

### 3. **Flexibility**
- Multiple configuration sources support different use cases
- Environment variables for CI/CD and containerized deployments
- File-based configuration for projects and teams
- Runtime updates for testing and experimentation

### 4. **Backward Compatibility**
- Existing environment variables (e.g., `FMP_API_KEY`) still work
- Migration path provided for existing code
- No breaking changes to public APIs

## Usage Examples

### Basic Usage
```python
from fin_statement_model.config import get_config, update_config

# Get current configuration
config = get_config()
print(config.forecasting.default_method)

# Update configuration
update_config({
    'forecasting': {'default_method': 'statistical'},
    'display': {'scale_factor': 0.001}
})
```

### Project Configuration
```yaml
# .fsm_config.yaml in project root
project_name: tech_company_analysis

forecasting:
  default_method: ml
  default_periods: 8

display:
  scale_factor: 0.000001  # millions
  default_units: "USD Millions"
```

### Environment Variables
```bash
export FSM_API_FMP_API_KEY=your_secret_key
export FSM_LOGGING_LEVEL=DEBUG
export FSM_FORECASTING_DEFAULT_PERIODS=10
```

## Migration Strategy

### Phase 1: Current Implementation
- Centralized configuration system available
- No breaking changes to existing code
- Documentation and examples provided

### Phase 2: Gradual Adoption (Recommended)
- Update library internals to use centralized config
- Deprecate scattered configuration patterns
- Provide migration warnings

### Phase 3: Full Migration (Future)
- Remove deprecated configuration methods
- All configuration through centralized system
- Simplified codebase and documentation

## Files Created/Modified

### New Files
- `fin_statement_model/config/__init__.py` - Public API
- `fin_statement_model/config/models.py` - Configuration models
- `fin_statement_model/config/manager.py` - Configuration manager
- `docs/configuration_guide.md` - User documentation
- `docs/CONFIGURATION_ARCHITECTURE.md` - This document
- `examples/fsm_config.yaml.example` - Example configuration
- `tests/config/test_config_manager.py` - Unit tests

### Future Integration Points
- Update existing modules to use `get_config()` instead of scattered configs
- Replace hardcoded defaults with configuration values
- Consolidate environment variable usage
- Unify validation settings across the library

## Conclusion

The centralized configuration architecture provides a solid foundation for managing library settings. It improves user experience through better discoverability, type safety, and flexibility while maintaining backward compatibility. The phased migration approach ensures smooth adoption without disrupting existing users. 