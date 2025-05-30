# Configuration Guide

## Overview

The `fin_statement_model` library now provides a centralized configuration system that allows you to customize library behavior through multiple sources. This guide explains how to use the configuration system and migrate from scattered configuration patterns.

## Table of Contents

1. [Configuration Sources](#configuration-sources)
2. [Configuration Options](#configuration-options)
3. [Usage Examples](#usage-examples)
4. [Migration Guide](#migration-guide)
5. [Best Practices](#best-practices)
6. [How the Library Uses Configuration](#how-the-library-uses-configuration)

## Configuration Sources

The configuration system loads settings from multiple sources in order of precedence (highest to lowest):

### 1. Runtime Updates
```python
from fin_statement_model.config import update_config

update_config({
    'logging': {'level': 'DEBUG'},
    'forecasting': {'default_method': 'statistical'}
})
```

### 2. Environment Variables
```bash
export FSM_LOGGING_LEVEL=DEBUG
export FSM_API_FMP_API_KEY=your_api_key
export FSM_FORECASTING_DEFAULT_PERIODS=10
```

### 3. User Configuration File
- `fsm_config.yaml` in current directory
- `~/.fsm_config.yaml` in home directory
- Custom path specified programmatically

### 4. Project Configuration File
- `.fsm_config.yaml` in project root (searches up directory tree)

### 5. Default Configuration
- Built-in defaults for all settings

## Configuration Options

### Logging Configuration

```yaml
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  detailed: false  # Include file/line numbers
  log_to_file: false
  log_file_path: ./logs/fsm.log
```

### Input/Output Configuration

```yaml
io:
  default_excel_sheet: Sheet1
  default_csv_delimiter: ","
  auto_create_output_dirs: true
  validate_on_read: true
  default_mapping_configs_dir: ./mappings  # Custom mapping directory
```

### Forecasting Configuration

```yaml
forecasting:
  default_method: historical_growth  # simple, historical_growth, curve, statistical, ml
  default_periods: 5
  default_growth_rate: 0.0
  min_historical_periods: 3
  allow_negative_forecasts: true
```

### Preprocessing Configuration

```yaml
preprocessing:
  auto_clean_data: true
  fill_missing_with_zero: false
  remove_empty_periods: true
  standardize_period_format: true
  default_normalization_type: null  # percent_of, minmax, standard, scale_by
```

### Display Configuration

```yaml
display:
  default_number_format: ",.2f"
  default_currency_format: "$,.2f"
  default_percentage_format: ".1%"
  hide_zero_rows: false
  contra_display_style: parentheses  # parentheses, brackets, negative
  thousands_separator: ","
  decimal_separator: "."
  default_units: USD
  scale_factor: 1.0  # 0.001 for thousands, 0.000001 for millions
```

### API Configuration

```yaml
api:
  fmp_api_key: null  # Set via env var FSM_API_FMP_API_KEY
  fmp_base_url: https://financialmodelingprep.com/api/v3
  api_timeout: 30
  api_retry_count: 3
  cache_api_responses: true
  cache_ttl_hours: 24
```

### Metrics Configuration

```yaml
metrics:
  custom_metrics_dir: null  # Path to custom metrics definitions
  validate_metric_inputs: true
  auto_register_metrics: true
```

### Validation Configuration

```yaml
validation:
  strict_mode: false
  check_balance_sheet_equation: true
  max_acceptable_variance: 0.01
  warn_on_negative_assets: true
  validate_sign_conventions: true
```

## Usage Examples

### Basic Usage

```python
from fin_statement_model.config import get_config, update_config

# Get current configuration
config = get_config()
print(f"Current log level: {config.logging.level}")
print(f"Default forecast method: {config.forecasting.default_method}")

# Update configuration at runtime
update_config({
    'logging': {'level': 'DEBUG'},
    'display': {'scale_factor': 0.001}  # Display in thousands
})
```

### Using Configuration in Your Code

```python
from fin_statement_model.config import get_config
from fin_statement_model.forecasting import StatementForecaster

config = get_config()

# Use configuration values
forecaster = StatementForecaster(
    method=config.forecasting.default_method,
    periods=config.forecasting.default_periods
)

# Format numbers based on config
def format_currency(value):
    scale = config.display.scale_factor
    fmt = config.display.default_currency_format
    return f"{value * scale:{fmt[1:]}}"
```

### Project-Specific Configuration

Create a `.fsm_config.yaml` in your project root:

```yaml
# Project-specific overrides
project_name: quarterly_analysis

logging:
  level: INFO
  log_to_file: true
  log_file_path: ./logs/quarterly_analysis.log

forecasting:
  default_method: statistical
  default_periods: 8  # 2 years of quarters

display:
  scale_factor: 0.000001  # Display in millions
  default_units: "USD Millions"
```

## Migration Guide

### From Environment Variables

**Old:**
```python
api_key = os.getenv("FMP_API_KEY")
```

**New:**
```python
from fin_statement_model.config import get_config
config = get_config()
api_key = config.api.fmp_api_key
```

### From Inline Configuration

**Old:**
```python
# Hardcoded forecast configuration
forecast_configs = {
    "revenue": {"method": "simple", "config": 0.10}
}
```

**New:**
```python
from fin_statement_model.config import get_config
config = get_config()

# Use defaults from config
forecast_configs = {
    "revenue": {
        "method": config.forecasting.default_method,
        "config": config.forecasting.default_growth_rate or 0.10
    }
}
```

### From Multiple Config Files

**Old:**
```python
# Load from various config files
excel_config = load_excel_config()
forecast_config = load_forecast_config()
display_config = load_display_config()
```

**New:**
```python
# All configuration in one place
from fin_statement_model.config import get_config
config = get_config()

# Access all settings through unified interface
excel_sheet = config.io.default_excel_sheet
forecast_method = config.forecasting.default_method
number_format = config.display.default_number_format
```

## Best Practices

### 1. Use Configuration Files for Projects

Create a `.fsm_config.yaml` in your project root for project-specific settings:

```yaml
project_name: tech_company_analysis
logging:
  level: INFO
forecasting:
  default_method: ml  # Use ML for tech companies
```

### 2. Use Environment Variables for Secrets

```bash
# Don't put API keys in config files
export FSM_API_FMP_API_KEY=your_secret_key
```

### 3. Override at Runtime for Experiments

```python
# Temporarily change settings for testing
from fin_statement_model.config import update_config, reset_config

# Save original state
original_config = get_config().to_dict()

# Experiment with different settings
update_config({'forecasting': {'default_method': 'curve'}})
run_analysis()

# Reset when done
reset_config()
```

### 4. Validate Configuration

```python
from fin_statement_model.config import get_config, Config

# Validate configuration file before using
try:
    config = Config.from_file(Path("my_config.yaml"))
    print("Configuration is valid!")
except Exception as e:
    print(f"Configuration error: {e}")
```

### 5. Document Team Standards

Create a team configuration template:

```yaml
# team_config_template.yaml
project_name: ${PROJECT_NAME}

# Team standards
display:
  scale_factor: 0.001  # Always show in thousands
  contra_display_style: parentheses  # Team convention

validation:
  strict_mode: true  # Enable for production
  max_acceptable_variance: 0.001  # Tight tolerance
```

## Configuration Schema

The complete configuration schema is defined in `fin_statement_model.config.models.Config`. You can generate a schema for validation:

```python
from fin_statement_model.config import Config
import json

# Generate JSON schema
schema = Config.model_json_schema()
print(json.dumps(schema, indent=2))
```

This schema can be used with YAML/JSON validators and IDE plugins for autocomplete and validation.

## How the Library Uses Configuration

The financial statement model library is designed to use the centralized configuration system internally for all default values. This means you don't need to constantly pass configuration values to library functions - they automatically use the appropriate defaults from your configuration.

### Automatic Configuration Usage

Library components automatically use configuration defaults:

```python
# Before: Manually passing config values everywhere
validator = UnifiedNodeValidator(
    strict_mode=config.validation.strict_mode,
    auto_standardize=config.validation.auto_standardize_names,
    warn_on_non_standard=config.validation.warn_on_non_standard
)

df = create_statement_dataframe(
    graph=graph,
    config_path_or_dir="income_statement.yaml",
    format_kwargs={
        "number_format": config.display.default_currency_format,
        "hide_zero_rows": config.display.hide_zero_rows,
        "contra_display_style": config.display.contra_display_style
    }
)

# After: Clean API with automatic config usage
validator = UnifiedNodeValidator()  # Uses config defaults automatically!

df = create_statement_dataframe(
    graph=graph,
    config_path_or_dir="income_statement.yaml"
    # No need to specify format_kwargs - uses config defaults!
)
```

### Override When Needed

You can still override configuration defaults for specific operations:

```python
# Use config defaults for most operations
validator = UnifiedNodeValidator()

# Override for a specific use case
strict_validator = UnifiedNodeValidator(strict_mode=True)

# Statement formatting with override
df = create_statement_dataframe(
    graph=graph,
    config_path_or_dir="income_statement.yaml",
    format_kwargs={
        "number_format": ",.0f"  # Override just this one setting
    }
)
```

### Components That Use Configuration

The following library components automatically use configuration:

1. **Validation (UnifiedNodeValidator)**
   - `strict_mode` from `validation.strict_mode`
   - `auto_standardize` from `validation.auto_standardize_names`
   - `warn_on_non_standard` from `validation.warn_on_non_standard`

2. **Statement Formatting (StatementFormatter)**
   - `hide_zero_rows` from `display.hide_zero_rows`
   - `contra_display_style` from `display.contra_display_style`
   - `number_format` from `display.default_number_format`
   - `scale_factor` from `display.scale_factor`

3. **IO Operations**
   - Excel sheet names from `io.default_excel_sheet`
   - CSV delimiters from `io.default_csv_delimiter`
   - Validation settings from `io.strict_validation`

4. **Forecasting Nodes**
   - Default method from `forecasting.default_method`
   - Default periods from `forecasting.default_periods`
   - Growth rates from `forecasting.default_growth_rate`

This design principle makes the library much easier to use while still maintaining flexibility for specific use cases. 