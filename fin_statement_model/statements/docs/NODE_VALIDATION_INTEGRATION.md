# UnifiedNodeValidator Integration with Statement Processing

## Overview

The statement processing system now includes comprehensive integration with the UnifiedNodeValidator to enforce naming conventions and improve graph hygiene during statement configuration parsing and building. This integration provides early validation of node IDs, automatic standardization of alternate names, and helpful suggestions for improvement.

## Benefits

- **Early Detection**: Catches naming convention violations before graph population
- **Automatic Standardization**: Converts alternate node names to standard forms
- **Improved Graph Hygiene**: Ensures consistent naming throughout the system
- **Contextual Error Messages**: Provides detailed information about where issues occur
- **Flexible Validation Modes**: Choose between strict errors or warning-only modes

## Integration Points

### 1. StatementConfig Validation

The `StatementConfig` class now supports node validation during the `validate_config()` process:

```python
from fin_statement_model.statements import StatementConfig

config = StatementConfig(
    config_data,
    enable_node_validation=True,
    node_validation_strict=False,  # Warnings only
)

errors = config.validate_config()
```

**Fields Validated:**
- Statement ID (`id`)
- Section IDs (`sections[].id`)
- Item IDs (`items[].id`)
- Node IDs (`node_id` fields)
- Standard node references (`standard_node_ref` fields)
- Calculation inputs (`calculation.inputs`)
- Metric inputs (`inputs` dictionary values)
- Subtotal inputs (`items_to_sum`)

### 2. StatementStructureBuilder Enhancement

The `StatementStructureBuilder` can perform additional validation during the build process:

```python
from fin_statement_model.statements import StatementStructureBuilder

builder = StatementStructureBuilder(
    enable_node_validation=True,
    node_validation_strict=True,  # Fail on errors
)

statement = builder.build(validated_config)
```

### 3. High-Level API Integration

The orchestration functions now support node validation:

```python
from fin_statement_model.statements.orchestration import create_statement_dataframe

df = create_statement_dataframe(
    graph=graph,
    config_path_or_dir="statements/",
    enable_node_validation=True,
    node_validation_strict=False,
)
```

## Usage Patterns

### Basic Usage with Defaults

```python
from fin_statement_model.statements import create_validated_statement_config

# Simple validation with defaults
config = create_validated_statement_config(
    config_data,
    enable_node_validation=True,
    strict_mode=False,
)

errors = config.validate_config()
if not errors:
    print("✅ Validation passed!")
```

### Custom Validator Configuration

```python
from fin_statement_model.io.validation import UnifiedNodeValidator
from fin_statement_model.statements import StatementConfig

# Create custom validator
validator = UnifiedNodeValidator(
    strict_mode=False,
    auto_standardize=True,
    enable_patterns=True,  # Recognize sub-node patterns
)

config = StatementConfig(
    config_data,
    enable_node_validation=True,
    node_validation_strict=False,
    node_validator=validator,
)
```

### High-Level Validation

```python
from fin_statement_model.statements import validate_statement_config_with_nodes

config, errors = validate_statement_config_with_nodes(
    "path/to/income_statement.yaml",
    strict_mode=True,
    auto_standardize=True,
)

if errors:
    print("Validation failed:", errors)
else:
    print("✅ Configuration is valid!")
```

### Complete Pipeline

```python
from fin_statement_model.statements import build_validated_statement_from_config

try:
    statement = build_validated_statement_from_config(
        "path/to/statement.yaml",
        strict_mode=True,
    )
    print(f"✅ Built statement: {statement.name}")
except ConfigurationError as e:
    print(f"❌ Validation failed: {e}")
```

## Validation Modes

### Non-Strict Mode (Default)
- **Invalid IDs**: Generate warnings, allow processing to continue
- **Non-standard IDs**: Generate warnings with suggestions
- **Best for**: Development and testing environments

### Strict Mode
- **Invalid IDs**: Generate errors, fail validation
- **Non-standard IDs**: Generate warnings (still processable)
- **Best for**: Production environments with strict naming requirements

## Error Types and Codes

| Error Code | Severity | Description |
|------------|----------|-------------|
| `invalid_node_id` | ERROR/WARNING | Node ID violates basic naming rules |
| `non_standard_node_id` | WARNING | Valid but non-standard node ID |
| `node_id_suggestions` | WARNING | Suggestions for improving node IDs |
| `node_validation_error` | WARNING | Unexpected error during validation |
| `build_invalid_node_id` | ERROR/WARNING | Build-time validation failure |

## Validation Context

The validator provides detailed context for each validation issue:

```python
# Example error output:
"[ERROR] statement.income_statement.section.revenue_section.item.invalid@node.id: 
Invalid item ID 'invalid@node': Non-standard node: 'invalid@node' 
(statement.income_statement.section.revenue_section.item.invalid@node.id)"
```

Context includes:
- Full path to the problematic field
- Original value that failed validation
- Reason for failure
- Location in configuration structure

## Performance Considerations

- **Caching**: Validation results are cached to avoid duplicate checks
- **Batch Operations**: Multiple IDs validated efficiently
- **Lazy Loading**: Validator created only when needed
- **Pattern Recognition**: Efficient regex-based pattern matching

## Best Practices

### 1. Enable Validation in Development
```python
# Always enable during development
config = StatementConfig(
    config_data,
    enable_node_validation=True,
    node_validation_strict=False,  # Warnings help learn standards
)
```

### 2. Use Strict Mode for Production
```python
# Enforce standards in production
config = StatementConfig(
    config_data,
    enable_node_validation=True,
    node_validation_strict=True,  # Fail on violations
)
```

### 3. Review Validation Output
```python
errors = config.validate_config()
if errors:
    print("Validation issues found:")
    for error in errors:
        print(f"  - {error}")
```

### 4. Use Convenience Functions
```python
# Simplest approach for most use cases
config, errors = validate_statement_config_with_nodes(
    config_path,
    strict_mode=False,
)
```

## Migration Guide

### Existing Code
No changes required for existing code. Node validation is **opt-in** and disabled by default.

### Enabling Validation
1. **Minimal Change**: Add `enable_node_validation=True` to existing calls
2. **Recommended**: Use convenience functions for new code
3. **Advanced**: Create custom validators for specific requirements

### Example Migration
```python
# Before
config = StatementConfig(config_data)

# After (minimal)
config = StatementConfig(config_data, enable_node_validation=True)

# After (recommended)
config = create_validated_statement_config(config_data)
```

## Troubleshooting

### Common Issues

**Issue**: "Node validation failed with invalid characters"
**Solution**: Remove special characters from node IDs, use underscores instead

**Issue**: "Non-standard node warnings"
**Solution**: Use standard node names from the registry, or enable auto-standardization

**Issue**: "Validation taking too long"
**Solution**: Check if caching is enabled, reduce config complexity

### Debug Mode
```python
import logging
logging.getLogger('fin_statement_model.statements').setLevel(logging.DEBUG)

# Now validation will log detailed debug information
```

## Examples

See `examples/scripts/node_validation_example.py` for comprehensive examples demonstrating:
- Basic validation with different modes
- Custom validator configuration
- Integration with graph operations
- Error handling and recovery
- Performance optimization techniques

## API Reference

### Main Classes
- `StatementConfig`: Enhanced with node validation capabilities
- `StatementStructureBuilder`: Build-time validation support
- `UnifiedNodeValidator`: Core validation engine

### Convenience Functions
- `create_validated_statement_config()`: Quick config creation with validation
- `create_validated_statement_builder()`: Quick builder creation with validation
- `validate_statement_config_with_nodes()`: High-level validation function
- `build_validated_statement_from_config()`: Complete pipeline function

### Configuration Parameters
- `enable_node_validation`: Enable/disable node validation
- `node_validation_strict`: Strict mode vs. warnings only
- `node_validator`: Custom UnifiedNodeValidator instance

This integration provides a robust foundation for maintaining consistent, high-quality node naming throughout the financial statement modeling system. 