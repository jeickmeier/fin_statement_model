# Financial Statement Model Examples

This directory contains examples demonstrating the proper use of the `fin_statement_model` library.

## 🚀 Quick Start

The key principle when using this library is to **work with high-level abstractions** rather than building graphs directly with core functionality. The library provides a layered architecture where each layer builds upon the previous:

1. **Core Layer** - Low-level graph and node functionality (not for direct use)
2. **Statements Layer** - Statement configurations and builders (primary interface)
3. **IO Layer** - Data readers and writers
4. **Extensions Layer** - Optional plugins and advanced features

## ⚙️ Configuration System

The library uses a centralized configuration system that controls behavior across all components. Configuration can be set through multiple sources with the following precedence (highest to lowest):

1. Runtime updates via `update_config()`
2. Environment variables (FSM_* prefix)
3. Configuration file (fsm_config.yaml)
4. User home directory (~/.fsm_config.yaml)
5. Default values

### Basic Configuration Usage

```python
from fin_statement_model import get_config, update_config

# Get current configuration
config = get_config()
print(f"Display units: {config.display.default_units}")

# Update configuration at runtime
update_config({
    "display": {
        "default_units": "USD Millions",
        "scale_factor": 0.000001
    }
})
```

### Environment Variables

- `FSM_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `FSM_API_FMP_API_KEY` - Financial Modeling Prep API key
- `FSM_DISPLAY_UNITS` - Default display units
- `FSM_VALIDATION_STRICT_MODE` - Enable strict validation (true/false)

See `scripts/config_demo.py` for a complete demonstration of the configuration system.

## 📋 Example Scripts

### Configuration Demo (`scripts/config_demo.py`)
Complete demonstration of the configuration system:
- Loading configuration from multiple sources
- Runtime configuration updates
- Environment variable usage
- Configuration file format
- Serialization and sharing

### Clean API Demo (`scripts/clean_api_demo.py`)
Shows how the library uses configuration internally for a clean API:
- Before/after comparison of API usage
- Automatic configuration defaults
- Simplified code without manual parameter passing
- Override capability when needed

### Simple Example (`scripts/simple_example.py`)
The best starting point. Demonstrates:
- Loading financial data using `read_data()`
- Defining statement configurations as Python dicts
- Creating statements with `create_statement_dataframe()`
- Calculating metrics using the metrics registry
- Performing trend analysis
- Using centralized configuration for formatting

```python
# The recommended pattern:
from fin_statement_model import get_config
from fin_statement_model.io import read_data
from fin_statement_model.statements import create_statement_dataframe
from fin_statement_model.io.specialized.statements import read_builtin_statement_config

# Configuration affects all operations
config = get_config()

# Load your data
graph = read_data(format_type="dict", source=financial_data)

# Define raw statement configurations (e.g., using built-in configs)
raw_configs = {
    "income_statement": read_builtin_statement_config("income_statement")
}

# Build statement structures and format with configured formatting
df_map = create_statement_dataframe(
    graph=graph,
    raw_configs=raw_configs,
    format_kwargs={
        "number_format": config.display.default_currency_format,
        "should_apply_signs": True,
    }
)

# Retrieve DataFrame by statement ID
df = df_map["income_statement"]
```

### Statement with Adjustments (`scripts/example_statement_with_adjustments.py`)
Shows advanced features:
- Building statements from configurations
- Applying forecasts using config defaults
- Adding manual adjustments
- Regenerating statements with adjustments applied

### Banking Analysis (`scripts/sector_examples/simple_banking_graph_example.py`)
Demonstrates sector-specific analysis:
- Node name validation with configured strictness
- Creating custom statement configurations
- Banking-specific metrics with proper formatting
- Metric interpretation and ratings

### FMP API Example (`scripts/provider_examples/fmp_example.py`)
Shows API integration:
- Using configured API keys and timeouts
- Applying display configuration to fetched data
- Caching configuration for API responses

## 📁 Configuration Files

### Example Configuration (`fsm_config.yaml.example`)
Complete example showing all available configuration options:
```yaml
# Logging configuration
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
# Display settings
display:
  default_units: "USD"
  scale_factor: 1.0
  default_currency_format: ",.0f"
  hide_zero_rows: false
  
# Validation rules
validation:
  strict_mode: false
  auto_standardize_names: true
  check_balance_sheet_balance: true
  balance_tolerance: 1.0
```

### Statement Configurations (`examples/`)
- `balance_sheet.json` - Standard balance sheet structure
- `income_statement.json` - Standard income statement structure
- `enhanced_income_statement.yaml` - Advanced formatting example

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

### ❌ DON'T: Hard-code formatting and display settings
```python
# WRONG - Don't hard-code formats
print(f"Revenue: ${value:,.0f}")
```

### ✅ DO: Use configuration for consistent formatting
```python
# CORRECT - Use centralized configuration
config = get_config()
scaled_value = value * config.display.scale_factor
print(f"Revenue: {scaled_value:{config.display.default_currency_format}} {config.display.default_units}")
```

## 🏗️ Best Practices

1. **Configure Early**: Set up your configuration before loading data
   ```python
   update_config({
       "display": {"default_units": "EUR Thousands", "scale_factor": 0.001},
       "validation": {"strict_mode": True}
   })
   ```

2. **Start with Data Loading**: Use appropriate readers (dict, excel, csv, fmp, etc.)
   ```python
   graph = read_data(format_type="excel", source="financials.xlsx", sheet_name="Data")
   ```

3. **Define Statement Structure**: Use YAML/JSON configurations to define your statements
   - Reuse standard configurations when possible
   - Create custom configs for specialized needs

4. **Let the Framework Work**: The statement layer will:
   - Validate your configuration
   - Build the statement structure
   - Create calculation nodes automatically
   - Handle dependencies and ordering

5. **Use the Metrics Registry**: For financial analysis
   ```python
   from fin_statement_model.core.metrics import calculate_metric, interpret_metric
   
   value = calculate_metric("return_on_equity", data_nodes, "2023")
   interpretation = interpret_metric(metric_def, value)
   ```

6. **Leverage Extensions**: For advanced features like LLM-powered analysis
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

2. (Optional) Set up a configuration file:
   ```bash
   cp examples/fsm_config.yaml.example fsm_config.yaml
   # Edit fsm_config.yaml with your preferences
   ```

3. (Optional) Set environment variables:
   ```bash
   export FSM_LOG_LEVEL=INFO
   export FSM_API_FMP_API_KEY=your_api_key
   ```

4. Run any example:
   ```bash
   python examples/scripts/simple_example.py
   ```

5. For examples that need configuration files, ensure you're running from the project root:
   ```bash
   cd /path/to/fin_statement_model
   python examples/scripts/example_statement_with_adjustments.py
   ```

## 📚 Further Reading

- See the main project README for installation and setup
- Check `docs/configuration_guide.md` for detailed configuration documentation
- Review `fin_statement_model/statements/config/mappings/` for example configurations
- Explore the metrics registry at `fin_statement_model/core/metrics/metric_defn/`

## 💡 Tips

- Use logging to debug issues: `update_config({"logging": {"level": "DEBUG"}})`
- The library validates node names - use the `NodeNameValidator` for consistency
- Statement configurations support nested sections and complex calculations
- Metrics come with built-in interpretations and thresholds
- Extensions can be loaded dynamically for additional functionality
- Configuration changes take effect immediately for new operations

Remember: **Always use the high-level abstractions provided by the statements and IO layers rather than working directly with core components.** The configuration system ensures consistent behavior across all operations. 