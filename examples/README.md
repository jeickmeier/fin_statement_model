# Financial Statement Model Examples

This directory contains examples demonstrating the proper use of the `fin_statement_model` library.

## 🚀 Quick Start

The key principle when using this library is to **work with high-level abstractions** rather than building graphs directly with core functionality. The library provides a layered architecture where each layer builds upon the previous:

1. **Core Layer** - Low-level graph and node functionality (not for direct use)
2. **Statements Layer** - Statement configurations and builders (primary interface)
3. **IO Layer** - Data readers and writers
4. **Extensions Layer** - Optional plugins and advanced features

## 📋 Example Scripts

### Simple Example (`scripts/simple_example.py`)
The best starting point. Demonstrates:
- Loading financial data using `read_data()`
- Using statement configurations with `create_statement_dataframe()`
- Calculating metrics using the metrics registry
- Performing trend analysis

```python
# The recommended pattern:
from fin_statement_model.io import read_data
from fin_statement_model.statements import create_statement_dataframe

# Load your data
graph = read_data(format_type="dict", source=financial_data)

# Build statement structure and populate calculations
df = create_statement_dataframe(
    graph=graph,
    config_path_or_dir="path/to/statement_config.yaml",
    format_kwargs={"should_apply_signs": True}
)
```

### Statement with Adjustments (`scripts/example_statement_with_adjustments.py`)
Shows advanced features:
- Building statements from configurations
- Applying forecasts
- Adding manual adjustments
- Regenerating statements with adjustments applied

### Banking Analysis (`scripts/sector_examples/simple_banking_graph_example.py`)
Demonstrates sector-specific analysis:
- Node name validation
- Creating custom statement configurations
- Banking-specific metrics
- Metric interpretation and ratings

## 📁 Configuration Files

### Statement Configurations (`examples/`)
- `balance_sheet.json` - Standard balance sheet structure
- `income_statement.json` - Standard income statement structure

These define the hierarchical structure of financial statements, including:
- Sections and subsections
- Line items linked to data nodes
- Calculated items (subtotals, derived metrics)
- Display formatting options

## ⚠️ Common Pitfalls to Avoid

### ❌ DON'T: Build graphs manually
```python
# WRONG - Don't do this!
from fin_statement_model.core.graph import Graph
graph = Graph(periods=["2021", "2022", "2023"])
graph.add_financial_statement_item("revenue", {...})
```

### ✅ DO: Use the IO layer to load data
```python
# CORRECT - Use the high-level interface
from fin_statement_model.io import read_data
graph = read_data(format_type="dict", source=data)
```

### ❌ DON'T: Manually create calculation nodes
```python
# WRONG - Don't manually add calculations
graph.add_calculation("gross_profit", ["revenue", "cogs"], "addition")
```

### ✅ DO: Let statement configurations handle calculations
```python
# CORRECT - Define calculations in statement config
# The create_statement_dataframe() function will create all necessary nodes
df = create_statement_dataframe(graph, config_path="income_statement.yaml")
```

## 🏗️ Best Practices

1. **Start with Data Loading**: Use appropriate readers (dict, excel, csv, fmp, etc.)
   ```python
   graph = read_data(format_type="excel", source="financials.xlsx", sheet_name="Data")
   ```

2. **Define Statement Structure**: Use YAML/JSON configurations to define your statements
   - Reuse standard configurations when possible
   - Create custom configs for specialized needs

3. **Let the Framework Work**: The statement layer will:
   - Validate your configuration
   - Build the statement structure
   - Create calculation nodes automatically
   - Handle dependencies and ordering

4. **Use the Metrics Registry**: For financial analysis
   ```python
   from fin_statement_model.core.metrics import calculate_metric, interpret_metric
   
   value = calculate_metric("return_on_equity", data_nodes, "2023")
   interpretation = interpret_metric(metric_def, value)
   ```

5. **Leverage Extensions**: For advanced features like LLM-powered analysis
   ```python
   from fin_statement_model.extensions.llm import MetricInterpreter
   ```

## 📊 Data Sources

The library supports multiple data sources through the IO layer:

- **Dictionary**: In-memory Python dictionaries
- **DataFrame**: Pandas DataFrames
- **Excel**: `.xlsx` files with configurable sheet/column mapping
- **CSV**: Comma-separated values with flexible column mapping
- **FMP API**: Financial Modeling Prep API integration
- **Graph Definition**: Serialized graph structures

## 🔧 Running the Examples

1. Ensure you have the library installed:
   ```bash
   pip install -e .
   ```

2. Run any example:
   ```bash
   python examples/scripts/simple_example.py
   ```

3. For examples that need configuration files, ensure you're running from the project root:
   ```bash
   cd /path/to/fin_statement_model
   python examples/scripts/example_statement_with_adjustments.py
   ```

## 📚 Further Reading

- See the main project README for installation and setup
- Check `docs/` for detailed API documentation
- Review `fin_statement_model/statements/config/mappings/` for example configurations
- Explore the metrics registry at `fin_statement_model/core/metrics/metric_defn/`

## 💡 Tips

- Use logging to debug issues: `logging.basicConfig(level=logging.DEBUG)`
- The library validates node names - use the `NodeNameValidator` for consistency
- Statement configurations support nested sections and complex calculations
- Metrics come with built-in interpretations and thresholds
- Extensions can be loaded dynamically for additional functionality

Remember: **Always use the high-level abstractions provided by the statements and IO layers rather than working directly with core components.** 