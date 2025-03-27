"""
Example script demonstrating how to use the FMP (Financial Modeling Prep) importer
with the financial statement model.

This script shows how to:
1. Set up the FMP adapter with your API key
2. Import financial statements for a company (using Apple Inc. as an example)
3. Analyze and visualize the imported financial data
4. Add custom calculations to the imported data
5. Export the result to Excel

Requirements:
- FMP API key (set as environment variable FMP_API_KEY or pass directly)
- matplotlib for plotting (pip install matplotlib)

Example usage:
    $ export FMP_API_KEY=your_api_key_here
    $ python fmp_importer_example.py
"""

import os
import matplotlib.pyplot as plt
from fin_statement_model.core.financial_statement import FinancialStatementGraph
from fin_statement_model.importers.fmp import FMPAdapter


def main():
    # Get API key from environment variable or set directly
    api_key = "4A7zLDw1zxKtZn3eVlFN3ZHGbLXpGKz3"  # os.environ.get("FMP_API_KEY")
    if not api_key:
        print(
            "FMP_API_KEY environment variable not set. Please set it or provide your key directly."
        )
        print("Example: export FMP_API_KEY=your_api_key_here")
        return

    # Company ticker to analyze
    ticker = "AAPL"  # Apple Inc.

    # Create FMP adapter with API key
    print(f"Setting up FMP adapter for {ticker}...")
    fmp_adapter = FMPAdapter(api_key=api_key)

    # Import income statement data
    print(f"Importing income statement data for {ticker}...")
    income_statement = fmp_adapter.create_statement_graph(
        identifier=ticker,
        period_type="FY",  # Annual data (use 'QTR' for quarterly)
        limit=5,  # Last 5 years
        statement_type="income_statement",
    )

    # Print income statement data as DataFrame
    print("\nIncome Statement:")
    income_df = income_statement.to_dataframe()
    print(income_df)

    # Import balance sheet data
    print(f"\nImporting balance sheet data for {ticker}...")
    balance_sheet = fmp_adapter.create_statement_graph(
        identifier=ticker, period_type="FY", limit=5, statement_type="balance_sheet"
    )
    balance_df = balance_sheet.to_dataframe()
    print(balance_df)

    # Import cash flow data - with modified node name suffix to avoid conflicts
    print(f"\nImporting cash flow data for {ticker}...")
    cf_sheet = fmp_adapter.create_statement_graph(
        identifier=ticker, period_type="FY", limit=5, statement_type="cash_flow"
    )
    cf_df = cf_sheet.to_dataframe()
    print(cf_df)

    # Add some custom calculations to the income statement
    print("\nAdding custom calculations...")

    # Calculate gross profit margin
    income_statement.add_calculation(
        "gross_profit_margin", ["gross_profit", "revenue"], "division"
    )

    # Calculate operating margin
    income_statement.add_calculation(
        "operating_margin", ["operating_income", "revenue"], "division"
    )

    # Calculate net profit margin
    income_statement.add_calculation(
        "net_profit_margin", ["net_income", "revenue"], "division"
    )

    # Recalculate to update values
    income_statement.recalculate_all()

    # Get updated DataFrame with calculations
    income_df_with_calcs = income_statement.to_dataframe()

    # Print the added metrics
    metrics = ["gross_profit_margin", "operating_margin", "net_profit_margin"]
    print("\nProfitability Metrics:")
    print(income_df_with_calcs.loc[metrics])

    # Plot revenue and profitability trends
    plt.figure(figsize=(12, 6))

    # Get periods (columns) in the correct order
    periods = income_df_with_calcs.columns.tolist()

    # Plot revenue as a bar chart (primary y-axis)
    ax1 = plt.gca()
    ax1.bar(periods, income_df_with_calcs.loc["revenue"], color="lightblue", alpha=0.7)
    ax1.set_ylabel("Revenue (in millions)")
    ax1.set_title(f"{ticker} Revenue and Profitability")

    # Plot margins as lines (secondary y-axis)
    ax2 = ax1.twinx()
    for metric, color in zip(metrics, ["green", "blue", "red"]):
        ax2.plot(
            periods,
            income_df_with_calcs.loc[metric],
            marker="o",
            color=color,
            label=metric,
        )

    ax2.set_ylabel("Margin (%)")
    ax2.set_ylim(0, 1)  # Set y limit from 0 to 1 (0% to 100%)
    ax2.grid(True, linestyle="--", alpha=0.5)

    # Add legend
    lines, labels = ax2.get_legend_handles_labels()
    ax2.legend(lines, labels, loc="upper right")

    # Save the figure
    plt.tight_layout()
    plot_file = f"examples/output/{ticker}_profitability.png"
    os.makedirs(os.path.dirname(plot_file), exist_ok=True)
    plt.savefig(plot_file)
    print(f"\nPlot saved to {plot_file}")

    # Create a consolidated financial model (optional - advanced usage)
    print("\nCreating a basic financial model...")

    # Demonstrate how to combine data from multiple statements
    # Create a new graph with all the periods
    periods = income_df.columns.tolist()
    model = FinancialStatementGraph(periods=periods)

    # Import key metrics from individual statements
    # Revenue and net income from income statement
    model.add_financial_statement_item("revenue", income_df.loc["revenue"].to_dict())
    model.add_financial_statement_item(
        "net_income", income_df.loc["net_income"].to_dict()
    )

    # Total assets and equity from balance sheet
    bs_df = balance_sheet.to_dataframe()
    model.add_financial_statement_item(
        "total_assets", bs_df.loc["total_assets"].to_dict()
    )
    model.add_financial_statement_item(
        "total_equity", bs_df.loc["total_equity"].to_dict()
    )

    # Operating cash flow from cash flow statement
    cf_df = cf_sheet.to_dataframe()

    # Add ROA calculation
    model.add_calculation(
        "return_on_assets", ["net_income", "total_assets"], "division"
    )

    # Add ROE calculation
    model.add_calculation(
        "return_on_equity", ["net_income", "total_equity"], "division"
    )

    # Recalculate and get results
    model.recalculate_all()
    model_df = model.to_dataframe()

    # Print key performance indicators
    print("\nKey Performance Indicators:")
    kpis = ["return_on_assets", "return_on_equity"]
    if "cash_flow_to_revenue" in model.graph.nodes:
        kpis.append("cash_flow_to_revenue")
    print(model_df.loc[kpis])

    # Export the model to Excel - using pandas export directly instead of the method
    model_excel_file = f"examples/output/{ticker}_financial_model.xlsx"
    try:
        model_df.to_excel(model_excel_file)
        print(f"\nFinancial model exported to {model_excel_file}")
    except Exception as e:
        print(f"Error exporting model to Excel: {e}")


if __name__ == "__main__":
    main()
