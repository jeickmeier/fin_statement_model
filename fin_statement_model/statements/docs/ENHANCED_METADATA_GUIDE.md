# Enhanced Metadata for Display Control and Units/Scaling

## Overview

The statements module now supports rich metadata for fine-grained control over statement presentation directly from YAML configurations. This includes custom number formatting, conditional hiding of items, CSS styling for web outputs, footnote references, and comprehensive units/scaling declarations.

## Features

### 1. Enhanced Display Control
- **`display_format`**: Item-specific number format strings
- **`hide_if_all_zero`**: Conditional visibility based on data values
- **`css_class`**: CSS classes for HTML/web outputs
- **`notes_references`**: Footnote and reference management

### 2. Units and Scaling Declaration
- **`units`**: Human-readable unit descriptions
- **`display_scale_factor`**: Automatic value scaling for display

## Configuration Reference

### Statement Level

```yaml
id: my_statement
name: My Financial Statement
units: "USD Thousands"              # Default units for entire statement
display_scale_factor: 0.001         # Default scaling (e.g., show in thousands)
```

### Section Level

```yaml
sections:
  - id: revenue_section
    name: Revenue
    units: "USD Millions"            # Override statement units
    display_scale_factor: 0.000001   # Show in millions
    css_class: "revenue-section"     # CSS styling
    hide_if_all_zero: false          # Section visibility control
    notes_references: ["note1"]      # Section-level footnotes
```

### Item Level

All item types (line_item, calculated, metric, subtotal) support these fields:

```yaml
items:
  - type: line_item
    id: revenue
    name: Total Revenue
    node_id: revenue_node
    
    # Display formatting
    display_format: ",.0f"           # Format: 1,234,567 (no decimals)
    hide_if_all_zero: false          # Hide if all periods are zero
    
    # Styling and references
    css_class: "revenue-line bold"   # CSS classes for HTML output
    notes_references: ["note1", "note2"]  # Footnote references
    
    # Units and scaling
    units: "USD Thousands"           # Override section/statement units
    display_scale_factor: 0.001      # Scale raw values for display
```

## Display Format Examples

### Common Number Formats

```yaml
# Whole numbers with thousands separators
display_format: ",.0f"      # 1,234,567

# Two decimal places with thousands separators  
display_format: ",.2f"      # 1,234,567.89

# Percentages
display_format: ".1%"       # 12.3%
display_format: ".2%"       # 12.34%

# Currency (combine with units)
display_format: "$,.0f"     # $1,234,567
units: "USD"

# Scientific notation
display_format: ".2e"       # 1.23e+06

# Fixed width padding
display_format: "10,.0f"    # Right-aligned in 10 characters

# Custom formats
display_format: "+,.1f"     # Always show sign: +1,234.5
```

### Format String Reference

| Format | Example Output | Use Case |
|--------|----------------|----------|
| `,.0f` | 1,234,567 | Whole dollar amounts |
| `,.2f` | 1,234.56 | Precise financial values |
| `.1%` | 12.3% | Margin/ratio calculations |
| `.2%` | 12.34% | Precise percentages |
| `+,.0f` | +1,234,567 | Emphasize positive/negative |
| `.2e` | 1.23e+06 | Very large/small numbers |

## Units and Scaling

### Hierarchical Units Resolution

Units are resolved in this priority order:
1. **Item level**: Most specific, overrides everything
2. **Section level**: Applies to all items in section
3. **Statement level**: Default for entire statement
4. **None**: No units displayed

```yaml
# Statement level - default
units: "USD Thousands"
display_scale_factor: 0.001

sections:
  - id: revenue_section
    # Section level - overrides statement
    units: "USD Millions"
    display_scale_factor: 0.000001
    
    items:
      - id: revenue
        # Item level - most specific
        units: "USD Thousands"
        display_scale_factor: 0.001
```

### Scaling Examples

```yaml
# Show values in thousands (divide by 1,000)
display_scale_factor: 0.001
units: "USD Thousands"

# Show values in millions (divide by 1,000,000)
display_scale_factor: 0.000001
units: "USD Millions"

# Convert decimals to percentages (multiply by 100)
display_scale_factor: 100
units: "Percentage"
display_format: ".1%"

# No scaling (raw values)
display_scale_factor: 1.0
```

## Conditional Visibility

### hide_if_all_zero

Items and sections can be automatically hidden when all values are zero or null:

```yaml
items:
  - id: interest_expense
    name: Interest Expense
    node_id: interest_expense_node
    hide_if_all_zero: true         # Hide if no interest expense

sections:
  - id: other_income_section
    name: Other Income/Expenses
    hide_if_all_zero: true         # Hide entire section if no other income
```

**Use Cases:**
- Optional expense categories (R&D, marketing campaigns)
- Seasonal revenue streams
- Conditional line items based on business model
- Clean presentation of zero-activity periods

## CSS Styling for Web Output

### CSS Classes

```yaml
items:
  - id: net_income
    name: Net Income
    css_class: "net-income bold-line highlight double-underline"
    
  - id: revenue
    name: Revenue  
    css_class: "revenue-line section-header"
```

### Using with StatementFormatter

```python
from fin_statement_model.statements import StatementFormatter

formatter = StatementFormatter(statement)

# Generate HTML with CSS classes
html = formatter.format_html(
    graph=graph,
    use_item_css_classes=True,
    css_styles={
        '.bold-line': 'font-weight: bold;',
        '.highlight': 'background-color: #ffffcc;',
        '.double-underline': 'border-bottom: 3px double #000;',
        '.section-header': 'background-color: #f0f0f0;'
    }
)
```

### Default CSS Classes

The formatter includes default styling:

```css
.statement-table { border-collapse: collapse; width: 100%; }
.statement-table th, .statement-table td { padding: 8px; text-align: right; border: 1px solid #ddd; }
.statement-table th { background-color: #f2f2f2; font-weight: bold; }
```

## Footnotes and References

### notes_references

Link items to footnotes or explanatory notes:

```yaml
items:
  - id: revenue
    name: Revenue
    notes_references: ["note1", "note3"]
    
  - id: tax_expense
    name: Income Tax Expense
    notes_references: ["note7", "note8"]
```

### Using with StatementFormatter

```python
# Include notes column in output
df = formatter.generate_dataframe(
    graph=graph,
    include_notes_column=True
)

# Notes appear as "note1; note3" in the notes column
```

## Advanced Usage Examples

### Mixed Units Statement

```yaml
id: mixed_units_statement
name: Multi-Unit Financial Statement
units: "USD Thousands"  # Default
display_scale_factor: 0.001

sections:
  - id: financial_section
    # Uses statement defaults: USD Thousands
    items:
      - id: revenue
        display_format: ",.0f"
        
  - id: ratios_section
    name: Financial Ratios
    units: "Percentage"
    display_scale_factor: 100
    items:
      - id: gross_margin
        display_format: ".1%"
        
  - id: operational_section
    name: Operational Metrics
    units: "Units"
    display_scale_factor: 1.0
    items:
      - id: headcount
        units: "Employees"
        display_format: ",.0f"
        
      - id: revenue_per_employee
        units: "USD per Employee"
        display_format: ",.0f"
```

### Conditional Display Statement

```yaml
id: conditional_statement
name: Statement with Conditional Items

sections:
  - id: core_operations
    name: Core Operations
    items:
      - id: base_revenue
        name: Base Revenue
        # Always shown
        
  - id: optional_items
    name: Additional Items
    hide_if_all_zero: true  # Hide section if no optional items
    items:
      - id: one_time_gain
        name: One-time Gain
        hide_if_all_zero: true
        
      - id: restructuring_cost
        name: Restructuring Costs
        hide_if_all_zero: true
        
  - id: seasonal_items
    name: Seasonal Revenue
    hide_if_all_zero: true
    items:
      - id: holiday_sales
        hide_if_all_zero: true
```

## API Integration

### StatementFormatter Options

```python
from fin_statement_model.statements import StatementFormatter

formatter = StatementFormatter(statement)

df = formatter.generate_dataframe(
    graph=graph,
    
    # Enhanced display control
    include_units_column=True,      # Show units for each item
    include_css_classes=True,       # Include CSS class metadata
    include_notes_column=True,      # Show footnote references
    apply_item_scaling=True,        # Apply display_scale_factor
    apply_item_formatting=True,     # Use item-specific formats
    respect_hide_flags=True,        # Honor hide_if_all_zero
    
    # Traditional options still work
    should_apply_signs=True,
    include_empty_items=False,
    number_format=None,  # Override item formats if specified
)
```

### HTML Output with Styling

```python
html = formatter.format_html(
    graph=graph,
    use_item_css_classes=True,
    css_styles={
        # Custom styles for your classes
        '.revenue-section': 'background-color: #e8f5e8;',
        '.bold-line': 'font-weight: bold;',
        '.highlight': 'background-color: #ffffcc;',
        '.margin-line': 'font-style: italic;',
    }
)
```

## Migration Guide

### From Basic Configurations

```yaml
# Before: Basic configuration
items:
  - type: line_item
    id: revenue
    name: Revenue
    node_id: revenue_node

# After: Enhanced configuration  
items:
  - type: line_item
    id: revenue
    name: Revenue
    node_id: revenue_node
    display_format: ",.0f"           # Add formatting
    units: "USD Thousands"           # Add units
    display_scale_factor: 0.001      # Add scaling
    css_class: "revenue-line"        # Add styling
    notes_references: ["note1"]      # Add references
```

### From Code-Based Formatting

```python
# Before: Manual formatting in code
def format_currency(value):
    return f"${value:,.0f}"

# After: Declarative in YAML
display_format: "$,.0f"
units: "USD"
```

## Best Practices

### 1. Consistent Units Strategy
- Use statement-level units for consistency
- Override at section/item level only when necessary
- Document unit meanings clearly

### 2. Scaling Strategy
- Choose appropriate scale for your audience
- Use consistent scaling within related sections
- Consider screen space and readability

### 3. Conditional Display
- Use `hide_if_all_zero` for optional items
- Group related optional items in sections
- Consider user expectations for missing items

### 4. CSS Organization
- Use meaningful class names
- Group related styles
- Consider responsive design for web outputs

### 5. Format Selection
- Match format precision to data significance
- Use percentage formats for ratios
- Consider cultural number formatting preferences

## Troubleshooting

### Common Issues

1. **Invalid Format Strings**
   ```
   Error: Invalid display_format ',.x': bad format specifier
   ```
   Solution: Use valid Python format specifications

2. **Scaling Not Applied**
   ```
   Values not scaling as expected
   ```
   Solution: Check `apply_item_scaling=True` in formatter options

3. **CSS Classes Not Appearing**
   ```
   CSS classes not in HTML output
   ```
   Solution: Use `include_css_classes=True` and `use_item_css_classes=True`

4. **Items Not Hiding**
   ```
   Items with zero values still showing
   ```
   Solution: Check `respect_hide_flags=True` and `hide_if_all_zero=True`

### Validation

The enhanced metadata includes built-in validation:

- **Format strings**: Tested against sample numbers
- **Scale factors**: Must be positive, non-zero
- **CSS classes**: No validation (allows flexibility)
- **Note references**: No validation (allows forward references)

This enhanced metadata system provides powerful, declarative control over statement presentation while maintaining the flexibility and type safety of the existing configuration system. 