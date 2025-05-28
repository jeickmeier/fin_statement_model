# Financial Statement Model IO Module

The `fin_statement_model.io` module provides a unified interface for reading and writing financial model data from/to various formats using a registry-based approach.

## Overview

The IO module follows a plugin architecture where readers and writers are registered for specific formats. This allows for easy extension and consistent error handling across all IO operations.

### Key Features

- **Registry-based architecture**: Dynamically register and discover IO handlers
- **Consistent error handling**: Standardized exceptions and error messages
- **Configuration validation**: Pydantic models for type-safe configuration
- **Reusable components**: Base classes and mixins reduce code duplication
- **Unified validation**: Single validator for all node name validation needs

## Architecture

### Core Components

#### Registry System (`registry.py`, `registry_base.py`)

The registry system manages format handlers:

```python
from fin_statement_model.io import read_data, write_data, list_readers, list_writers

# Read data from various formats
graph = read_data("excel", "data.xlsx", sheet_name="Sheet1")
graph = read_data("csv", "data.csv", item_col="Item", period_col="Period", value_col="Value")
graph = read_data("fmp", "AAPL", statement_type="income_statement", api_key="...")

# Write data to various formats
write_data("excel", graph, "output.xlsx", sheet_name="Results")
df = write_data("dataframe", graph, None)  # Returns DataFrame
data_dict = write_data("dict", graph, None)  # Returns dict
```

#### Base Implementations (`base_implementations.py`)

Provides reusable base classes:

- `FileBasedReader`: Common file validation and error handling
- `ConfigurableReaderMixin`: Configuration value access helpers
- `DataFrameBasedWriter`: Consistent data extraction from graphs
- `BatchProcessingMixin`: Utilities for processing large datasets

#### Utilities (`utils.py`)

Common utilities for all IO operations:

- `@handle_read_errors()`: Decorator for consistent read error handling
- `@handle_write_errors()`: Decorator for consistent write error handling
- `ValueExtractionMixin`: Standardized value extraction from nodes
- `ValidationResultCollector`: Batch validation result collection

#### Unified Validation (`validation.py`)

The new `UnifiedNodeValidator` combines all validation functionality:

```python
from fin_statement_model.io.validation import UnifiedNodeValidator

# Create validator with desired settings
validator = UnifiedNodeValidator(
    strict_mode=False,         # Allow non-standard names
    auto_standardize=True,     # Convert known alternates
    warn_on_non_standard=True, # Log warnings
    enable_patterns=True       # Recognize sub-nodes and formulas
)

# Validate a single node
result = validator.validate(
    "revenue_q1",
    node_type="data",
    parent_nodes=["revenue"]
)

# Validate an entire graph
report = validator.validate_graph(graph.nodes.values())
```

### Readers

All readers inherit from `DataReader` and are registered with `@register_reader()`:

- **ExcelReader**: Reads from Excel files with flexible mapping
- **CsvReader**: Reads from CSV files in long format
- **DataFrameReader**: Reads from pandas DataFrames
- **DictReader**: Reads from Python dictionaries
- **FmpReader**: Reads from Financial Modeling Prep API

### Writers

All writers inherit from `DataWriter` and are registered with `@register_writer()`:

- **ExcelWriter**: Writes to Excel files
- **DataFrameWriter**: Converts to pandas DataFrame
- **DictWriter**: Converts to Python dictionary
- **MarkdownWriter**: Writes formatted financial statements

## Configuration Models

All readers and writers use Pydantic models for configuration validation:

```python
# Example: Excel reader configuration
from fin_statement_model.io.config.models import ExcelReaderConfig

config = ExcelReaderConfig(
    source="data.xlsx",
    format_type="excel",
    sheet_name="Sheet1",
    items_col=1,        # 1-indexed column for items
    periods_row=1,      # 1-indexed row for periods
    mapping_config={    # Optional name mapping
        "Sales": "revenue",
        "COGS": "cost_of_goods_sold"
    }
)
```

## Error Handling

The module provides specific exception types:

- `IOError`: Base exception for all IO errors
- `ReadError`: Errors during read operations
- `WriteError`: Errors during write operations
- `FormatNotSupportedError`: Unknown format requested

All exceptions include context about the operation:

```python
try:
    graph = read_data("excel", "missing.xlsx")
except ReadError as e:
    print(f"Failed to read: {e}")
    print(f"Source: {e.source_or_target}")
    print(f"Format: {e.format_type}")
    print(f"Original error: {e.original_error}")
```

## Node Name Validation

The unified validation system handles all validation scenarios:

### Validation Categories

1. **Standard nodes**: Defined in `standard_nodes.yaml`
2. **Alternate names**: Map to standard names (e.g., "sales" → "revenue")
3. **Sub-nodes**: Recognized patterns (e.g., "revenue_q1", "revenue_europe")
4. **Formula nodes**: Calculation patterns (e.g., "gross_margin", "current_ratio")
5. **Derived nodes**: Related to parent nodes
6. **Custom nodes**: User-defined names

### Pattern Recognition

The validator recognizes common patterns:

- Quarterly: `revenue_q1`, `revenue_q2`
- Annual: `revenue_2023`, `revenue_fy2024`
- Monthly: `revenue_jan`, `revenue_feb`
- Scenarios: `revenue_budget`, `revenue_forecast`
- Segments: `revenue_north_america`, `revenue_retail`
- Formulas: `gross_profit_margin`, `debt_equity_ratio`

### Validation Modes

```python
# Flexible mode (default) - allows custom names
validator = UnifiedNodeValidator(strict_mode=False)

# Strict mode - only standard names allowed
validator = UnifiedNodeValidator(strict_mode=True)

# Disable pattern recognition
validator = UnifiedNodeValidator(enable_patterns=False)
```

## Extending the IO Module

### Adding a New Reader

```python
from fin_statement_model.io import DataReader, register_reader
from fin_statement_model.io.utils import handle_read_errors

@register_reader("myformat")
class MyFormatReader(DataReader):
    def __init__(self, cfg: MyFormatReaderConfig):
        self.cfg = cfg
    
    @handle_read_errors()
    def read(self, source: str, **kwargs) -> Graph:
        # Implementation here
        pass
```

### Adding a New Writer

```python
from fin_statement_model.io import DataWriter, register_writer
from fin_statement_model.io.utils import handle_write_errors

@register_writer("myformat")
class MyFormatWriter(DataWriter):
    def __init__(self, cfg: MyFormatWriterConfig):
        self.cfg = cfg
    
    @handle_write_errors()
    def write(self, graph: Graph, target: str, **kwargs) -> None:
        # Implementation here
        pass
```

## Migration Guide

### From Old Validators to UnifiedNodeValidator

```python
# Old approach (no longer available - modules removed)
# from fin_statement_model.io.node_name_validator import NodeNameValidator
# from fin_statement_model.io.context_aware_validator import ContextAwareNodeValidator
# 
# basic_validator = NodeNameValidator(strict_mode=False)
# context_validator = ContextAwareNodeValidator()

# New unified approach
from fin_statement_model.io.validation import UnifiedNodeValidator

validator = UnifiedNodeValidator(
    strict_mode=False,
    enable_patterns=True  # Includes context awareness
)
```

### Backward Compatibility

For backward compatibility, the old validation functions are still available:

```python
from fin_statement_model.io.validation import validate_node_name

# Works like the old NodeNameValidator
std_name, is_valid, message = validate_node_name("sales", auto_standardize=True)
```

## Best Practices

1. **Use the facade functions**: Prefer `read_data()` and `write_data()` over direct reader/writer instantiation
2. **Handle errors appropriately**: Catch specific exception types for better error messages
3. **Validate node names**: Use the unified validator during data import
4. **Configure readers properly**: Use Pydantic models for type-safe configuration
5. **Leverage base classes**: Extend base implementations for consistent behavior

## Examples

### Reading Financial Data

```python
from fin_statement_model.io import read_data

# From Excel with mapping
graph = read_data(
    "excel",
    "financials.xlsx",
    sheet_name="Income Statement",
    mapping_config={
        "Sales Revenue": "revenue",
        "Cost of Sales": "cost_of_goods_sold"
    }
)

# From CSV
graph = read_data(
    "csv",
    "data.csv",
    item_col="Account",
    period_col="Period", 
    value_col="Amount"
)

# From API
graph = read_data(
    "fmp",
    "AAPL",
    statement_type="balance_sheet",
    period_type="FY",
    limit=5
)
```

### Writing Financial Data

```python
from fin_statement_model.io import write_data

# To Excel
write_data(
    "excel",
    graph,
    "output.xlsx",
    sheet_name="Financial Model",
    recalculate=True
)

# To DataFrame for analysis
df = write_data("dataframe", graph, None)

# To dictionary for serialization
data = write_data("dict", graph, None)
```

### Validating Node Names

```python
from fin_statement_model.io.validation import UnifiedNodeValidator

validator = UnifiedNodeValidator()

# Validate during import
for name in imported_names:
    result = validator.validate(name)
    if not result.is_valid and strict_import:
        raise ValueError(f"Invalid node name: {result.message}")
    
    # Use standardized name
    node_name = result.standardized_name
```

## Performance Considerations

- The unified validator includes caching for repeated validations
- Base implementations optimize value extraction and error handling
- Batch operations are supported for processing large datasets
- Registry lookups are O(1) for format resolution

## Future Enhancements

- Additional format support (JSON, YAML, Parquet)
- Streaming readers for large files
- Async IO operations
- Enhanced validation with fuzzy matching
- Plugin system for external format handlers 