"""
Example script demonstrating usage of the Financial Statement Model library.

This script creates a sample financial statement graph for a hypothetical company,
populating it with historical financial data and calculating various financial metrics.
It shows how to:
    1. Create a financial statement graph
    2. Add raw financial statement items with historical data
    3. Add and calculate derived financial metrics
    4. Access calculated values for specific time periods

The example uses simplified sample data where:
    - Revenue grows 10% year over year
    - Cost of goods sold is 40% of revenue
    - Operating expenses are 20% of revenue
    - Interest expense is fixed at $50
    - Tax rate is 10% of revenue

The script demonstrates calculation of metrics like:
    - Gross profit
    - Net profit margin
    - DuPont ROE analysis

Example usage:
    $ python example_company.py

The script will output the calculated net profit margin and DuPont ROE for FY2022.
"""

from fin_statement_model.financial_statement import FinancialStatementGraph

if __name__ == "__main__":
    """
    Generate historical financial data for the example company.

    Creates dictionaries mapping fiscal years to financial values:
    - Revenue grows 10% year over year from $1000 base
    - Cost of goods sold (COGS) is 40% of revenue
    - Operating expenses (OPEX) are 20% of revenue  
    - Interest expense is fixed at $50 per year
    - Tax is 10% of revenue
    - Net income is calculated as: Revenue - COGS - OPEX - Interest - Tax

    The data covers fiscal years 2020-2022 (FY2020-FY2022).
    """
    periods = ["FY2020", "FY2021", "FY2022"]
    revenue_data = {"FY2020": 1000.0, "FY2021": 1100.0, "FY2022": 1210.0}
    cogs_data = {p: revenue_data[p] * 0.4 for p in periods}
    opex_data = {p: revenue_data[p] * 0.2 for p in periods}
    interest_data = {p: 50.0 for p in periods}
    tax_data = {p: revenue_data[p] * 0.1 for p in periods}
    net_income_data = {p: (revenue_data[p] - cogs_data[p] - opex_data[p] - interest_data[p] - tax_data[p])
                       for p in periods}

    """
    Create a FinancialStatementGraph instance and add raw financial statement items.
    """
    fsg = FinancialStatementGraph(periods=periods)
 
    # Add financial statement items for each regional revenue
    fsg.add_financial_statement_item("revenue_americas", revenue_data)
    fsg.add_financial_statement_item("revenue_europe", revenue_data)
    fsg.add_financial_statement_item("revenue_apac", revenue_data)

    # Now define a calculation node for total revenue as the sum of these three
    fsg.add_calculation("revenue", ["revenue_americas", "revenue_europe", "revenue_apac"], "addition")

    fsg.add_financial_statement_item("cost_of_goods_sold", cogs_data)
    fsg.add_financial_statement_item("operating_expenses", opex_data)
    fsg.add_financial_statement_item("interest_expense", interest_data)
    fsg.add_financial_statement_item("taxes", tax_data)
    fsg.add_financial_statement_item("net_income", net_income_data)

    # Add balance sheet items needed for DuPont ROE calculation
    # Total assets grows 10% year over year from $5000 base
    total_assets_data = {"FY2020": 5000.0, "FY2021": 5500.0, "FY2022": 6050.0}
    fsg.add_financial_statement_item("total_assets", total_assets_data)
    
    # Add total_assets_previous (shifted by one period)
    total_assets_previous_data = {
        "FY2020": 4545.45,  # FY2019 value (5000/1.1)
        "FY2021": 5000.0,   # FY2020 value
        "FY2022": 5500.0    # FY2021 value
    }
    fsg.add_financial_statement_item("total_assets_previous", total_assets_previous_data)
    
    # Total equity grows 5% year over year from $3000 base
    total_equity_data = {"FY2020": 3000.0, "FY2021": 3150.0, "FY2022": 3307.5}
    fsg.add_financial_statement_item("total_equity", total_equity_data)
    
    # Add total_equity_previous (shifted by one period)
    total_equity_previous_data = {
        "FY2020": 2857.14,  # FY2019 value (3000/1.05)
        "FY2021": 3000.0,   # FY2020 value
        "FY2022": 3150.0    # FY2021 value
    }
    fsg.add_financial_statement_item("total_equity_previous", total_equity_previous_data)
    
    # Add shares outstanding (constant at 1000)
    fsg.add_financial_statement_item("shares_outstanding", {"FY2020": 1000, "FY2021": 1000, "FY2022": 1000})

    """
    Add metrics to the graph.
    """
    # Add metric: gross_profit
    fsg.add_metric("gross_profit")
    # Add metric: net_profit_margin
    fsg.add_metric("net_profit_margin")
    # Add metric: asset_turnover
    fsg.add_metric("asset_turnover")
    # Add metric: equity_multiplier
    fsg.add_metric("equity_multiplier")
    # Add metric: dupont_roe
    fsg.add_metric("dupont_roe")

    """
    Calculate metrics for specific time periods.
    """
    # Calculate net_profit_margin in FY2022
    npm_2022 = fsg.calculate_financial_statement("net_profit_margin", "FY2022")
    print("Net Profit Margin FY2022:", npm_2022)

    # Calculate and print DuPont ROE components and final value
    print("\nDuPont ROE Analysis FY2022:")
    print("Net Profit Margin:", fsg.calculate_financial_statement("net_profit_margin", "FY2022"))
    print("Asset Turnover:", fsg.calculate_financial_statement("asset_turnover", "FY2022"))
    print("Equity Multiplier:", fsg.calculate_financial_statement("equity_multiplier", "FY2022"))
    print("DuPont ROE:", fsg.calculate_financial_statement("dupont_roe", "FY2022"))
