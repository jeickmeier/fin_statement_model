# Declarative Adjustment Handling in Statement Configurations

## Overview

The declarative adjustment handling feature allows you to specify default adjustment filters directly in statement configuration files (YAML/JSON). This provides fine-grained control over how adjusted vs. unadjusted data is presented for different items and sections in your financial statements.

## Benefits

- **Granular Control**: Set different adjustment filters for specific items or sections
- **Configuration-Driven**: No need to modify code to change adjustment behavior
- **Hierarchical Precedence**: Clear precedence rules for filter resolution
- **Flexible Options**: Support for both simple tag-based filters and complex filter specifications

## How It Works

### Filter Precedence

When fetching data for a statement item, adjustment filters are resolved in this order (highest to lowest priority):

1. **Global Filter**: Explicitly passed to `generate_dataframe()` or similar methods
2. **Item-Level Filter**: `default_adjustment_filter` specified on the item itself
3. **Section-Level Filter**: `default_adjustment_filter` specified on the parent section
4. **No Filter**: Raw data without adjustments

### Configuration Options

You can specify `default_adjustment_filter` in two formats:

#### 1. Simple Tag List
```yaml
default_adjustment_filter:
  - "budget"
  - "forecast"
```

#### 2. Full Filter Specification
```yaml
default_adjustment_filter:
  include_scenarios: ["base", "upside"]
  exclude_scenarios: ["downside"]
  include_tags: ["budget", "forecast"]
  exclude_tags: ["preliminary"]
  require_all_tags: ["approved"]
  include_types: ["additive", "multiplicative"]
  exclude_types: ["replacement"]
  period: "2024Q1"
```

## Configuration Examples

### Example 1: Item-Level Filters

```yaml
id: income_statement
name: Income Statement
sections:
  - id: revenue_section
    name: Revenue
    items:
      - type: line_item
        id: gross_revenue
        name: Gross Revenue
        node_id: revenue_base
        # Show only budget adjustments for revenue
        default_adjustment_filter:
          include_tags: ["budget"]
          
      - type: line_item
        id: net_revenue
        name: Net Revenue
        node_id: revenue_net
        # Show all adjustments except preliminary ones
        default_adjustment_filter:
          exclude_tags: ["preliminary"]
```

### Example 2: Section-Level Filters

```yaml
id: balance_sheet
name: Balance Sheet
sections:
  - id: assets_section
    name: Assets
    # Apply forecast adjustments to all items in this section by default
    default_adjustment_filter:
      include_tags: ["forecast"]
    items:
      - type: line_item
        id: cash
        name: Cash and Equivalents
        node_id: cash_balance
        # This inherits the section's forecast filter
        
      - type: line_item
        id: receivables
        name: Accounts Receivable
        node_id: ar_balance
        # Override section filter to show actuals only
        default_adjustment_filter: []  # Empty list = no adjustments
```

### Example 3: Mixed Filter Types

```yaml
id: cash_flow
name: Cash Flow Statement
sections:
  - id: operating_section
    name: Operating Activities
    # Section-level filter for all operating items
    default_adjustment_filter:
      include_scenarios: ["base", "optimistic"]
      exclude_types: ["replacement"]
    items:
      - type: line_item
        id: net_income
        name: Net Income
        node_id: ni_base
        # Simple tag filter overrides complex section filter
        default_adjustment_filter: ["actuals", "budget"]
        
      - type: calculated
        id: adjusted_income
        name: Adjusted Net Income
        calculation:
          type: addition
          inputs: ["net_income", "adjustments"]
        # Uses section filter (complex filter specification)
```

## API Usage

### Basic Usage with Default Filters

```python
from fin_statement_model.statements import create_statement_dataframe

# Load configuration with default adjustment filters
df = create_statement_dataframe(
    graph=my_graph,
    config_path="statements/income_statement.yaml"
    # No adjustment_filter specified - uses defaults from config
)
```

### Override Default Filters

```python
from fin_statement_model.statements import StatementFormatter
from fin_statement_model.core.adjustments.models import AdjustmentFilter

# Load statement structure
statement = build_validated_statement_from_config("config.yaml")
formatter = StatementFormatter(statement)

# Override all default filters with a global filter
global_filter = AdjustmentFilter(include_tags={"budget", "actual"})
df = formatter.generate_dataframe(
    graph=my_graph,
    adjustment_filter=global_filter  # Overrides all default filters
)
```

### Check What Filters Are Applied

```python
# Access default filters from structure objects
for section in statement.sections:
    print(f"Section {section.id}: {section.default_adjustment_filter}")
    
    for item in section.items:
        if hasattr(item, 'default_adjustment_filter'):
            print(f"  Item {item.id}: {item.default_adjustment_filter}")
```

## Advanced Use Cases

### Scenario-Based Statements

```yaml
id: scenario_analysis
name: Scenario Analysis
sections:
  - id: base_case
    name: Base Case
    default_adjustment_filter:
      include_scenarios: ["base"]
    items:
      # All items show base scenario by default
      
  - id: stress_test
    name: Stress Test
    default_adjustment_filter:
      include_scenarios: ["stress", "adverse"]
    items:
      # All items show stress scenario by default
```

### Period-Specific Filters

```yaml
sections:
  - id: current_period
    name: Current Period Results
    default_adjustment_filter:
      period: "2024Q4"  # Only show adjustments effective in Q4
      include_tags: ["approved"]
    items:
      # Items inherit period-specific filter
```

### Audit vs. Management Views

```yaml
# Management view - includes all adjustments
sections:
  - id: management_view
    name: Management View
    default_adjustment_filter:
      include_tags: ["budget", "forecast", "management"]
    
# Audit view - only approved adjustments  
sections:
  - id: audit_view
    name: Audit View
    default_adjustment_filter:
      include_tags: ["approved", "audited"]
      exclude_tags: ["preliminary"]
```

## Filter Resolution Examples

Given this configuration:
```yaml
sections:
  - id: revenue
    name: Revenue
    default_adjustment_filter: ["budget"]  # Section level
    items:
      - id: gross_revenue
        name: Gross Revenue
        node_id: revenue_node
        default_adjustment_filter: ["actual"]  # Item level
```

**Scenarios:**
1. `formatter.generate_dataframe(graph)` 
   → Uses item filter: `["actual"]`

2. `formatter.generate_dataframe(graph, adjustment_filter=["forecast"])`
   → Uses global filter: `["forecast"]` (overrides item filter)

3. Item without `default_adjustment_filter` in revenue section
   → Uses section filter: `["budget"]`

## Best Practices

1. **Start with Section Filters**: Apply common filters at the section level
2. **Override When Needed**: Use item-level filters for exceptions
3. **Document Filter Logic**: Add comments explaining why specific filters are used
4. **Test Filter Combinations**: Verify that filter precedence works as expected
5. **Use Meaningful Tags**: Choose descriptive tag names that indicate purpose
6. **Consider Performance**: Complex filters may impact data fetching speed

## Migration Guide

### From Manual Filter Passing
```python
# Before: Manual filter management
budget_filter = AdjustmentFilter(include_tags={"budget"})
df = formatter.generate_dataframe(graph, adjustment_filter=budget_filter)

# After: Declarative configuration
# Add to YAML config:
# default_adjustment_filter:
#   include_tags: ["budget"]
df = formatter.generate_dataframe(graph)  # Uses config defaults
```

### From Code-Based Logic
```python
# Before: Code-based filter logic
def get_filter_for_item(item_id):
    if item_id.startswith("revenue"):
        return AdjustmentFilter(include_tags={"budget"})
    elif item_id.startswith("cost"):
        return AdjustmentFilter(include_tags={"actual"})
    return None

# After: Configuration-driven
# Move logic to YAML configuration with appropriate filters per item
```

This feature provides a powerful way to manage complex adjustment scenarios while keeping the logic declarative and maintainable in configuration files. 