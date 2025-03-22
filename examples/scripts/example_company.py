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

from fin_statement_model.core.financial_statement import FinancialStatementGraph
import matplotlib.pyplot as plt

# Define periods
historical_periods = ["FY2020", "FY2021", "FY2022"]
forecast_periods = ["FY2023", "FY2024", "FY2025"]
all_periods = historical_periods + forecast_periods

# Create a graph with all periods
fsg = FinancialStatementGraph(periods=all_periods)

# Add more complete financial statement data
fsg.add_financial_statement_item("revenue_americas", {"FY2020": 1000.0, "FY2021": 1100.0, "FY2022": 1210.0})
fsg.add_financial_statement_item("revenue_europe", {"FY2020": 800.0, "FY2021": 880.0, "FY2022": 968.0})
fsg.add_financial_statement_item("revenue_apac", {"FY2020": 500.0, "FY2021": 575.0, "FY2022": 661.3})
fsg.add_financial_statement_item("expenses", {"FY2020": 1800.0, "FY2021": 1950.0, "FY2022": 2145.0})

# Add your calculations
fsg.add_calculation("total_revenue", ["revenue_americas", "revenue_europe", "revenue_apac"], "addition")
fsg.add_calculation("operating_profit", ["total_revenue", "expenses"], "subtraction")

fsg.create_forecast(
    forecast_periods,
    {
        "revenue_americas": [0.05, 0.06, 0.07],  # Curve growth
        "revenue_europe": {
            "distribution": "normal",
            "params": {"mean": 0.05, "std": 0.02}
        },  #Statistical
        "revenue_apac": None,  # Historical Average
        "expenses": 0.04  # Simple growth
    },
    method={
        "revenue_americas": "curve",
        "revenue_europe": "statistical",
        "revenue_apac": "historical_growth",
        "expenses": "simple"
    }
)

# Recalculate all values
fsg.recalculate_all()

# Display the results
df = fsg.to_dataframe()
print("Financial Statement Forecast:")
print(df)

# Growth rates table
growth_df = df.pct_change(axis=1)
print("\nYear-over-Year Growth Rates:")
print(growth_df)

# Plot revenue by region
plt.figure(figsize=(12, 6))
for region in ["revenue_americas", "revenue_europe", "revenue_apac"]:
    plt.plot(df.loc[region], marker='o', label=region)

plt.axvline(x="FY2022", color='gray', linestyle='--', label='Forecast Start')
plt.title('Revenue Forecast by Region')
plt.legend()
plt.grid(True)
plt.show()

# Plot total metrics
plt.figure(figsize=(12, 6))
plt.plot(df.loc["total_revenue"], marker='o', label='Total Revenue')
plt.plot(df.loc["expenses"], marker='s', label='Expenses')
plt.plot(df.loc["operating_profit"], marker='^', label='Operating Profit')
plt.axvline(x="FY2022", color='gray', linestyle='--', label='Forecast Start')
plt.title('Financial Performance Forecast')
plt.legend()
plt.grid(True)
plt.show()
