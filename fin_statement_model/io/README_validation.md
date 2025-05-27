# Node Name Validation System

The `fin_statement_model` library provides a flexible node name validation system that balances standardization with the practical needs of financial modeling.

## Key Concepts

### Standard Nodes
These are the fundamental financial statement items defined in `standard_nodes.yaml`:
- `revenue`, `cost_of_goods_sold`, `gross_profit`, etc.
- Have alternate names that map to the standard (e.g., `sales` → `revenue`)
- Used by built-in metrics for consistent calculations

### Sub-Nodes
These are detailed breakdowns that aggregate to standard nodes:
- Regional: `revenue_north_america`, `revenue_europe`
- Temporal: `revenue_q1`, `revenue_2023`
- Product/Segment: `revenue_product_a`, `revenue_services`
- Scenario: `revenue_budget`, `revenue_forecast`

### Formula Nodes
These are calculated nodes with descriptive names:
- Margins: `gross_profit_margin`, `operating_margin`
- Ratios: `current_ratio`, `debt_equity_ratio`
- Growth: `revenue_growth_yoy`, `earnings_growth`

## Validation Modes

### 1. Flexible Mode (Default)
```python
validator = NodeNameValidator(
    strict_mode=False,         # Allow non-standard names
    auto_standardize=True,     # Convert known alternates
    warn_on_non_standard=True  # Log warnings for tracking
)
```
- ✅ Allows sub-nodes and custom names
- ✅ Standardizes alternate names automatically
- ✅ Provides warnings for unrecognized names
- ✅ Perfect for real-world financial models

### 2. Strict Mode
```python
validator = NodeNameValidator(
    strict_mode=True,          # Only standard names allowed
    auto_standardize=True
)
```
- ❌ Rejects non-standard names
- ✅ Ensures complete standardization
- ✅ Useful for validating metric inputs

### 3. Context-Aware Mode
```python
validator = ContextAwareNodeValidator(
    validate_subnodes=True,    # Check sub-node patterns
    validate_formulas=True     # Recognize formula patterns
)
```
- ✅ Understands node relationships
- ✅ Categorizes nodes intelligently
- ✅ Provides detailed validation reports

## Common Patterns

### Regional Breakdown
```python
# Sub-nodes that sum to revenue
revenue_north_america = FinancialStatementItemNode("revenue_north_america", [100, 110])
revenue_europe = FinancialStatementItemNode("revenue_europe", [80, 85])
revenue_asia = FinancialStatementItemNode("revenue_asia", [60, 70])

# Standard node that aggregates regions
revenue = FormulaCalculationNode(
    name="revenue",  # Standard name
    inputs=[revenue_north_america, revenue_europe, revenue_asia],
    formula="{revenue_north_america} + {revenue_europe} + {revenue_asia}"
)
```

### Time-Based Analysis
```python
# Quarterly nodes
revenue_q1 = FinancialStatementItemNode("revenue_q1", [250])
revenue_q2 = FinancialStatementItemNode("revenue_q2", [260])
revenue_q3 = FinancialStatementItemNode("revenue_q3", [270])
revenue_q4 = FinancialStatementItemNode("revenue_q4", [280])

# Annual total
revenue = FormulaCalculationNode(
    name="revenue",
    inputs=[revenue_q1, revenue_q2, revenue_q3, revenue_q4],
    formula="{revenue_q1} + {revenue_q2} + {revenue_q3} + {revenue_q4}"
)
```

### Formula Nodes
```python
# Margin calculations (formula pattern nodes)
gross_margin_pct = FormulaCalculationNode(
    name="gross_margin_pct",  # Formula pattern name
    inputs=[gross_profit, revenue],
    formula="{gross_profit} / {revenue} * 100"
)

# Custom adjustments
ebitda_adjustment = FinancialStatementItemNode(
    name="ebitda_one_time_adjustment",  # Custom name
    values=[10, 0, -5]
)
```

## Best Practices

### 1. Use Standard Names for Aggregates
When creating nodes that represent totals, use standard names:
```python
# Good: Use standard name for the total
revenue = sum_of_regions  # name="revenue"

# Avoid: Don't use custom names for standard concepts
total_sales = sum_of_regions  # name="total_sales" 
```

### 2. Use Consistent Sub-Node Patterns
Follow patterns for sub-nodes to enable pattern recognition:
```python
# Good: Consistent pattern
revenue_north_america
revenue_europe
revenue_asia_pacific

# Avoid: Inconsistent naming
revenue_NA
european_revenue
asiapac_sales
```

### 3. Document Custom Nodes
For truly custom nodes, add clear descriptions:
```python
# Custom adjustment with clear name
covid_revenue_impact = FinancialStatementItemNode(
    name="covid_revenue_impact",
    values=[-50, -30, -10],
    metadata={"description": "Revenue impact from COVID-19 lockdowns"}
)
```

### 4. Validate During Import
Always validate when importing data:
```python
# In a data reader
validator = NodeNameValidator(auto_standardize=True)

for row in data:
    original_name = row['item']
    std_name, is_valid, msg = validator.validate_and_standardize(original_name)
    
    if not is_valid and strict_required:
        raise ValueError(f"Invalid node name: {original_name}")
    
    # Create node with standardized or original name
    node = FinancialStatementItemNode(name=std_name, values=row['values'])
```

## Integration with Metrics

Standard metrics expect standard node names:
```python
# This metric expects nodes named 'current_assets' and 'current_liabilities'
current_ratio = graph.calculate_metric("current_ratio")

# If your nodes are named differently, the metric won't find them
# That's why standardization is important for metric compatibility
```

Sub-nodes and custom nodes can still be used in custom metrics:
```python
# Custom metric using sub-nodes
regional_concentration = FormulaCalculationNode(
    name="north_america_revenue_concentration",
    inputs=[revenue_north_america, revenue],
    formula="{revenue_north_america} / {revenue} * 100"
)
```

## Summary

The validation system provides the flexibility needed for real-world financial modeling while encouraging standardization where it matters:

- ✅ **Standard nodes** for compatibility with built-in metrics
- ✅ **Sub-nodes** for detailed analysis and drill-downs
- ✅ **Formula nodes** for calculated metrics and ratios
- ✅ **Custom nodes** for special adjustments and client-specific items

Use `strict_mode=False` (default) for most use cases, and leverage the context-aware validator when you need detailed validation reports. 