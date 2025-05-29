# Financial Statements Module

The `fin_statement_model.statements` module provides tools for defining, building, managing, and presenting financial statements (Income Statement, Balance Sheet, Cash Flow Statement, etc.) based on underlying configurations.

## Overview

This module sits above the `core` layer and orchestrates the use of core components (like `Graph`, `Node`) within the context of financial statement structures. It transforms static statement configurations into dynamic calculation graphs and formatted output.

### Key Features

- **Configuration-driven**: Define statements in YAML/JSON files
- **Flexible structure**: Support for nested sections, calculations, and subtotals
- **Automatic dependency resolution**: Smart handling of item dependencies
- **Multiple output formats**: DataFrames, Excel, JSON, HTML
- **Robust error handling**: Comprehensive error collection and reporting
- **Extensible design**: Easy to add new item types and processors

## Directory Structure

```
fin_statement_model/statements/
├── __init__.py              # Main public API exports
├── errors.py                # Statement-specific exceptions
├── registry.py              # Statement registry
├── configs/                 # Configuration handling
│   ├── loader.py           # Config file loading
│   ├── models.py           # Pydantic validation models
│   └── validator.py        # StatementConfig class
├── structure/               # Statement structure definitions
│   ├── builder.py          # StatementStructureBuilder
│   ├── containers.py       # StatementStructure, Section
│   └── items.py            # LineItem, CalculatedLineItem, etc.
├── population/              # Graph population logic
│   ├── id_resolver.py      # ID resolution logic
│   ├── item_processors.py  # Item processing strategies
│   └── populator.py        # Main population function
├── formatting/              # Output formatting
│   ├── data_fetcher.py     # Data retrieval from graph
│   ├── formatter.py        # StatementFormatter
│   └── _formatting_utils.py # Internal utilities
├── orchestration/           # High-level coordination
│   ├── factory.py          # Public API facade
│   ├── orchestrator.py     # Main workflow coordination
│   ├── loader.py           # Statement loading
│   └── exporter.py         # Export functionality
├── utilities/               # Cross-cutting utilities
│   ├── result_types.py     # Result/Success/Failure types
│   └── retry_handler.py    # Retry mechanisms
└── docs/                    # Documentation
```

## Quick Start

### Basic Usage

```python
from fin_statement_model.core.graph import Graph
from fin_statement_model.statements import create_statement_dataframe

# Create a graph with your data
graph = Graph()
graph.add_node('revenue', values={'2023': 1000, '2024': 1200})
graph.add_node('cogs', values={'2023': 600, '2024': 700})

# Create statement DataFrame from configuration
df = create_statement_dataframe(
    graph=graph,
    config_path_or_dir='path/to/income_statement.yaml'
)

print(df)
```

### Export to Multiple Formats

```python
from fin_statement_model.statements import (
    export_statements_to_excel,
    export_statements_to_json
)

# Export to Excel files
export_statements_to_excel(
    graph=graph,
    config_path_or_dir='configs/',
    output_dir='output/excel/'
)

# Export to JSON files
export_statements_to_json(
    graph=graph,
    config_path_or_dir='configs/',
    output_dir='output/json/',
    writer_kwargs={'orient': 'records', 'indent': 2}
)
```

## Statement Configuration

### YAML Configuration Example

```yaml
# income_statement.yaml
id: income_statement
name: Income Statement
description: Standard income statement format
sections:
  - id: revenue_section
    name: Revenue
    items:
      - type: line_item
        id: revenue
        name: Total Revenue
        node_id: revenue_node
        
  - id: costs_section
    name: Costs
    items:
      - type: line_item
        id: cogs
        name: Cost of Goods Sold
        node_id: cogs_node
        
      - type: calculated
        id: gross_profit
        name: Gross Profit
        calculation:
          type: subtraction
          inputs: [revenue, cogs]
          
    subtotal:
      type: subtotal
      id: total_costs
      name: Total Costs
      items_to_sum: [cogs]
```

### Programmatic Configuration

```python
from fin_statement_model.statements import (
    StatementStructure,
    Section,
    LineItem,
    CalculatedLineItem,
    StatementRegistry
)

# Create statement structure programmatically
statement = StatementStructure(
    id="balance_sheet",
    name="Balance Sheet"
)

# Add sections and items
assets_section = Section(id="assets", name="Assets")
assets_section.add_item(LineItem(
    id="cash",
    name="Cash and Cash Equivalents",
    node_id="cash_node"
))

statement.add_section(assets_section)

# Register the statement
registry = StatementRegistry()
registry.register(statement)
```

## Key Concepts

### Statement Items

The module supports several types of statement items:

#### 1. LineItem
Basic items that map to existing graph nodes:

```python
revenue_item = LineItem(
    id="revenue",
    name="Total Revenue",
    node_id="revenue_data_node",
    sign_convention=1
)
```

#### 2. CalculatedLineItem
Items whose values are calculated from other items:

```python
gross_profit = CalculatedLineItem(
    id="gross_profit",
    name="Gross Profit",
    calculation={
        "type": "subtraction",
        "inputs": ["revenue", "cogs"]
    }
)
```

#### 3. MetricLineItem
Items based on registered metrics:

```python
margin_item = MetricLineItem(
    id="gross_margin",
    name="Gross Margin %",
    metric_id="margin_percentage",
    inputs={"numerator": "gross_profit", "denominator": "revenue"}
)
```

#### 4. SubtotalLineItem
Items that sum multiple other items:

```python
total_expenses = SubtotalLineItem(
    id="total_expenses",
    name="Total Operating Expenses",
    item_ids=["salaries", "rent", "utilities"]
)
```

### Advanced Usage

#### Custom Formatting

```python
from fin_statement_model.statements import StatementFormatter

formatter = StatementFormatter(statement)
df = formatter.generate_dataframe(
    graph=graph,
    should_apply_signs=True,
    include_empty_items=False,
    number_format=",.0f",
    include_metadata_cols=True
)
```

#### Error Handling with Result Types

```python
from fin_statement_model.statements.utilities import Result, Success, Failure

def safe_create_statement(config_path: str) -> Result[pd.DataFrame]:
    try:
        df = create_statement_dataframe(graph, config_path)
        return Success(df)
    except Exception as e:
        return Failure.from_exception(e)

result = safe_create_statement('config.yaml')
if result.is_success():
    df = result.get_value()
    print("Statement created successfully")
else:
    for error in result.get_errors():
        print(f"Error: {error}")
```

#### Retry Mechanisms

```python
from fin_statement_model.statements.utilities import retry_with_exponential_backoff

def create_statement_with_retry():
    return retry_with_exponential_backoff(
        operation=lambda: create_statement_dataframe(graph, config_path),
        max_attempts=3,
        base_delay=1.0
    )

retry_result = create_statement_with_retry()
if retry_result.success:
    df = retry_result.unwrap()
```

## Working with Adjustments

The module supports financial adjustments and filtering:

```python
from fin_statement_model.core.adjustments.models import AdjustmentFilterInput

# Create statement with adjustment filtering
df = formatter.generate_dataframe(
    graph=graph,
    adjustment_filter=AdjustmentFilterInput(
        adjustment_types=['accrual', 'reclassification']
    ),
    add_is_adjusted_column=True
)
```

## Data Processing Pipeline

The module follows a clear data processing pipeline:

1. **Configuration Loading**: Read YAML/JSON configs
2. **Validation**: Validate structure using Pydantic models
3. **Building**: Convert configs to `StatementStructure` objects
4. **Registration**: Store statements in registry
5. **Population**: Add calculation nodes to graph
6. **Formatting**: Fetch data and format as DataFrame
7. **Export**: Output to various formats

```python
# Complete pipeline example
from fin_statement_model.statements import (
    StatementConfig,
    StatementStructureBuilder,
    StatementRegistry,
    populate_graph_from_statement,
    StatementFormatter
)

# 1. Load and validate configuration
config_data = {...}  # From YAML/JSON
config = StatementConfig(config_data)
errors = config.validate_config()

if errors:
    print("Validation errors:", errors)
else:
    # 2. Build statement structure
    builder = StatementStructureBuilder()
    statement = builder.build(config)
    
    # 3. Register statement
    registry = StatementRegistry()
    registry.register(statement)
    
    # 4. Populate graph
    populate_errors = populate_graph_from_statement(statement, graph)
    
    # 5. Format output
    formatter = StatementFormatter(statement)
    df = formatter.generate_dataframe(graph)
```

## Testing

The module includes comprehensive testing utilities:

```python
import pytest
from fin_statement_model.statements import StatementStructure, LineItem

def test_statement_creation():
    statement = StatementStructure(id="test", name="Test Statement")
    assert statement.id == "test"
    assert statement.name == "Test Statement"

def test_line_item_validation():
    with pytest.raises(StatementError):
        LineItem(id="", name="Invalid", node_id="node")
```

## Error Handling

The module provides comprehensive error handling:

```python
from fin_statement_model.statements.errors import StatementError, ConfigurationError

try:
    df = create_statement_dataframe(graph, config_path)
except ConfigurationError as e:
    print(f"Configuration error: {e.message}")
    if e.errors:
        for error in e.errors:
            print(f"  - {error}")
except StatementError as e:
    print(f"Statement error: {e}")
```

## Best Practices

1. **Use configuration files**: Define statements in YAML for maintainability
2. **Validate early**: Always validate configurations before building
3. **Handle dependencies**: Use the retry mechanism for complex dependencies
4. **Collect errors**: Use `ErrorCollector` for batch operations
5. **Cache structures**: Reuse `StatementStructure` objects when possible
6. **Format consistently**: Use the same formatting options across statements

## API Reference

### Main Functions
- `create_statement_dataframe()`: Main orchestration function
- `export_statements_to_excel()`: Export to Excel files
- `export_statements_to_json()`: Export to JSON files
- `populate_graph_from_statement()`: Add nodes to graph

### Core Classes
- `StatementStructure`: Top-level statement container
- `Section`: Statement section container
- `LineItem`, `CalculatedLineItem`, `MetricLineItem`, `SubtotalLineItem`: Item types
- `StatementFormatter`: Formatting engine
- `StatementRegistry`: Statement management
- `IDResolver`: ID resolution logic

### Utility Classes
- `Result`, `Success`, `Failure`: Functional error handling
- `ErrorCollector`: Error aggregation
- `RetryHandler`: Retry mechanisms
- `DataFetcher`: Data retrieval from graph

## Contributing

When extending the module:

1. Follow the existing patterns for processors and builders
2. Add comprehensive error handling using `Result` types
3. Include docstrings following Google style
4. Add tests for new functionality
5. Update this README with new features

For more detailed information, see the documentation in the `docs/` directory. 