# Standard Nodes Organization

This directory contains the organized standard node definitions for the financial statement model library. The nodes are split into logical categories for easier maintenance and understanding.

## Directory Structure

```
standard_nodes/
├── README.md                    # This file
├── __init__.py                  # Exports and registry loading
├── balance_sheet/
│   ├── __init__.py
│   ├── assets.yaml             # Current and non-current assets
│   ├── liabilities.yaml        # Current and non-current liabilities
│   └── equity.yaml             # Equity components
├── income_statement/
│   ├── __init__.py
│   ├── revenue_costs.yaml      # Revenue and direct costs
│   ├── operating.yaml          # Operating expenses and income
│   ├── non_operating.yaml     # Interest, other income, taxes
│   └── shares.yaml             # Share-related items
├── cash_flow/
│   ├── __init__.py
│   ├── operating.yaml          # Operating activities
│   ├── investing.yaml          # Investing activities
│   └── financing.yaml          # Financing activities
├── calculated/
│   ├── __init__.py
│   ├── profitability.yaml      # EBITDA, NOPAT, etc.
│   ├── liquidity.yaml          # Working capital measures
│   ├── leverage.yaml           # Net debt, leverage measures
│   └── valuation.yaml          # Enterprise value, etc.
├── market_data/
│   ├── __init__.py
│   └── market_data.yaml        # Market prices and per-share data
└── real_estate/
    ├── __init__.py
    ├── property_operations.yaml # Property income, expenses, metrics
    └── reit_specific.yaml       # FFO, AFFO, REIT-specific items
```

## Benefits of This Organization

1. **Logical Grouping**: Related nodes are grouped together
2. **Easier Maintenance**: Smaller files are easier to edit and review
3. **Clear Ownership**: Each file has a specific purpose
4. **Scalability**: Easy to add new categories or industry-specific nodes
5. **Better Documentation**: Each category can have specific documentation

## Loading Standard Nodes

The registry automatically loads all node definitions from these files:

```python
from fin_statement_model.core.nodes import standard_node_registry

# All nodes are automatically loaded
print(f"Loaded {len(standard_node_registry)} standard nodes")

# Access by category
balance_sheet_assets = standard_node_registry.list_standard_names("balance_sheet_assets")
real_estate_nodes = standard_node_registry.list_standard_names("real_estate_operations")
```

## Adding New Nodes

To add new standard nodes:

1. Choose the appropriate category file
2. Add the node definition following the existing pattern
3. Include alternate names and proper categorization
4. Update tests if needed

## Industry-Specific Extensions

For industry-specific nodes, create new directories:

```
standard_nodes/
├── industries/
│   ├── banking/
│   │   ├── assets.yaml         # Loans, securities, etc.
│   │   └── liabilities.yaml    # Deposits, regulatory capital
│   ├── real_estate/
│   │   └── operations.yaml     # NOI, FFO, AFFO, etc.
│   └── insurance/
│       └── operations.yaml     # Premiums, claims, reserves
```

These can be loaded optionally based on industry context. 