# Contra Items Support in Financial Statements

## Overview

The Financial Statement Model now supports "contra" items - accounts that naturally reduce the balance of their category while maintaining proper accounting presentation. Contra items like Accumulated Depreciation, Treasury Stock, and Sales Returns can now be displayed with appropriate formatting that aligns with accounting conventions.

## Benefits

- **Intuitive Display**: Contra items display naturally (e.g., in parentheses) while calculations remain correct
- **Accounting Standards Compliance**: Follows standard accounting presentation practices
- **Flexible Formatting**: Multiple display styles for different preferences
- **Automatic Styling**: CSS classes automatically applied for web-based outputs
- **Clear Separation**: Calculation logic (`sign_convention`) separated from display logic (`is_contra`)

## How It Works

### Dual Convention System

The system uses two complementary attributes:

1. **`sign_convention`**: Controls calculation behavior (how the item affects subtotals)
   - `1` (positive): Item adds to subtotals
   - `-1` (negative): Item subtracts from subtotals

2. **`is_contra`**: Controls display formatting (how the item appears to users)
   - `false` (default): Normal display formatting
   - `true`: Special contra formatting (parentheses, brackets, etc.)

### Example: Treasury Stock

```yaml
- id: treasury_stock
  name: Less: Treasury Stock
  type: line_item
  node_id: treasury_stock
  sign_convention: -1  # Reduces total equity in calculations
  is_contra: true      # Display with contra formatting
```

This configuration:
- **Calculates correctly**: Subtracts treasury stock from total equity
- **Displays intuitively**: Shows as "(25,000)" or with other contra formatting
- **Maintains semantics**: Clearly indicates this is a contra-equity item

## Configuration

### Basic Configuration

Add `is_contra: true` to any item that should be displayed as a contra item:

```yaml
items:
  - id: accumulated_depreciation
    name: Less: Accumulated Depreciation
    type: line_item
    node_id: accumulated_depreciation
    sign_convention: -1  # Calculation: reduces asset value
    is_contra: true      # Display: show as contra item
```

### With Custom Styling

Combine with CSS classes for enhanced presentation:

```yaml
items:
  - id: sales_returns
    name: Less: Sales Returns & Allowances
    type: line_item
    node_id: sales_returns_allowances
    sign_convention: -1
    is_contra: true
    css_class: "revenue-contra highlight"  # Custom styling
```

## Display Styles

### Available Styles

The formatter supports multiple contra display styles:

| Style | Example Output | Description |
|-------|---------------|-------------|
| `parentheses` | `(25,000.00)` | Default - industry standard |
| `negative_sign` | `-25,000.00` | Explicit negative sign |
| `brackets` | `[25,000.00]` | Square brackets |

### Setting Display Style

#### Global Style (All Contra Items)

```python
from fin_statement_model.statements import StatementFormatter

formatter = StatementFormatter(statement)
df = formatter.generate_dataframe(
    graph=graph,
    contra_display_style="negative_sign",  # Override default
    apply_contra_formatting=True
)
```

#### Per-Formatter Default

```python
# Set default in formatter
formatter.default_formats["contra_display_style"] = "brackets"
```

## API Usage

### Basic Usage

```python
from fin_statement_model.statements import create_statement_dataframe

# Standard usage - contra items automatically formatted
df = create_statement_dataframe(
    graph=my_graph,
    config_path="statements/balance_sheet.yaml"
)
```

### Advanced Configuration

```python
from fin_statement_model.statements import StatementFormatter

formatter = StatementFormatter(statement)

df = formatter.generate_dataframe(
    graph=graph,
    # Contra formatting options
    apply_contra_formatting=True,              # Enable contra formatting
    contra_display_style="parentheses",       # Set display style
    add_contra_indicator_column=True,          # Add is_contra column
    include_css_classes=True,                  # Include CSS styling
)
```

### HTML Output with Contra Styling

```python
html = formatter.format_html(
    graph=graph,
    apply_contra_formatting=True,
    css_styles={
        '.contra-item': 'font-style: italic; color: #666;',
        '.asset-contra': 'background-color: #f0f8f0;',
        '.equity-contra': 'background-color: #f8f0f0;',
    }
)
```

## Common Contra Items

### Asset Contra Items

```yaml
# Accumulated Depreciation
- id: accumulated_depreciation
  name: Less: Accumulated Depreciation
  type: line_item
  node_id: accumulated_depreciation
  sign_convention: -1
  is_contra: true
  css_class: "asset-contra"

# Allowance for Doubtful Accounts
- id: allowance_doubtful_accounts
  name: Less: Allowance for Doubtful Accounts
  type: line_item
  node_id: allowance_doubtful_accounts
  sign_convention: -1
  is_contra: true
  css_class: "asset-contra"
```

### Revenue Contra Items

```yaml
# Sales Returns and Allowances
- id: sales_returns
  name: Less: Sales Returns & Allowances
  type: line_item
  node_id: sales_returns_allowances
  sign_convention: -1
  is_contra: true
  css_class: "revenue-contra"

# Sales Discounts
- id: sales_discounts
  name: Less: Sales Discounts
  type: line_item
  node_id: sales_discounts
  sign_convention: -1
  is_contra: true
  css_class: "revenue-contra"
```

### Equity Contra Items

```yaml
# Treasury Stock
- id: treasury_stock
  name: Less: Treasury Stock
  type: line_item
  node_id: treasury_stock
  sign_convention: -1
  is_contra: true
  css_class: "equity-contra"
  display_format: ",.0f"  # No decimals for share values
```

## Advanced Examples

### Balance Sheet with Asset Contra

```yaml
sections:
  - id: assets
    name: Assets
    items:
      - id: gross_ppe
        name: Property, Plant & Equipment
        type: line_item
        node_id: gross_ppe
        sign_convention: 1
        
      - id: accumulated_depreciation
        name: Less: Accumulated Depreciation
        type: line_item
        node_id: accumulated_depreciation
        sign_convention: -1
        is_contra: true
        
      - id: net_ppe
        name: Net Property, Plant & Equipment
        type: calculated
        calculation:
          type: addition
          inputs: [gross_ppe, accumulated_depreciation]
        sign_convention: 1
```

**Output Example:**
```
Property, Plant & Equipment        1,000,000
Less: Accumulated Depreciation      (250,000)
Net Property, Plant & Equipment      750,000
```

### Income Statement with Revenue Contra

```yaml
sections:
  - id: revenue
    name: Revenue
    items:
      - id: gross_sales
        name: Gross Sales
        type: line_item
        node_id: gross_sales
        sign_convention: 1
        
      - id: returns_allowances
        name: Less: Returns & Allowances
        type: line_item
        node_id: sales_returns_allowances
        sign_convention: -1
        is_contra: true
        css_class: "revenue-contra"
        
    subtotal:
      id: net_sales
      name: Net Sales
      type: subtotal
      items_to_sum: [gross_sales, returns_allowances]
```

**Output Example:**
```
Gross Sales                      1,200,000
Less: Returns & Allowances          (50,000)
Net Sales                        1,150,000
```

## CSS Styling

### Default Classes

The system automatically applies CSS classes:

- `.contra-item`: Applied to all contra items
- Custom classes from item configuration

### Default Styling

```css
.contra-item { 
    font-style: italic; 
    color: #666; 
}
```

### Custom Styling Examples

```css
/* Asset contra items */
.asset-contra {
    background-color: #f0f8f0;
    border-left: 3px solid #4CAF50;
}

/* Revenue contra items */
.revenue-contra {
    background-color: #fff8f0;
    border-left: 3px solid #FF9800;
}

/* Equity contra items */
.equity-contra {
    background-color: #f8f0f0;
    border-left: 3px solid #F44336;
}
```

## Migration Guide

### From Manual Formatting

```yaml
# Before: Manual formatting in item names
- id: accumulated_depreciation
  name: "  Less: Accumulated Depreciation"  # Manual indentation/formatting
  type: line_item
  node_id: accumulated_depreciation
  sign_convention: -1

# After: Declarative contra designation
- id: accumulated_depreciation
  name: "Less: Accumulated Depreciation"
  type: line_item
  node_id: accumulated_depreciation
  sign_convention: -1
  is_contra: true  # Automatic formatting
```

### From Code-Based Logic

```python
# Before: Manual formatting in code
def format_value(item_id, value):
    if item_id in ['treasury_stock', 'accumulated_depreciation']:
        return f"({abs(value):,.2f})"
    return f"{value:,.2f}"

# After: Configuration-driven
# Add is_contra: true to relevant items in YAML
```

## Best Practices

### 1. Consistent Naming
Use clear naming conventions that indicate contra nature:
- "Less: [Item Name]"
- "[Item Name] (Contra)"
- "Allowance for [Item Name]"

### 2. Appropriate Sign Conventions
Always set `sign_convention: -1` for contra items to ensure proper calculations.

### 3. Meaningful CSS Classes
Use descriptive CSS classes that group related contra items:
- `asset-contra`
- `revenue-contra`
- `equity-contra`

### 4. Consistent Display Formatting
Choose one display style per statement type for consistency.

### 5. Documentation
Document contra items clearly in configuration comments:

```yaml
- id: treasury_stock
  name: Less: Treasury Stock
  # Contra-equity item: reduces shareholders' equity
  type: line_item
  node_id: treasury_stock
  sign_convention: -1  # Calculation: subtracts from equity
  is_contra: true      # Display: show in parentheses
```

## Troubleshooting

### Common Issues

1. **Values Not Displaying as Contra**
   - Check `is_contra: true` is set
   - Verify `apply_contra_formatting: true` in formatter options

2. **Calculations Incorrect**
   - Ensure `sign_convention: -1` for items that should subtract
   - Verify contra items are included in subtotal `items_to_sum`

3. **CSS Styling Not Applied**
   - Check `include_css_classes: True` in formatter options
   - Verify CSS class names in configuration

4. **Mixed Display Styles**
   - Set consistent `contra_display_style` across statements
   - Check for conflicting `display_format` specifications

### Validation

The system validates:
- `is_contra` is boolean
- CSS class names are strings
- Display styles are recognized values

This contra items feature provides a powerful way to create intuitive, accounting-standard financial statements while maintaining computational accuracy and flexibility. 