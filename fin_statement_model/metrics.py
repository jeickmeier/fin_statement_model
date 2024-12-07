METRIC_DEFINITIONS = {
    # Profitability Metrics
    "gross_profit": {
        "calculation_type": "subtraction",
        "inputs": ["revenue", "cost_of_goods_sold"],
        "metric_type": "profitability",
        "metric_description": "The profit a company makes after deducting the costs directly associated with making and selling its products or services."
    },
    "operating_income": {
        "calculation_type": "subtraction", 
        "inputs": ["gross_profit", "operating_expenses"],
        "metric_type": "profitability",
        "metric_description": "Profit generated from core business operations, excluding interest and taxes."
    },
    "ebit": {
        "calculation_type": "addition",
        "inputs": ["operating_income", "non_operating_income", "(-non_operating_expenses)"],
        "metric_type": "profitability",
        "metric_description": "Earnings Before Interest and Taxes; measures company's operating performance without considering financial and tax-related decisions."
    },
    "ebitda": {
        "calculation_type": "addition",
        "inputs": ["ebit", "depreciation", "amortization"],
        "metric_type": "profitability",
        "metric_description": "Earnings Before Interest, Taxes, Depreciation, and Amortization; indicates operational performance excluding non-cash expenses."
    },
    "nopat": {
        "calculation_type": "multiplication",
        "inputs": ["ebit", "(1 - tax_rate)"],
        "metric_type": "profitability",
        "metric_description": "Net Operating Profit After Taxes; shows operating performance after tax adjustments but before financing costs."
    },

    # Margin Metrics
    "gross_profit_margin": {
        "calculation_type": "division",
        "inputs": ["gross_profit", "revenue"],
        "metric_type": "margin",
        "metric_description": "Percentage of revenue remaining after deducting cost of goods sold; indicates pricing strategy and production efficiency."
    },
    "operating_margin": {
        "calculation_type": "division",
        "inputs": ["operating_income", "revenue"],
        "metric_type": "margin",
        "metric_description": "Percentage of revenue remaining after operating expenses; measures operational efficiency."
    },
    "net_profit_margin": {
        "calculation_type": "division",
        "inputs": ["net_income", "revenue"],
        "metric_type": "margin",
        "metric_description": "Percentage of revenue that becomes profit after all expenses; indicates overall profitability."
    },
    "ebit_margin": {
        "calculation_type": "division",
        "inputs": ["ebit", "revenue"],
        "metric_type": "margin",
        "metric_description": "Operating profitability as a percentage of revenue before interest and taxes."
    },
    "ebitda_margin": {
        "calculation_type": "division",
        "inputs": ["ebitda", "revenue"],
        "metric_type": "margin",
        "metric_description": "Operating performance as a percentage of revenue before financial, tax, and non-cash items."
    },
    "nopat_margin": {
        "calculation_type": "division",
        "inputs": ["nopat", "revenue"],
        "metric_type": "margin",
        "metric_description": "After-tax operating profit as a percentage of revenue."
    },

    # Asset Metrics
    "average_total_assets": {
        "calculation_type": "average_of_two_periods",
        "inputs": ["total_assets"],
        "metric_type": "asset",
        "metric_description": "Mean value of assets between two periods; used for various return calculations."
    },
    "average_shareholders_equity": {
        "calculation_type": "average_of_two_periods",
        "inputs": ["total_equity"],
        "metric_type": "asset",
        "metric_description": "Mean value of shareholders' equity between two periods; used for return calculations."
    },

    # Return Metrics
    "return_on_assets": {
        "calculation_type": "division",
        "inputs": ["net_income", "average_total_assets"],
        "metric_type": "return",
        "metric_description": "Measures how efficiently a company uses its assets to generate profits."
    },
    "return_on_equity": {
        "calculation_type": "division",
        "inputs": ["net_income", "average_shareholders_equity"],
        "metric_type": "return",
        "metric_description": "Measures how efficiently a company uses shareholders' investments to generate profits."
    },
    "temp_debt_equity": {
        "calculation_type": "addition",
        "inputs": ["total_debt", "total_equity"],
        "metric_type": "return",
        "metric_description": "Temporary calculation for invested capital computation."
    },
    "invested_capital": {
        "calculation_type": "subtraction",
        "inputs": ["temp_debt_equity", "cash"],
        "metric_type": "return",
        "metric_description": "Total investment in the business excluding excess cash; used for ROIC calculation."
    },
    "roic": {
        "calculation_type": "division",
        "inputs": ["nopat", "average_invested_capital"],
        "metric_type": "return",
        "metric_description": "Return on Invested Capital; measures how efficiently a company uses all capital to generate profits."
    },
    "capital_employed": {
        "calculation_type": "subtraction",
        "inputs": ["total_assets", "current_liabilities"],
        "metric_type": "return",
        "metric_description": "Long-term capital invested in the business; used for ROCE calculation."
    },
    "roce": {
        "calculation_type": "division",
        "inputs": ["ebit", "average_capital_employed"],
        "metric_type": "return",
        "metric_description": "Return on Capital Employed; measures profitability relative to long-term financing."
    },

    # Liquidity Metrics
    "current_ratio": {
        "calculation_type": "division",
        "inputs": ["current_assets", "current_liabilities"],
        "metric_type": "liquidity",
        "metric_description": "Measures company's ability to pay short-term obligations with short-term assets."
    },
    "quick_assets": {
        "calculation_type": "subtraction",
        "inputs": ["current_assets", "inventory"],
        "metric_type": "liquidity",
        "metric_description": "Most liquid assets; used in quick ratio calculation."
    },
    "quick_ratio": {
        "calculation_type": "division",
        "inputs": ["quick_assets", "current_liabilities"],
        "metric_type": "liquidity",
        "metric_description": "More conservative measure of liquidity that excludes inventory from current assets."
    },
    "cash_ratio": {
        "calculation_type": "division",
        "inputs": ["cash", "current_liabilities"],
        "metric_type": "liquidity",
        "metric_description": "Most conservative liquidity measure; shows ability to cover short-term debt with cash only."
    },

    # Leverage Metrics
    "debt_to_equity": {
        "calculation_type": "division",
        "inputs": ["total_debt", "total_shareholders_equity"],
        "metric_type": "leverage",
        "metric_description": "Measures extent of debt financing relative to equity financing."
    },
    "debt_to_assets": {
        "calculation_type": "division",
        "inputs": ["total_debt", "total_assets"],
        "metric_type": "leverage",
        "metric_description": "Indicates percentage of assets financed through debt."
    },
    "interest_coverage": {
        "calculation_type": "division",
        "inputs": ["ebit", "interest_expense"],
        "metric_type": "leverage",
        "metric_description": "Indicates ability to meet interest payments from operating earnings."
    },
    "financial_leverage": {
        "calculation_type": "division",
        "inputs": ["average_total_assets", "average_shareholders_equity"],
        "metric_type": "leverage",
        "metric_description": "Measures total assets relative to shareholders' equity; indicates leverage level."
    },
    "equity_multiplier": {
        "calculation_type": "division",
        "inputs": ["total_assets", "total_equity"],
        "metric_type": "leverage",
        "metric_description": "Alternative measure of financial leverage; shows assets funded by each dollar of equity."
    },

    # Debt Service Metrics
    "cash_available_for_debt_service": {
        "calculation_type": "addition",
        "inputs": ["operating_cash_flow", "interest_expense", "taxes"],
        "metric_type": "debt_service",
        "metric_description": "Cash available to service debt obligations after operations."
    },
    "debt_service_coverage_ratio": {
        "calculation_type": "division",
        "inputs": ["cash_available_for_debt_service", "debt_service"],
        "metric_type": "debt_service",
        "metric_description": "Measures ability to service debt obligations from operating cash flow."
    },
    "ebit_plus_fixed_charges": {
        "calculation_type": "addition",
        "inputs": ["ebit", "fixed_charges_before_tax"],
        "metric_type": "debt_service",
        "metric_description": "Operating earnings plus fixed charges; used in fixed charge coverage ratio."
    },
    "fixed_charge_coverage_ratio": {
        "calculation_type": "division",
        "inputs": ["ebit_plus_fixed_charges", "fixed_charges"],
        "metric_type": "debt_service",
        "metric_description": "Measures ability to meet fixed payment obligations from earnings."
    },

    # Efficiency Metrics
    "asset_turnover": {
        "calculation_type": "division",
        "inputs": ["revenue", "average_total_assets"],
        "metric_type": "efficiency",
        "metric_description": "Measures how efficiently assets are used to generate revenue."
    },
    "inventory_turnover": {
        "calculation_type": "division",
        "inputs": ["cost_of_goods_sold", "average_inventory"],
        "metric_type": "efficiency",
        "metric_description": "Indicates how many times inventory is sold and replaced over a period."
    },
    "receivables_turnover": {
        "calculation_type": "division",
        "inputs": ["revenue", "average_accounts_receivable"],
        "metric_type": "efficiency",
        "metric_description": "Measures how quickly customers pay their bills."
    },
    "payables_turnover": {
        "calculation_type": "division",
        "inputs": ["cost_of_goods_sold", "average_accounts_payable"],
        "metric_type": "efficiency",
        "metric_description": "Measures how quickly the company pays its suppliers."
    },

    # Working Capital Metrics
    "ar_over_revenue": {
        "calculation_type": "division",
        "inputs": ["average_accounts_receivable", "revenue"],
        "metric_type": "working_capital",
        "metric_description": "Proportion of receivables to revenue; used in DSO calculation."
    },
    "dso": {
        "calculation_type": "multiplication",
        "inputs": ["ar_over_revenue", "365"],
        "metric_type": "working_capital",
        "metric_description": "Days Sales Outstanding; average number of days to collect payment."
    },
    "inv_over_cogs": {
        "calculation_type": "division",
        "inputs": ["average_inventory", "cost_of_goods_sold"],
        "metric_type": "working_capital",
        "metric_description": "Proportion of inventory to COGS; used in DIO calculation."
    },
    "dio": {
        "calculation_type": "multiplication",
        "inputs": ["inv_over_cogs", "365"],
        "metric_type": "working_capital",
        "metric_description": "Days Inventory Outstanding; average days to sell inventory."
    },
    "ap_over_cogs": {
        "calculation_type": "division",
        "inputs": ["average_accounts_payable", "cost_of_goods_sold"],
        "metric_type": "working_capital",
        "metric_description": "Proportion of payables to COGS; used in DPO calculation."
    },
    "dpo": {
        "calculation_type": "multiplication",
        "inputs": ["ap_over_cogs", "365"],
        "metric_type": "working_capital",
        "metric_description": "Days Payables Outstanding; average days to pay suppliers."
    },
    "temp_dso_dio": {
        "calculation_type": "addition",
        "inputs": ["dso", "dio"],
        "metric_type": "working_capital",
        "metric_description": "Temporary calculation for cash conversion cycle."
    },
    "cash_conversion_cycle": {
        "calculation_type": "subtraction",
        "inputs": ["temp_dso_dio", "dpo"],
        "metric_type": "working_capital",
        "metric_description": "Number of days to convert resource inputs into cash flows."
    },

    # Asset Utilization Metrics
    "working_capital_turnover": {
        "calculation_type": "division",
        "inputs": ["revenue", "average_working_capital"],
        "metric_type": "asset_utilization",
        "metric_description": "Measures how efficiently working capital is used to generate sales."
    },
    "fixed_asset_turnover": {
        "calculation_type": "division",
        "inputs": ["revenue", "average_net_fixed_assets"],
        "metric_type": "asset_utilization",
        "metric_description": "Measures how efficiently fixed assets are used to generate sales."
    },

    # Market Metrics
    "eps": {
        "calculation_type": "division",
        "inputs": ["net_income", "shares_outstanding"],
        "metric_type": "market",
        "metric_description": "Earnings Per Share; profit allocated to each outstanding share."
    },
    "p_e_ratio": {
        "calculation_type": "division",
        "inputs": ["share_price", "eps"],
        "metric_type": "market",
        "metric_description": "Price-to-Earnings ratio; indicates market value relative to earnings."
    },
    "p_s_ratio": {
        "calculation_type": "division",
        "inputs": ["market_capitalization", "revenue"],
        "metric_type": "market",
        "metric_description": "Price-to-Sales ratio; indicates market value relative to revenue."
    },
    "ev_ebitda": {
        "calculation_type": "division",
        "inputs": ["enterprise_value", "ebitda"],
        "metric_type": "market",
        "metric_description": "Enterprise Value to EBITDA; indicates company value relative to operating performance."
    },
    "ev_ebit": {
        "calculation_type": "division",
        "inputs": ["enterprise_value", "ebit"],
        "metric_type": "market",
        "metric_description": "Enterprise Value to EBIT; indicates company value relative to operating earnings."
    },

    # Dividend Metrics
    "dividends_per_share": {
        "calculation_type": "division",
        "inputs": ["annual_dividends", "shares_outstanding"],
        "metric_type": "dividend",
        "metric_description": "Total dividends paid divided by number of shares outstanding."
    },
    "dividend_yield": {
        "calculation_type": "division",
        "inputs": ["dividends_per_share", "share_price"],
        "metric_type": "dividend",
        "metric_description": "Dividend return relative to share price."
    },
    "dividend_payout_ratio": {
        "calculation_type": "division",
        "inputs": ["dividends", "net_income"],
        "metric_type": "dividend",
        "metric_description": "Proportion of earnings paid out as dividends."
    },

    # Cash Flow Metrics
    "free_cash_flow": {
        "calculation_type": "subtraction",
        "inputs": ["operating_cash_flow", "capex"],
        "metric_type": "cash_flow",
        "metric_description": "Cash available after operating expenses and capital investments."
    },
    "p_fcf": {
        "calculation_type": "division",
        "inputs": ["market_capitalization", "free_cash_flow"],
        "metric_type": "cash_flow",
        "metric_description": "Price to Free Cash Flow; indicates market value relative to cash generation."
    },
    "ev_sales": {
        "calculation_type": "division",
        "inputs": ["enterprise_value", "revenue"],
        "metric_type": "cash_flow",
        "metric_description": "Enterprise Value to Sales ratio; indicates company value relative to revenue."
    },

    # Growth Metrics
    "revenue_change": {
        "calculation_type": "subtraction",
        "inputs": ["revenue_current", "revenue_previous"],
        "metric_type": "growth",
        "metric_description": "Absolute change in revenue between periods."
    },
    "revenue_growth": {
        "calculation_type": "division",
        "inputs": ["revenue_change", "revenue_previous"],
        "metric_type": "growth",
        "metric_description": "Percentage change in revenue between periods."
    },
    "eps_change": {
        "calculation_type": "subtraction",
        "inputs": ["eps_current", "eps_previous"],
        "metric_type": "growth",
        "metric_description": "Absolute change in EPS between periods."
    },
    "eps_growth": {
        "calculation_type": "division",
        "inputs": ["eps_change", "eps_previous"],
        "metric_type": "growth",
        "metric_description": "Percentage change in EPS between periods."
    },
    "peg_ratio": {
        "calculation_type": "division",
        "inputs": ["p_e_ratio", "eps_growth"],
        "metric_type": "growth",
        "metric_description": "P/E ratio relative to EPS growth rate; indicates value considering growth."
    },
    "net_income_change": {
        "calculation_type": "subtraction",
        "inputs": ["net_income_current", "net_income_previous"],
        "metric_type": "growth",
        "metric_description": "Absolute change in net income between periods."
    },
    "net_income_growth": {
        "calculation_type": "division",
        "inputs": ["net_income_change", "net_income_previous"],
        "metric_type": "growth",
        "metric_description": "Percentage change in net income between periods."
    },
    "dividend_change": {
        "calculation_type": "subtraction",
        "inputs": ["dividends_current", "dividends_previous"],
        "metric_type": "growth",
        "metric_description": "Absolute change in dividends between periods."
    },
    "dividend_growth": {
        "calculation_type": "division",
        "inputs": ["dividend_change", "dividends_previous"],
        "metric_type": "growth",
        "metric_description": "Percentage change in dividends between periods."
    },

    # Additional Performance Metrics
    "return_on_sales": {
        "calculation_type": "division",
        "inputs": ["ebit", "revenue"],
        "metric_type": "performance",
        "metric_description": "Operating profit as a percentage of sales; indicates operational efficiency."
    },
    "gross_profit_change": {
        "calculation_type": "subtraction",
        "inputs": ["gross_profit_current", "gross_profit_previous"],
        "metric_type": "performance",
        "metric_description": "Absolute change in gross profit between periods."
    },
    "gross_profit_growth": {
        "calculation_type": "division",
        "inputs": ["gross_profit_change", "gross_profit_previous"],
        "metric_type": "performance",
        "metric_description": "Percentage change in gross profit between periods."
    },
    "cash_return_on_assets": {
        "calculation_type": "division",
        "inputs": ["operating_cash_flow", "average_total_assets"],
        "metric_type": "performance",
        "metric_description": "Cash-based return on assets; indicates asset efficiency in generating cash."
    },
    "ocf_minus_capex": {
        "calculation_type": "subtraction",
        "inputs": ["operating_cash_flow", "capex"],
        "metric_type": "performance",
        "metric_description": "Operating cash flow less capital expenditures; used in FCFE calculation."
    },
    "fcfe": {
        "calculation_type": "addition",
        "inputs": ["ocf_minus_capex", "net_borrowings"],
        "metric_type": "performance",
        "metric_description": "Free Cash Flow to Equity; cash available to equity holders."
    },
    "free_cash_flow_per_share": {
        "calculation_type": "division",
        "inputs": ["free_cash_flow", "shares_outstanding"],
        "metric_type": "performance",
        "metric_description": "Free cash flow allocated to each outstanding share."
    },
    "fcf_yield": {
        "calculation_type": "division",
        "inputs": ["free_cash_flow_per_share", "share_price"],
        "metric_type": "performance",
        "metric_description": "Free cash flow return relative to share price."
    },
    "dupont_roe": {
        "calculation_type": "multiplication",
        "inputs": ["net_profit_margin", "asset_turnover", "equity_multiplier"],
        "metric_type": "performance",
        "metric_description": "Detailed breakdown of ROE into operational efficiency, asset use efficiency, and leverage."
    }
}