# Financial Metrics Organization

This directory contains the organized financial metric definitions for the financial statement model library. The metrics are split into logical categories for easier maintenance and understanding.

## Directory Structure

```
metrics/
├── README.md                    # This file
├── __init__.py                  # Main exports and registry loading
├── models.py                    # Pydantic models for metric definitions
├── registry.py                  # Metric registry and loading logic
├── interpretation.py            # Metric interpretation and rating system
├── builtin_organized/           # Built-in metrics organized by category
│   ├── README.md               # Built-in metrics documentation
│   ├── __init__.py             # Built-in metrics loading
│   ├── liquidity/              # Liquidity and working capital metrics
│   │   ├── __init__.py
│   │   ├── ratios.yaml         # Current, quick, cash ratios
│   │   └── working_capital.yaml # DSO, DIO, DPO, cash conversion cycle
│   ├── leverage/               # Leverage and solvency metrics
│   │   ├── __init__.py
│   │   ├── debt_ratios.yaml    # Debt-to-equity, debt-to-assets, etc.
│   │   └── net_leverage.yaml   # Net debt ratios and EBITDA multiples
│   ├── coverage/               # Coverage and debt service metrics
│   │   ├── __init__.py
│   │   ├── interest_coverage.yaml # Interest coverage ratios
│   │   └── debt_service.yaml   # DSCR, cash flow coverage
│   ├── profitability/          # Profitability and margin metrics
│   │   ├── __init__.py
│   │   ├── margins.yaml        # Gross, operating, net margins
│   │   └── returns.yaml        # ROA, ROE, ROIC, ROCE
│   ├── efficiency/             # Efficiency and turnover metrics
│   │   ├── __init__.py
│   │   ├── asset_turnover.yaml # Asset, fixed asset, working capital turnover
│   │   └── component_turnover.yaml # Inventory, receivables, payables turnover
│   ├── valuation/              # Valuation multiples and yields
│   │   ├── __init__.py
│   │   ├── price_multiples.yaml # P/E, P/B, P/S ratios
│   │   ├── enterprise_multiples.yaml # EV/EBITDA, EV/Sales, EV/EBIT
│   │   └── yields.yaml         # Dividend yield, earnings yield, FCF yield
│   ├── cash_flow/              # Cash flow metrics
│   │   ├── __init__.py
│   │   ├── generation.yaml     # OCF margin, FCF margin, quality of earnings
│   │   └── returns.yaml        # Cash flow ROA, ROE, capex coverage
│   ├── growth/                 # Growth metrics
│   │   ├── __init__.py
│   │   └── growth_rates.yaml   # Revenue, EBITDA, EPS, asset growth
│   ├── per_share/              # Per share metrics
│   │   ├── __init__.py
│   │   └── per_share_metrics.yaml # Revenue, cash, FCF, book value per share
│   ├── credit_risk/            # Credit risk and distress models
│   │   ├── __init__.py
│   │   ├── altman_scores.yaml  # Altman Z-Score variants
│   │   └── warning_flags.yaml  # Binary warning indicators
│   ├── advanced/               # Advanced analysis tools
│   │   ├── __init__.py
│   │   └── dupont_analysis.yaml # DuPont ROE decomposition
│   ├── special/                # Special calculated metrics
│   │   ├── __init__.py
│   │   ├── gross_profit.yaml   # Gross profit calculation
│   │   ├── net_income.yaml     # Net income calculation
│   │   └── retained_earnings.yaml # Retained earnings calculation
│   └── real_estate/            # Real estate and REIT metrics
│       ├── __init__.py
│       ├── operational_metrics.yaml # NOI, FFO, AFFO, occupancy
│       ├── valuation_metrics.yaml # Cap rates, price per SF, REIT multiples
│       └── per_share_metrics.yaml # FFO/share, AFFO/share, NAV/share
└── industry_extensions/        # Industry-specific metrics (future)
    ├── banking/
    ├── real_estate/
    └── insurance/
```

## Benefits of This Organization

1. **Logical Grouping**: Related metrics are grouped together by analytical purpose
2. **Easier Maintenance**: Smaller files are easier to edit and review
3. **Clear Ownership**: Each file has a specific analytical focus
4. **Scalability**: Easy to add new categories or industry-specific metrics
5. **Better Documentation**: Each category can have specific documentation
6. **Faster Loading**: Can load specific categories as needed

## Loading Metrics

The registry automatically loads all metric definitions from these organized files:

```python
from fin_statement_model.core.metrics import metric_registry

# All metrics are automatically loaded
print(f"Loaded {len(metric_registry)} metrics")

# Access by category
liquidity_metrics = [m for m in metric_registry.list_metrics() 
                    if metric_registry.get(m).category == "liquidity"]
```

## Metric Categories

### Core Analysis Categories
- **Liquidity (8 metrics)**: Short-term solvency and working capital efficiency
- **Leverage (8 metrics)**: Capital structure and long-term solvency  
- **Coverage (7 metrics)**: Ability to service debt and fixed charges
- **Profitability (11 metrics)**: Margin and return metrics
- **Efficiency (12 metrics)**: Asset utilization and turnover ratios

### Market and Valuation
- **Valuation (10 metrics)**: Market-based valuation multiples and yields
- **Cash Flow (7 metrics)**: Cash generation and quality metrics
- **Per Share (4 metrics)**: Per share calculations

### Advanced Analysis
- **Growth (5 metrics)**: Period-over-period growth rates
- **Credit Risk (5 metrics)**: Bankruptcy prediction and warning flags
- **Advanced (2 metrics)**: DuPont analysis and sophisticated tools

### Industry-Specific
- **Real Estate (12 metrics)**: REIT and property-specific metrics including NOI, FFO, AFFO, cap rates, and occupancy metrics

## Adding New Metrics

To add new metrics:

1. Choose the appropriate category directory
2. Add the metric definition to the relevant YAML file
3. Follow the existing pattern for metric definitions
4. Include comprehensive interpretation guidelines
5. Update tests if needed

## Industry-Specific Extensions

For industry-specific metrics, create new directories under `industry_extensions/`:

```
industry_extensions/
├── banking/
│   ├── asset_quality.yaml     # NPL ratios, charge-offs
│   ├── capital_adequacy.yaml  # Tier 1 capital, risk-weighted assets
│   └── profitability.yaml     # Net interest margin, efficiency ratio
├── real_estate/
│   ├── operations.yaml        # NOI, FFO, AFFO metrics
│   └── valuation.yaml         # Cap rates, price per square foot
└── insurance/
    ├── underwriting.yaml      # Combined ratio, loss ratio
    └── investment.yaml        # Investment yield, duration matching
```

These can be loaded optionally based on industry context.

## Metric Quality Standards

All metrics must include:
- Clear description and purpose
- Comprehensive interpretation guidelines with thresholds
- Industry context and usage notes
- Related metrics for cross-analysis
- Proper categorization and tagging

## Usage Examples

### Basic Analysis
```python
# Load specific category
liquidity_analysis = [
    "current_ratio", "quick_ratio", "cash_ratio", 
    "operating_cash_flow_ratio", "cash_conversion_cycle"
]

# Calculate and interpret
for metric_name in liquidity_analysis:
    value = graph.calculate_metric(metric_name)
    interpretation = interpret_metric(metric_registry.get(metric_name), value)
    print(f"{metric_name}: {interpretation['interpretation_message']}")
```

### Real Estate Analysis
```python
# REIT analysis dashboard
reit_metrics = {
    "operational": ["net_operating_income", "funds_from_operations", "adjusted_funds_from_operations"],
    "valuation": ["capitalization_rate", "ffo_multiple", "affo_multiple", "price_to_nav_ratio"],
    "per_share": ["ffo_per_share", "affo_per_share", "dividend_coverage_ratio_affo"],
    "efficiency": ["occupancy_rate", "same_store_noi_growth"]
}

# Generate REIT assessment
reit_assessment = analyze_reit_metrics(graph, reit_metrics)
```

### Credit Analysis Dashboard
```python
# Comprehensive credit assessment
credit_metrics = {
    "liquidity": ["current_ratio", "quick_ratio", "operating_cash_flow_ratio"],
    "leverage": ["debt_to_equity_ratio", "net_debt_to_ebitda", "financial_leverage_ratio"],
    "coverage": ["times_interest_earned", "ebitda_interest_coverage", "debt_service_coverage_ratio"],
    "profitability": ["operating_profit_margin", "return_on_assets", "return_on_equity"],
    "credit_risk": ["altman_z_score_manufacturing", "interest_coverage_flag"]
}

# Generate comprehensive assessment
credit_assessment = analyze_credit_metrics(graph, credit_metrics)
```

This organized structure provides a solid foundation for comprehensive financial analysis while maintaining the flexibility needed for diverse analytical requirements. 