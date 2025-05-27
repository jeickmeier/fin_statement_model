# Core Metrics Summary

## Metrics Count by Category

| Category | Count | Description |
|----------|-------|-------------|
| **Common Base Nodes** | 74 | Fundamental data nodes required across all metrics |
| **Liquidity Metrics** | 8 | Short-term solvency and working capital efficiency |
| **Leverage/Solvency** | 8 | Capital structure and long-term solvency |
| **Coverage Metrics** | 8 | Ability to service debt and fixed charges |
| **Profitability** | 9 | Margin and return metrics |
| **Efficiency** | 7 | Asset utilization and turnover |
| **Valuation** | 10 | Market-based valuation multiples |
| **Cash Flow** | 7 | Cash generation and quality |
| **Credit Risk** | 7 | Bankruptcy and manipulation detection |
| **DuPont Analysis** | 2 | ROE decomposition models |
| **Growth Metrics** | 5 | Period-over-period growth rates |
| **Per Share** | 5 | Per share calculations |
| **TOTAL METRICS** | **96** | Comprehensive coverage for credit and equity analysis |

## Key Node Dependencies

### Most Used Base Nodes
1. **revenue** - Used in 25+ metrics
2. **total_assets** - Used in 20+ metrics
3. **total_equity** - Used in 15+ metrics
4. **net_income** - Used in 15+ metrics
5. **ebitda** - Used in 12+ metrics
6. **operating_cash_flow** - Used in 10+ metrics
7. **total_debt** - Used in 10+ metrics
8. **current_assets/liabilities** - Used in 8+ metrics

### Critical Calculated Nodes
- **ebitda** = operating_income + depreciation_and_amortization
- **net_debt** = total_debt - cash_and_equivalents
- **working_capital** = current_assets - current_liabilities
- **free_cash_flow** = operating_cash_flow + capital_expenditures
- **enterprise_value** = market_cap + net_debt + minority_interest

### Nodes Requiring Special Handling
1. **Balance Sheet Averages**: Many efficiency and return metrics require average balance sheet values
2. **Market Data**: Valuation metrics require real-time or point-in-time market prices
3. **Prior Period Values**: Growth metrics need access to historical data
4. **Industry-Specific**: Some nodes may need industry-specific definitions (e.g., same-store sales for retail)

## Implementation Complexity

### Simple Metrics (Direct Formula)
- Basic ratios with 2-3 inputs
- Examples: Current Ratio, Debt-to-Equity, Gross Margin
- **Count: ~60 metrics**

### Moderate Complexity
- Multi-step calculations or special node requirements
- Examples: Cash Conversion Cycle, ROIC, Free Cash Flow metrics
- **Count: ~25 metrics**

### Complex Metrics
- Require multiple calculated inputs or sophisticated logic
- Examples: Altman Z-Score variants, Beneish M-Score, DuPont 5-step
- **Count: ~11 metrics**

## Node Standardization Requirements

### Naming Conventions
- Use lowercase with underscores
- Be explicit (e.g., `operating_cash_flow` not just `cfo`)
- Distinguish between gross/net values clearly
- Use consistent terminology across statements

### Sign Conventions
- **Positive**: Revenue, profits, assets, equity
- **Negative**: Expenses (when stored as negative), dividends paid, capex, debt repayments
- **Context-dependent**: Working capital changes

### Missing Data Strategies
1. **Zero Default**: For non-critical additions (e.g., other income)
2. **Calculation Skip**: For ratios with missing critical inputs
3. **Proxy Calculation**: Alternative formulas when preferred data unavailable
4. **Industry Defaults**: Use industry medians for missing non-critical data

## Cross-Metric Dependencies

### Metric Families
1. **Liquidity Family**: Current → Quick → Cash ratios (increasing conservatism)
2. **Leverage Family**: Gross Debt → Net Debt → Coverage ratios
3. **Profitability Family**: Gross → Operating → EBITDA → Net margins
4. **Return Family**: ROA → ROE → ROIC (different capital bases)
5. **Cash Flow Family**: OCF → FCF → Quality of earnings

### Validation Relationships
- ROE (DuPont) should equal ROE (direct calculation)
- Sum of per-share metrics × shares should equal totals
- Cash flow statement should reconcile with balance sheet changes

## Next Steps

1. **Create Base Node Definitions**: Start with the 74 common nodes
2. **Implement Phase 1 Metrics**: ~20 core metrics for basic analysis
3. **Add Calculation Nodes**: For computed values like EBITDA, net debt
4. **Build Metric Registry**: YAML definitions for each metric
5. **Test with Real Data**: Validate calculations against known examples
6. **Add Industry Adjustments**: Sector-specific modifications as needed 