# IO Module Migration Guide

This guide helps you migrate from the old validation system to the new unified validator in the `fin_statement_model.io` module.

## Overview of Changes

The IO module has been refactored to:
1. Eliminate code duplication
2. Provide a unified validation system
3. Improve error handling consistency
4. Add reusable base implementations

## Validation System Migration

### Old System (Removed)

Previously, there were two separate validators:
- `NodeNameValidator`: Basic validation and standardization (REMOVED)
- `ContextAwareNodeValidator`: Pattern recognition and context awareness (REMOVED)

### New System (Current)

The new `UnifiedNodeValidator` combines all functionality into a single, more efficient implementation.

## Migration Examples

### Basic Validation

**Old approach (no longer available):**
```python
# This code will no longer work - the module has been removed
from fin_statement_model.io.node_name_validator import NodeNameValidator  # Module removed!

validator = NodeNameValidator(
    strict_mode=False,
    auto_standardize=True,
    warn_on_non_standard=True
)

std_name, is_valid, message = validator.validate_and_standardize("sales")
```

**New approach (required):**
```python
from fin_statement_model.io.validation import UnifiedNodeValidator

validator = UnifiedNodeValidator(
    strict_mode=False,
    auto_standardize=True,
    warn_on_non_standard=True
)

result = validator.validate("sales")
std_name = result.standardized_name
is_valid = result.is_valid
message = result.message
```

### Context-Aware Validation

**Old approach (no longer available):**
```python
# This code will no longer work - the module has been removed
from fin_statement_model.io.context_aware_validator import ContextAwareNodeValidator  # Module removed!

validator = ContextAwareNodeValidator(
    validate_subnodes=True,
    validate_formulas=True
)

std_name, is_valid, message, category = validator.validate_node(
    "revenue_q1",
    node_type="data"
)
```

**New approach (required):**
```python
from fin_statement_model.io.validation import UnifiedNodeValidator

validator = UnifiedNodeValidator(
    enable_patterns=True  # Enables sub-node and formula recognition
)

result = validator.validate(
    "revenue_q1",
    node_type="data"
)
category = result.category  # "subnode"
```

### Batch Validation

**Old approach (no longer available):**
```python
# This code will no longer work - the module has been removed
from fin_statement_model.io.node_name_validator import NodeNameValidator  # Module removed!

validator = NodeNameValidator()
results = validator.validate_batch(["revenue", "sales", "custom_item"])
```

**New approach (required):**
```python
from fin_statement_model.io.validation import UnifiedNodeValidator

validator = UnifiedNodeValidator()
results = validator.validate_batch(["revenue", "sales", "custom_item"])
# Returns dict[str, ValidationResult] instead of dict[str, tuple]
```

### Graph Validation

**Old approach (no longer available):**
```python
# This code will no longer work - the module has been removed
from fin_statement_model.io.context_aware_validator import ContextAwareNodeValidator  # Module removed!

validator = ContextAwareNodeValidator()
report = validator.validate_graph_nodes(graph.nodes.values())
```

**New approach (required):**
```python
from fin_statement_model.io.validation import UnifiedNodeValidator

validator = UnifiedNodeValidator()
report = validator.validate_graph(graph.nodes.values())
```

## Key Differences

### 1. Return Types

The new validator returns `ValidationResult` objects instead of tuples:

```python
# Old: Returns tuple (no longer available)
# std_name, is_valid, message = validator.validate_and_standardize("sales")

# New: Returns ValidationResult object
result = validator.validate("sales")
print(result.original_name)      # "sales"
print(result.standardized_name)  # "revenue"
print(result.is_valid)          # True
print(result.message)           # "Standardized 'sales' to 'revenue'"
print(result.category)          # "alternate"
print(result.confidence)        # 1.0
print(result.suggestions)       # []
```

### 2. Enhanced Features

The unified validator provides additional features:

- **Confidence scores**: Indicates validation confidence (0.0 to 1.0)
- **Suggestions**: Provides improvement suggestions for non-standard names
- **Caching**: Improves performance for repeated validations
- **Better pattern recognition**: More accurate sub-node and formula detection

### 3. Simplified API

All validation goes through a single `validate()` method:

```python
# Simple validation
result = validator.validate("revenue")

# With context
result = validator.validate(
    "revenue_margin",
    node_type="calculation",
    parent_nodes=["revenue", "gross_profit"]
)
```

## Backward Compatibility

For easier migration, compatibility functions are provided:

```python
from fin_statement_model.io.validation import validate_node_name

# Works like the old NodeNameValidator.validate_and_standardize()
std_name, is_valid, message = validate_node_name("sales", auto_standardize=True)
```

## Step-by-Step Migration

1. **Update imports:**
   ```python
   # Remove these imports (modules no longer exist):
   # from fin_statement_model.io.node_name_validator import NodeNameValidator
   # from fin_statement_model.io.context_aware_validator import ContextAwareNodeValidator
   
   # Use this instead:
   from fin_statement_model.io.validation import UnifiedNodeValidator
   ```

2. **Update validator creation:**
   ```python
   # Instead of creating two validators:
   # basic_validator = NodeNameValidator(...)  # No longer available
   # context_validator = ContextAwareNodeValidator(...)  # No longer available
   
   # Create one unified validator:
   validator = UnifiedNodeValidator(
       strict_mode=False,
       auto_standardize=True,
       warn_on_non_standard=True,
       enable_patterns=True
   )
   ```

3. **Update validation calls:**
   ```python
   # Replace tuple unpacking:
   # std_name, is_valid, message = validator.validate_and_standardize(name)  # Old API
   
   # With result object access:
   result = validator.validate(name)
   if result.is_valid:
       use_name = result.standardized_name
   ```

4. **Update batch operations:**
   ```python
   # The batch methods now return ValidationResult objects:
   results = validator.validate_batch(names)
   for name, result in results.items():
       print(f"{name}: {result.category} - {result.message}")
   ```

## Common Patterns

### Import-time Validation

```python
from fin_statement_model.io.validation import UnifiedNodeValidator
from fin_statement_model.io import read_data

# Create validator for import
validator = UnifiedNodeValidator(auto_standardize=True)

# Read data
graph = read_data("excel", "data.xlsx")

# Validate all nodes
report = validator.validate_graph(graph.nodes.values())
if report["by_validity"]["invalid"] > 0:
    print(f"Warning: {report['by_validity']['invalid']} invalid node names found")
    for name, suggestions in report["suggestions"].items():
        print(f"  {name}: {'; '.join(suggestions)}")
```

### Strict Import Mode

```python
validator = UnifiedNodeValidator(strict_mode=True)

for name in imported_names:
    result = validator.validate(name)
    if not result.is_valid:
        raise ValueError(f"Invalid node name '{name}': {result.message}")
```

### Pattern Analysis

```python
validator = UnifiedNodeValidator()

# Analyze node patterns in your data
results = validator.validate_batch(node_names)
pattern_counts = {}
for result in results.values():
    pattern_counts[result.category] = pattern_counts.get(result.category, 0) + 1

print("Node pattern distribution:")
for category, count in pattern_counts.items():
    print(f"  {category}: {count}")
```

## Important Note

**The old validator modules have been removed from the codebase.** If you have code that still imports from `node_name_validator` or `context_aware_validator`, it will fail with an ImportError. You must update your code to use the new `UnifiedNodeValidator`.

## Getting Help

If you encounter issues during migration:

1. Check the validation result's `message` and `suggestions` fields
2. Enable debug logging: `logging.getLogger("fin_statement_model.io.validation").setLevel(logging.DEBUG)`
3. Review the comprehensive test suite in `tests/io/test_validation.py`
4. Refer to the main IO module README for more examples

## Summary

The new unified validator simplifies the API while providing more features:
- Single import instead of two
- Richer return types with more information
- Better performance through caching
- More accurate pattern recognition
- Helpful suggestions for improvements

The migration is straightforward and mostly involves updating imports and adapting to the new return type structure. 