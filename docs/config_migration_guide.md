# Configuration System Migration Guide

This guide explains the improvements made to the configuration system in Phase 3 and how to migrate existing code to take advantage of the new dynamic features.

## What Changed

### 1. Dynamic Environment Variable Mapping

**Before**: Environment variable mappings were hardcoded in `ConfigManager._load_from_env()`:

```python
# Old hardcoded approach
env_mappings = {
    "FSM_LOGGING_LEVEL": ["logging", "level"],
    "FSM_IO_DEFAULT_EXCEL_SHEET": ["io", "default_excel_sheet"],
    # ... 50+ more hardcoded mappings
}
```

**After**: Environment variable mappings are generated dynamically from the Pydantic Config model:

```python
# New dynamic approach
from .introspection import generate_env_mappings
from .models import Config

env_mappings = generate_env_mappings(Config, self.ENV_PREFIX.rstrip("_"))
```

**Benefits**:
- Automatically generates mappings for all config fields
- No need to manually update mappings when adding new config fields
- Guaranteed consistency between config model and environment variables
- Generates 56+ mappings automatically

### 2. Enhanced Parameter Mapping System

**Before**: Parameter mappings were hardcoded in the `config_aware_init` decorator:

```python
# Old hardcoded approach
param_mappings = {
    "delimiter": "io.default_csv_delimiter",
    "sheet_name": "io.default_excel_sheet",
    # ... limited set of mappings
}
```

**After**: Dynamic parameter mapping with multiple sources and convention-based detection:

```python
# New dynamic approach with multiple sources
base_mappings = ParamMapper.get_all_mappings()
class_mappings = get_class_param_mappings(class_)
param_mappings = merge_param_mappings(base_mappings, class_mappings)

# Plus convention-based mapping for unmapped parameters
config_path = ParamMapper.get_config_path(param_name)
```

**Benefits**:
- Convention-based automatic mapping (e.g., `default_periods` → `forecasting.default_periods`)
- Class-level custom mappings via `_config_mappings` attribute
- Extensible mapping system with registration support
- Fallback to dynamic discovery for unknown parameters

### 3. New Discovery and Documentation Tools

Added comprehensive utilities for understanding and working with the configuration system:

- `list_all_config_paths()` - List all available configuration paths
- `generate_env_var_documentation()` - Generate environment variable documentation
- `generate_param_mapping_documentation()` - Generate parameter mapping documentation
- `get_config_field_info()` - Get detailed information about config fields
- `find_config_paths_by_type()` - Find config paths by type
- `validate_config_completeness()` - Validate mapping completeness
- `generate_config_summary()` - Generate comprehensive system summary

## Migration Steps

### For Library Developers

#### 1. Adding New Configuration Fields

**Before**: Required manual updates to environment variable mappings:

```python
# 1. Add field to Config model
class IOConfig(BaseModel):
    new_field: str = "default_value"

# 2. Manually add to env_mappings in manager.py
env_mappings = {
    # ... existing mappings
    "FSM_IO_NEW_FIELD": ["io", "new_field"],  # Manual addition required
}
```

**After**: Automatic - just add the field to the Config model:

```python
# 1. Add field to Config model - that's it!
class IOConfig(BaseModel):
    new_field: str = "default_value"

# Environment variable FSM_IO_NEW_FIELD is automatically available
```

#### 2. Adding Parameter Mappings

**Before**: Required editing the hardcoded dictionary:

```python
# Manual addition to param_mappings
param_mappings = {
    # ... existing mappings
    "new_param": "config.path.to.new_field",  # Manual addition
}
```

**After**: Multiple options for adding mappings:

```python
# Option 1: Register at runtime
from fin_statement_model.config import ParamMapper
ParamMapper.register_mapping("new_param", "config.path.to.new_field")

# Option 2: Use class-level mappings
@config_aware_init
class MyClass:
    _config_mappings = {
        "new_param": "config.path.to.new_field"
    }
    
    def __init__(self, new_param=None):
        self.new_param = new_param

# Option 3: Use conventions (automatic)
# Parameter "default_timeout" automatically maps to "some_section.default_timeout"
```

### For Library Users

#### 1. Environment Variables

**No changes required** - all existing environment variables continue to work exactly as before. The new system generates the same mappings automatically.

#### 2. Configuration Usage

**No changes required** - all existing configuration usage continues to work. The new system is fully backward compatible.

#### 3. Custom Parameter Mappings

**New capability** - you can now define custom parameter mappings at the class level:

```python
from fin_statement_model.config import config_aware_init

@config_aware_init
class MyDataProcessor:
    # Define custom parameter mappings
    _config_mappings = {
        "custom_delimiter": "io.default_csv_delimiter",
        "custom_timeout": "api.api_timeout",
    }
    
    def __init__(self, custom_delimiter=None, custom_timeout=None):
        self.delimiter = custom_delimiter
        self.timeout = custom_timeout

# Parameters automatically get values from config
processor = MyDataProcessor()  # Uses config defaults
```

## New Features Available

### 1. Configuration Discovery

```python
from fin_statement_model.config import (
    list_all_config_paths,
    get_config_field_info,
    find_config_paths_by_type
)

# List all available configuration paths
paths = list_all_config_paths()
print(f"Available config paths: {len(paths)}")

# Get detailed information about a specific field
info = get_config_field_info("logging.level")
print(f"Type: {info['type']}, Default: {info['default']}")

# Find all boolean configuration fields
bool_configs = find_config_paths_by_type(bool)
print(f"Boolean configs: {bool_configs}")
```

### 2. Documentation Generation

```python
from fin_statement_model.config import (
    generate_env_var_documentation,
    generate_param_mapping_documentation,
    generate_config_summary
)

# Generate environment variable documentation
env_doc = generate_env_var_documentation()
with open("env_vars.md", "w") as f:
    f.write(env_doc)

# Generate parameter mapping documentation
param_doc = generate_param_mapping_documentation()
with open("param_mappings.md", "w") as f:
    f.write(param_doc)

# Generate comprehensive system summary
summary = generate_config_summary()
print(summary)
```

### 3. Validation and Completeness Checking

```python
from fin_statement_model.config import validate_config_completeness

# Validate that all config fields have proper mappings
results = validate_config_completeness()

if results["missing_env_vars"]:
    print(f"Missing env vars: {results['missing_env_vars']}")

if results["missing_param_mappings"]:
    print(f"Potential missing param mappings: {results['missing_param_mappings']}")
```

## Convention-Based Parameter Mapping

The new system automatically maps parameters following these conventions:

| Pattern | Example | Maps To |
|---------|---------|---------|
| `default_*` | `default_periods` | `forecasting.default_periods` |
| `*_timeout` | `api_timeout` | `api.api_timeout` |
| `*_format` | `number_format` | `display.default_number_format` |
| `auto_*` | `auto_clean_data` | `preprocessing.auto_clean_data` |

This means many parameters will automatically get config mappings without any manual setup.

## Testing the New System

All new functionality is thoroughly tested:

- **116 total tests** covering all configuration functionality
- **18 tests** for introspection utilities
- **24 tests** for parameter mapping utilities  
- **29 tests** for discovery utilities
- **Full backward compatibility** verified

## Performance Impact

The new system has minimal performance impact:

- Environment variable mappings are generated once at startup
- Parameter mappings use efficient lookup with caching
- Discovery tools are designed for development/debugging use
- All existing functionality maintains the same performance characteristics

## Troubleshooting

### Issue: Custom parameter not getting config value

**Solution**: Check if the parameter follows naming conventions or add explicit mapping:

```python
# Option 1: Use naming convention
def my_function(default_periods=None):  # Automatically maps to forecasting.default_periods
    pass

# Option 2: Add explicit mapping
ParamMapper.register_mapping("my_param", "my.config.path")

# Option 3: Use class-level mapping
@config_aware_init
class MyClass:
    _config_mappings = {"my_param": "my.config.path"}
```

### Issue: Environment variable not recognized

**Solution**: Check that the config field exists in the Config model:

```python
from fin_statement_model.config import list_all_config_paths

# Check if your config path exists
paths = list_all_config_paths()
if "my.config.path" not in paths:
    print("Config field doesn't exist - add it to the Config model")
```

### Issue: Need to understand available configurations

**Solution**: Use the discovery tools:

```python
from fin_statement_model.config import generate_config_summary

# Get comprehensive overview
summary = generate_config_summary()
print(summary)
```

## Summary

The new dynamic configuration system provides:

✅ **Automatic environment variable mapping** - no more manual updates  
✅ **Convention-based parameter mapping** - automatic mapping for common patterns  
✅ **Extensible mapping system** - easy to add custom mappings  
✅ **Comprehensive discovery tools** - understand and document the system  
✅ **Full backward compatibility** - existing code continues to work  
✅ **Thorough testing** - 116 tests ensure reliability  

The system is now more maintainable, extensible, and user-friendly while maintaining full backward compatibility. 