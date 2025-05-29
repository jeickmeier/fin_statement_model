# Real Estate Metrics and Nodes Addition

This document summarizes the real estate-specific metrics and nodes that have been added to the financial statement model library.

## Overview

The library now includes comprehensive support for real estate investment trust (REIT) analysis and property-level financial modeling through:

- **16 real estate-specific metrics** organized into operational, valuation, and per-share categories
- **34 real estate-specific nodes** covering property operations and REIT-specific items
- **Comprehensive test coverage** ensuring all metrics work correctly
- **Example usage** demonstrating real-world REIT analysis

## Real Estate Metrics Added

### Operational Metrics (`real_estate/operational_metrics.yaml`)
1. **Net Operating Income** - Property income after operating expenses
2. **Funds From Operations (FFO)** - REIT earnings metric adding back depreciation
3. **Adjusted Funds From Operations (AFFO)** - FFO adjusted for recurring capex
4. **Occupancy Rate** - Percentage of rentable space occupied
5. **Same Store NOI Growth** - Organic growth excluding acquisitions

### Valuation Metrics (`real_estate/valuation_metrics.yaml`)
1. **Capitalization Rate** - NOI as percentage of property value
2. **Price Per Square Foot** - Property value per square foot
3. **Rent Per Square Foot** - Annual rental income per square foot
4. **FFO Multiple** - Market cap divided by FFO (REIT P/E equivalent)
5. **AFFO Multiple** - Market cap divided by AFFO
6. **NAV Per Share** - Net asset value per share
7. **Price to NAV Ratio** - Market premium/discount to asset value

### Per Share Metrics (`real_estate/per_share_metrics.yaml`)
1. **FFO Per Share** - FFO divided by shares outstanding
2. **AFFO Per Share** - AFFO divided by shares outstanding
3. **Dividend Coverage Ratio (AFFO)** - AFFO coverage of dividends
4. **Property Revenue Per Share** - Property revenue per share

## Real Estate Nodes Added

### Property Operations (`real_estate/property_operations.yaml`)
**Income Items:**
- `rental_income` - Total rental income from properties
- `other_property_income` - Non-rental income (parking, fees, etc.)
- `total_property_revenue` - Total property revenue

**Expense Items:**
- `property_operating_expenses` - Total property operating expenses
- `property_management_fees` - Management and leasing fees
- `property_taxes` - Real estate taxes
- `utilities` - Utilities expenses
- `maintenance_and_repairs` - Property maintenance costs
- `insurance` - Property insurance expenses

**Property Metrics:**
- `occupied_square_feet` - Total occupied square footage
- `total_rentable_square_feet` - Total rentable square footage
- `total_square_feet` - Total building square footage
- `number_of_units` - Total rental units
- `occupied_units` - Number of occupied units

**Valuation:**
- `property_value` - Estimated property value
- `total_property_value` - Total portfolio value

### REIT-Specific Items (`real_estate/reit_specific.yaml`)
**Core REIT Metrics:**
- `funds_from_operations` - FFO calculation
- `adjusted_funds_from_operations` - AFFO calculation
- `gains_on_property_sales` - Property disposition gains
- `recurring_capital_expenditures` - Maintenance capex

**Accounting Adjustments:**
- `straight_line_rent_adjustments` - Rent accounting adjustments
- `stock_compensation_expense` - Stock-based compensation

**Development & Leasing:**
- `acquisition_costs` - Property acquisition costs
- `development_costs` - Development and redevelopment costs
- `tenant_improvements` - Tenant improvement capex
- `leasing_commissions` - Leasing activity commissions

**Same Store Analysis:**
- `same_store_noi_current` - Current period same-store NOI
- `same_store_noi_prior` - Prior period same-store NOI

**Per Share Items:**
- `ffo_per_share` - FFO per share
- `affo_per_share` - AFFO per share
- `nav_per_share` - Net asset value per share

## Integration with Existing System

### Metrics Loading
Real estate metrics are automatically loaded with the existing metric system:
```python
from fin_statement_model.core.metrics import metric_registry

# All real estate metrics are automatically available
real_estate_metrics = [m for m in metric_registry.list_metrics() 
                      if 'real_estate' in metric_registry.get(m).category]
```

### Nodes Loading
Real estate nodes are automatically loaded with the standard node registry:
```python
from fin_statement_model.core.nodes import standard_node_registry

# Access real estate nodes by category
property_nodes = standard_node_registry.list_standard_names('real_estate_operations')
reit_nodes = standard_node_registry.list_standard_names('real_estate_reit')
```

## Usage Example

The library includes a comprehensive example (`examples/real_estate_analysis_example.py`) demonstrating:

1. **Creating REIT financial data** using standard nodes
2. **Calculating key metrics** like NOI, FFO, occupancy rate, cap rate
3. **Interpreting results** using built-in interpretation guidelines
4. **Growth analysis** comparing periods

Sample output:
```
=== REIT Analysis Example ===

Key REIT Metrics for 2023:
----------------------------------------
Net Operating Income: $70,000,000
Funds From Operations: $77,500,000
Occupancy Rate: 94.2%
  → Good performance: 94.23
Capitalization Rate: 3.33
FFO Per Share: $0.75
FFO Multiple: 40.0x
  → Warning level: 40.00

Growth Analysis:
----------------------------------------
NOI Growth (2022-2023): 6.9%
FFO Growth (2022-2023): 9.2%
```

## Testing

Comprehensive test coverage includes:
- **Metric loading verification** - Ensures all real estate metrics load correctly
- **Calculation accuracy** - Tests key metric calculations (NOI, FFO, occupancy, cap rate, etc.)
- **Interpretation guidelines** - Verifies metrics have proper interpretation thresholds
- **Integration testing** - Confirms metrics work with the existing node system

## File Structure

```
fin_statement_model/
├── core/
│   ├── metrics/
│   │   └── metric_defn/
│   │       └── real_estate/
│   │           ├── __init__.py
│   │           ├── operational_metrics.yaml
│   │           ├── valuation_metrics.yaml
│   │           └── per_share_metrics.yaml
│   └── nodes/
│       └── standard_nodes/
│           └── real_estate/
│               ├── __init__.py
│               ├── property_operations.yaml
│               └── reit_specific.yaml
├── examples/
│   └── real_estate_analysis_example.py
└── tests/
    └── core/
        └── metrics/
            └── test_real_estate_metrics.py
```

## Benefits

1. **Industry-Specific Analysis** - Enables proper REIT and real estate analysis
2. **Professional Standards** - Follows NAREIT standards for FFO/AFFO calculations
3. **Comprehensive Coverage** - Includes operational, valuation, and per-share metrics
4. **Easy Integration** - Works seamlessly with existing library architecture
5. **Extensible Design** - Easy to add more real estate metrics as needed

## Future Enhancements

Potential areas for expansion:
- Property type-specific metrics (office, retail, multifamily, industrial)
- Geographic/market-specific adjustments
- ESG (Environmental, Social, Governance) metrics for real estate
- Development and construction-specific metrics
- International real estate standards (EPRA, etc.)

This addition significantly enhances the library's capability for real estate investment analysis while maintaining the existing architecture and coding standards. 