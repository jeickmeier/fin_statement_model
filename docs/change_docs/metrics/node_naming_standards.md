# Node Naming Standards

## General Principles

1. **Use lowercase with underscores**: `total_assets` not `TotalAssets` or `total-assets`
2. **Be explicit and descriptive**: `operating_cash_flow` not `ocf` or `cash_flow_ops`
3. **Use full words**: `depreciation_and_amortization` not `d_and_a`
4. **Be consistent across statements**: If using `revenue` on IS, don't use `sales` elsewhere
5. **Include qualifiers**: `gross_profit`, `operating_income`, `net_income` (not just `profit` or `income`)

## Balance Sheet Naming

### Assets
```
# Current Assets
cash_and_equivalents          # Not: cash, c_and_e
short_term_investments        # Not: st_investments, marketable_securities
accounts_receivable           # Not: ar, receivables, trade_receivables
inventory                     # Not: inventories, inv
prepaid_expenses             # Not: prepaids
current_assets               # Not: ca, current_assets_total

# Non-Current Assets  
property_plant_equipment     # Not: ppe, fixed_assets, pp_and_e
accumulated_depreciation     # Not: acc_dep, accum_depr
intangible_assets           # Not: intangibles
goodwill                    # Separate from other intangibles when possible
long_term_investments       # Not: lt_investments
deferred_tax_assets         # Not: dta
total_assets               # Not: ta, assets
```

### Liabilities
```
# Current Liabilities
accounts_payable            # Not: ap, payables
accrued_expenses           # Not: accruals, accrued_liabilities  
short_term_debt            # Not: st_debt, current_debt
current_portion_long_term_debt  # Not: cpltd
current_liabilities        # Not: cl, current_liabilities_total

# Non-Current Liabilities
long_term_debt             # Not: lt_debt, ltb
deferred_tax_liabilities   # Not: dtl
pension_liabilities        # Not: pension_obligations
total_liabilities          # Not: tl, liabilities
```

### Equity
```
common_stock               # Not: cs, common_shares
preferred_stock            # Not: pref_stock, ps
additional_paid_in_capital # Not: apic, capital_surplus
retained_earnings          # Not: re
treasury_stock            # Not: ts (note: store as negative)
accumulated_other_comprehensive_income  # Not: aoci
total_equity              # Not: te, shareholders_equity, stockholders_equity
minority_interest         # Not: nci, non_controlling_interest
```

## Income Statement Naming

```
# Revenue & COGS
revenue                    # Not: sales, total_revenue, revenues
cost_of_goods_sold        # Not: cogs, cost_of_sales, cos
gross_profit              # Not: gp, gross_margin_dollars

# Operating Expenses
operating_expenses        # Not: opex, operating_costs
selling_general_admin     # Not: sg_and_a, sga  
research_development      # Not: r_and_d, rd, research_and_development
depreciation_amortization # Not: d_and_a, da, dep_amort

# Operating Income
operating_income          # Not: ebit, operating_profit, oi

# Non-Operating
interest_expense          # Not: int_expense, interest_exp
interest_income           # Not: int_income
other_income             # Not: other_income_expense
income_before_tax        # Not: ebt, pretax_income, pbt
income_tax_expense       # Not: taxes, tax_expense, income_taxes
net_income               # Not: ni, net_profit, earnings

# Per Share
earnings_per_share        # Not: eps
diluted_earnings_per_share # Not: deps, diluted_eps
dividends_per_share       # Not: dps
shares_outstanding        # Not: shares, common_shares_outstanding
diluted_shares_outstanding # Not: diluted_shares
```

## Cash Flow Statement Naming

```
# Operating Activities
cash_from_operations      # Start with net_income
depreciation_amortization # Add back non-cash
change_in_working_capital # Not: wc_change, working_capital_changes
change_in_receivables     # Not: ar_change
change_in_inventory       # Not: inv_change  
change_in_payables        # Not: ap_change
operating_cash_flow       # Not: cfo, ocf, cffo

# Investing Activities
capital_expenditures      # Not: capex, ppe_purchases (store as negative)
acquisitions             # Not: m_and_a, business_acquisitions
asset_sales              # Not: ppe_sales, asset_disposals
investing_cash_flow      # Not: cfi, cffi

# Financing Activities
debt_issuance            # Not: debt_proceeds, new_debt
debt_repayment           # Not: debt_payments (store as negative)
equity_issuance          # Not: stock_issuance, equity_proceeds
share_repurchases        # Not: buybacks, stock_repurchases (store as negative)
dividends_paid           # Not: dividends, div_paid (store as negative)
financing_cash_flow      # Not: cff, cfff
```

## Calculated/Derived Nodes

```
# Earnings Metrics
ebitda                   # operating_income + depreciation_amortization
ebit                     # Same as operating_income in most cases
nopat                    # Net operating profit after tax
noplat                   # Net operating profit less adjusted taxes

# Balance Sheet Metrics
working_capital          # current_assets - current_liabilities
net_working_capital      # (current_assets - cash) - (current_liabilities - short_term_debt)
net_debt                 # total_debt - cash_and_equivalents
total_debt               # short_term_debt + long_term_debt
net_assets               # total_assets - total_liabilities
tangible_assets          # total_assets - intangible_assets
tangible_book_value      # total_equity - intangible_assets

# Cash Flow Metrics
free_cash_flow           # operating_cash_flow + capital_expenditures
unlevered_free_cash_flow # For DCF models
levered_free_cash_flow   # After debt service

# Valuation Metrics
enterprise_value         # market_cap + net_debt + minority_interest - cash
market_cap               # market_price * shares_outstanding
book_value_per_share     # total_equity / shares_outstanding
```

## Industry-Specific Considerations

### Banking/Financial Services
```
net_interest_income      # Not: nii
provision_for_loan_losses # Not: pll, loan_loss_provision
tier_1_capital           # Not: t1_capital
risk_weighted_assets     # Not: rwa
```

### Real Estate
```
funds_from_operations    # Not: ffo
adjusted_funds_from_operations # Not: affo
net_operating_income     # Not: noi (different from operating_income)
```

### Retail
```
same_store_sales         # Not: sss, comp_sales
gross_merchandise_value  # Not: gmv
```

## Node Type Prefixes (Optional)

For clarity in large models, consider prefixes:
```
calc_ebitda              # Calculated node
input_revenue            # Direct input node
forecast_revenue         # Forecast node
avg_total_assets         # Average/time-weighted node
```

## Handling Multiple Periods

```
# For period-specific references
revenue_2023             # Specific year
revenue_q1_2023          # Specific quarter
revenue_ltm              # Last twelve months
revenue_ttm              # Trailing twelve months
revenue_projected        # Forward-looking

# For growth/change calculations
revenue_growth_yoy       # Year-over-year
revenue_growth_qoq       # Quarter-over-quarter
revenue_cagr_5y          # 5-year CAGR
```

## Common Abbreviations to Avoid

❌ **Don't use**:
- `ta` → Use `total_assets`
- `tl` → Use `total_liabilities`
- `te` → Use `total_equity`
- `ni` → Use `net_income`
- `cfo` → Use `operating_cash_flow`
- `fcf` → Use `free_cash_flow`
- `ppe` → Use `property_plant_equipment`
- `ar` → Use `accounts_receivable`
- `ap` → Use `accounts_payable`
- `sga` → Use `selling_general_admin`

## Validation Rules

1. **No spaces**: Use underscores
2. **No special characters**: Except underscores
3. **No mixed case**: All lowercase
4. **No numbers at start**: `3m_revenue` → `revenue_3m`
5. **Meaningful names**: Should be self-documenting

## Example Metric Implementation

```yaml
# Good naming example
name: "Return on Assets"
description: "Net income divided by total assets"
inputs:
  - net_income        # Clear, standard name
  - total_assets      # Clear, standard name
formula: "net_income / total_assets"

# Bad naming example - DO NOT USE
name: "ROA"
inputs:
  - ni   # Unclear abbreviation
  - ta   # Unclear abbreviation
formula: "ni / ta"
``` 