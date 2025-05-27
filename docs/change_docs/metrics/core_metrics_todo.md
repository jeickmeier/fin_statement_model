# Core Financial Metrics TODO List

## Common Base Nodes Required

These are the fundamental nodes that should be standardized across all metrics:

### Balance Sheet Items
- [x] `cash_and_equivalents` - Cash and cash equivalents
- [x] `short_term_investments` - Short-term marketable securities
- [x] `accounts_receivable` - Trade receivables
- [x] `inventory` - Total inventory
- [x] `prepaid_expenses` - Prepaid expenses and other current assets
- [x] `current_assets` - Total current assets
- [x] `property_plant_equipment` - Net PP&E
- [x] `intangible_assets` - Intangible assets including goodwill
- [x] `long_term_investments` - Long-term investments
- [x] `total_assets` - Total assets
- [x] `accounts_payable` - Trade payables
- [x] `accrued_expenses` - Accrued expenses
- [x] `short_term_debt` - Short-term debt and current portion of long-term debt
- [x] `current_liabilities` - Total current liabilities
- [x] `long_term_debt` - Long-term debt excluding current portion
- [x] `total_debt` - Total debt (short_term_debt + long_term_debt)
- [x] `total_liabilities` - Total liabilities
- [x] `common_stock` - Common stock
- [x] `retained_earnings` - Retained earnings
- [x] `treasury_stock` - Treasury stock (negative value)
- [x] `total_equity` - Total shareholders' equity
- [x] `minority_interest` - Non-controlling interests

### Income Statement Items
- [x] `revenue` - Total revenue/sales
- [x] `cost_of_goods_sold` - Cost of goods sold
- [x] `gross_profit` - Gross profit
- [x] `operating_expenses` - Total operating expenses
- [x] `sg_and_a` - Selling, general & administrative expenses
- [x] `r_and_d` - Research & development expenses
- [x] `depreciation_and_amortization` - D&A expense
- [x] `operating_income` - Operating income/EBIT
- [x] `interest_expense` - Interest expense
- [x] `interest_income` - Interest income
- [x] `other_income` - Other non-operating income
- [x] `income_before_tax` - Pre-tax income
- [x] `income_tax` - Income tax expense
- [x] `net_income` - Net income
- [x] `dividends` - Common dividends paid
- [x] `shares_outstanding` - Weighted average shares outstanding
- [x] `diluted_shares_outstanding` - Diluted shares outstanding

### Cash Flow Items
- [x] `operating_cash_flow` - Cash flow from operations
- [x] `capital_expenditures` - Capital expenditures (negative value)
- [x] `acquisitions` - Cash used for acquisitions
- [x] `asset_sales` - Proceeds from asset sales
- [x] `investing_cash_flow` - Cash flow from investing
- [x] `debt_issuance` - Proceeds from debt issuance
- [x] `debt_repayment` - Debt repayments (negative value)
- [x] `equity_issuance` - Proceeds from equity issuance
- [x] `share_repurchases` - Share buybacks (negative value)
- [x] `financing_cash_flow` - Cash flow from financing
- [x] `free_cash_flow` - Free cash flow (operating_cash_flow + capital_expenditures)

### Calculated Items
- [x] `ebitda` - EBITDA (operating_income + depreciation_and_amortization)
- [x] `ebit` - EBIT (operating_income)
- [x] `nopat` - Net operating profit after tax
- [x] `working_capital` - Working capital (current_assets - current_liabilities)
- [x] `net_working_capital` - Operating working capital (excluding cash and debt)
- [x] `net_debt` - Net debt (total_debt - cash_and_equivalents)
- [x] `enterprise_value` - Enterprise value (market_cap + net_debt + minority_interest)
- [x] `invested_capital` - Total invested capital
- [x] `tangible_book_value` - Book value excluding intangibles

### Market Data
- [x] `market_price` - Current stock price
- [x] `market_cap` - Market capitalization
- [x] `dividends_per_share` - Dividends per share
- [x] `earnings_per_share` - Basic EPS
- [x] `book_value_per_share` - Book value per share

## Liquidity Metrics

- [x] **Current Ratio**
  - Formula: `current_assets / current_liabilities`
  - Description: Measures ability to pay short-term obligations

- [x] **Quick Ratio (Acid Test)**
  - Formula: `(current_assets - inventory - prepaid_expenses) / current_liabilities`
  - Description: More conservative liquidity measure

- [x] **Cash Ratio**
  - Formula: `(cash_and_equivalents + short_term_investments) / current_liabilities`
  - Description: Most conservative liquidity measure

- [x] **Operating Cash Flow Ratio**
  - Formula: `operating_cash_flow / current_liabilities`
  - Description: Ability to pay current liabilities with cash from operations

- [x] **Days Sales Outstanding (DSO)**
  - Formula: `(accounts_receivable / revenue) * 365`
  - Description: Average collection period

- [x] **Days Inventory Outstanding (DIO)**
  - Formula: `(inventory / cost_of_goods_sold) * 365`
  - Description: Average inventory holding period

- [x] **Days Payables Outstanding (DPO)**
  - Formula: `(accounts_payable / cost_of_goods_sold) * 365`
  - Description: Average payment period

- [x] **Cash Conversion Cycle**
  - Formula: `days_sales_outstanding + days_inventory_outstanding - days_payables_outstanding`
  - Description: Time to convert investments in inventory to cash

## Leverage/Solvency Metrics

- [x] **Debt-to-Equity Ratio**
  - Formula: `total_debt / total_equity`
  - Description: Financial leverage measure

- [x] **Debt-to-Assets Ratio**
  - Formula: `total_debt / total_assets`
  - Description: Percentage of assets financed by debt

- [x] **Debt-to-Capital Ratio**
  - Formula: `total_debt / (total_debt + total_equity)`
  - Description: Proportion of capital from debt

- [x] **Net Debt-to-Equity Ratio**
  - Formula: `net_debt / total_equity`
  - Description: Leverage adjusted for cash position

- [x] **Financial Leverage Ratio**
  - Formula: `total_assets / total_equity`
  - Description: Assets per dollar of equity

- [x] **Net Debt-to-EBITDA**
  - Formula: `net_debt / ebitda`
  - Description: Years to pay off net debt from EBITDA

- [x] **Total Debt-to-EBITDA**
  - Formula: `total_debt / ebitda`
  - Description: Years to pay off total debt from EBITDA

- [x] **EBITDA-to-Assets**
  - Formula: `ebitda / total_assets`
  - Description: EBITDA generation efficiency

## Coverage Metrics

- [x] **Interest Coverage Ratio (Times Interest Earned)**
  - Formula: `ebit / interest_expense`
  - Description: Ability to pay interest expenses

- [x] **EBITDA Interest Coverage**
  - Formula: `ebitda / interest_expense`
  - Description: Cash-based interest coverage

- [x] **Fixed Charge Coverage Ratio**
  - Formula: `(ebit + lease_expense) / (interest_expense + lease_expense)`
  - Description: Ability to cover fixed charges

- [x] **Debt Service Coverage Ratio (DSCR)**
  - Formula: `operating_cash_flow / (interest_expense + principal_repayments)`
  - Description: Cash available for debt service

- [x] **Cash Flow Coverage**
  - Formula: `operating_cash_flow / total_debt`
  - Description: Cash generation relative to debt

- [x] **Free Cash Flow to Debt**
  - Formula: `free_cash_flow / total_debt`
  - Description: FCF available for debt repayment

## Profitability Metrics

- [x] **Gross Profit Margin**
  - Formula: `gross_profit / revenue`
  - Description: Profitability after direct costs

- [x] **Operating Profit Margin**
  - Formula: `operating_income / revenue`
  - Description: Profitability from operations

- [x] **EBITDA Margin**
  - Formula: `ebitda / revenue`
  - Description: Cash operating profitability

- [x] **Net Profit Margin**
  - Formula: `net_income / revenue`
  - Description: Bottom line profitability

- [x] **Return on Assets (ROA)**
  - Formula: `net_income / total_assets`
  - Description: Profit per dollar of assets

- [x] **Return on Equity (ROE)**
  - Formula: `net_income / total_equity`
  - Description: Return to shareholders

- [x] **Return on Invested Capital (ROIC)**
  - Formula: `nopat / invested_capital`
  - Description: Return on all invested capital

- [x] **Return on Capital Employed (ROCE)**
  - Formula: `ebit / (total_assets - current_liabilities)`
  - Description: Return on capital employed in operations

- [x] **Pre-tax ROA**
  - Formula: `income_before_tax / total_assets`
  - Description: Pre-tax return on assets

## Efficiency Metrics

- [x] **Asset Turnover**
  - Formula: `revenue / total_assets`
  - Description: Revenue per dollar of assets

- [x] **Fixed Asset Turnover**
  - Formula: `revenue / property_plant_equipment`
  - Description: Revenue per dollar of fixed assets

- [x] **Working Capital Turnover**
  - Formula: `revenue / working_capital`
  - Description: Efficiency of working capital use

- [x] **Inventory Turnover**
  - Formula: `cost_of_goods_sold / inventory`
  - Description: Times inventory sold and replaced

- [x] **Receivables Turnover**
  - Formula: `revenue / accounts_receivable`
  - Description: Times receivables collected

- [x] **Payables Turnover**
  - Formula: `cost_of_goods_sold / accounts_payable`
  - Description: Times payables paid

- [x] **Capital Intensity**
  - Formula: `total_assets / revenue`
  - Description: Assets required per dollar of revenue

## Valuation Metrics

- [x] **Price-to-Earnings (P/E)**
  - Formula: `market_price / earnings_per_share`
  - Description: Price per dollar of earnings

- [x] **Price-to-Book (P/B)**
  - Formula: `market_price / book_value_per_share`
  - Description: Price relative to book value

- [x] **Price-to-Sales (P/S)**
  - Formula: `market_cap / revenue`
  - Description: Market value per dollar of sales

- [x] **EV/EBITDA**
  - Formula: `enterprise_value / ebitda`
  - Description: Enterprise value multiple

- [x] **EV/Sales**
  - Formula: `enterprise_value / revenue`
  - Description: Enterprise value to sales

- [x] **EV/EBIT**
  - Formula: `enterprise_value / ebit`
  - Description: Enterprise value to EBIT

- [x] **Dividend Yield**
  - Formula: `dividends_per_share / market_price`
  - Description: Dividend return

- [x] **Earnings Yield**
  - Formula: `earnings_per_share / market_price`
  - Description: Inverse of P/E ratio

- [x] **Free Cash Flow Yield**
  - Formula: `free_cash_flow / market_cap`
  - Description: FCF return to equity holders

- [x] **Book-to-Market**
  - Formula: `book_value_per_share / market_price`
  - Description: Book value relative to market price

## Cash Flow Metrics

- [x] **Operating Cash Flow Margin**
  - Formula: `operating_cash_flow / revenue`
  - Description: Cash generation from operations

- [x] **Free Cash Flow Margin**
  - Formula: `free_cash_flow / revenue`
  - Description: FCF generation efficiency

- [x] **Cash Flow Return on Assets**
  - Formula: `operating_cash_flow / total_assets`
  - Description: Cash generation per dollar of assets

- [x] **Cash Flow Return on Equity**
  - Formula: `operating_cash_flow / total_equity`
  - Description: Cash return to equity holders

- [x] **Cash Flow to Capital Expenditures**
  - Formula: `operating_cash_flow / abs(capital_expenditures)`
  - Description: Ability to fund capex from operations

- [x] **Free Cash Flow to Operating Cash Flow**
  - Formula: `free_cash_flow / operating_cash_flow`
  - Description: Percentage of OCF available after capex

- [x] **Quality of Earnings**
  - Formula: `operating_cash_flow / net_income`
  - Description: Cash backing of reported earnings

## Credit Risk Metrics

- [x] **Altman Z-Score (Manufacturing)**
  - Formula: `1.2 * (working_capital / total_assets) + 1.4 * (retained_earnings / total_assets) + 3.3 * (ebit / total_assets) + 0.6 * (market_cap / total_liabilities) + 1.0 * (revenue / total_assets)`
  - Description: Bankruptcy prediction score

- [x] **Altman Z'-Score (Private Companies)**
  - Formula: `0.717 * (working_capital / total_assets) + 0.847 * (retained_earnings / total_assets) + 3.107 * (ebit / total_assets) + 0.420 * (book_value_equity / total_liabilities) + 0.998 * (revenue / total_assets)`
  - Description: Modified Z-score for private firms

- [x] **Altman Z"-Score (Non-Manufacturing)**
  - Formula: `6.56 * (working_capital / total_assets) + 3.26 * (retained_earnings / total_assets) + 6.72 * (ebit / total_assets) + 1.05 * (book_value_equity / total_liabilities)`
  - Description: Z-score for service companies

- [ ] **Beneish M-Score**
  - Formula: Complex 8-variable model (requires additional nodes for accruals, asset quality, etc.)
  - Description: Earnings manipulation detection

- [ ] **Piotroski F-Score**
  - Components: 9 binary indicators of financial strength
  - Description: Financial health score (0-9)

- [x] **Interest Coverage Below 1.5x Flag**
  - Formula: `interest_coverage_ratio < 1.5`
  - Description: Weak interest coverage indicator

- [x] **Negative Working Capital Flag**
  - Formula: `working_capital < 0`
  - Description: Potential liquidity stress

## DuPont Analysis Components

- [x] **ROE DuPont 3-Step**
  - Formula: `(net_income / revenue) * (revenue / total_assets) * (total_assets / total_equity)`
  - Components: Net Margin × Asset Turnover × Financial Leverage

- [x] **ROE DuPont 5-Step**
  - Formula: `(net_income / ebt) * (ebt / ebit) * (ebit / revenue) * (revenue / total_assets) * (total_assets / total_equity)`
  - Components: Tax Burden × Interest Burden × Operating Margin × Asset Turnover × Financial Leverage

## Growth Metrics

- [x] **Revenue Growth Rate**
  - Formula: `(revenue_current - revenue_prior) / revenue_prior`
  - Description: Year-over-year revenue growth

- [x] **EBITDA Growth Rate**
  - Formula: `(ebitda_current - ebitda_prior) / ebitda_prior`
  - Description: Year-over-year EBITDA growth

- [x] **EPS Growth Rate**
  - Formula: `(eps_current - eps_prior) / eps_prior`
  - Description: Year-over-year EPS growth

- [x] **Asset Growth Rate**
  - Formula: `(total_assets_current - total_assets_prior) / total_assets_prior`
  - Description: Balance sheet expansion rate

- [x] **Sustainable Growth Rate**
  - Formula: `roe * (1 - dividend_payout_ratio)`
  - Description: Growth sustainable from retained earnings

## Per Share Metrics

- [x] **Book Value Per Share**
  - Formula: `total_equity / shares_outstanding`
  - Description: Accounting value per share

- [x] **Tangible Book Value Per Share**
  - Formula: `(total_equity - intangible_assets) / shares_outstanding`
  - Description: Tangible book value per share

- [x] **Revenue Per Share**
  - Formula: `revenue / shares_outstanding`
  - Description: Revenue per share

- [x] **Cash Per Share**
  - Formula: `cash_and_equivalents / shares_outstanding`
  - Description: Cash per share

- [x] **Free Cash Flow Per Share**
  - Formula: `free_cash_flow / shares_outstanding`
  - Description: FCF per share

## Implementation Notes

1. **Node Standardization**: Ensure all base nodes use consistent naming conventions
2. **Data Quality**: Add validation for denominators to avoid division by zero
3. **Time Periods**: Support both point-in-time and average calculations for balance sheet items
4. **Industry Adjustments**: Some metrics need industry-specific modifications
5. **GAAP/IFRS Differences**: Account for accounting standard differences
6. **Missing Data Handling**: Define fallback calculations when certain nodes are unavailable

## Priority Implementation Order

### Phase 1: Core Foundation (Critical for Basic Analysis) ✅ COMPLETED
1. Key liquidity ratios (current, quick)
2. Basic leverage ratios (debt-to-equity, debt-to-assets)
3. Core coverage ratios (interest coverage, DSCR)
4. Essential profitability (margins, ROE, ROA)
5. Basic valuation (P/E, EV/EBITDA)

### Phase 2: Credit Analysis Focus ✅ COMPLETED
1. Net debt calculations and ratios
2. Free cash flow metrics
3. Altman Z-Score variants
4. Advanced coverage ratios
5. Credit flags and warnings

### Phase 3: Comprehensive Analysis ✅ COMPLETED
1. Efficiency metrics
2. DuPont analysis
3. Per share calculations
4. Growth metrics
5. Quality of earnings

### Phase 4: Advanced Features ✅ COMPLETED
1. Industry-specific adjustments
2. Peer comparison tools
3. Trend analysis
4. Scenario testing capabilities
5. Automated ratio interpretation 