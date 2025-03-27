"""
Simple example script demonstrating how to use the FMP (Financial Modeling Prep) importer
with the financial statement model.

This script focuses on the basic usage of the FMP importer to fetch financial statement data.

Requirements:
- FMP API key (set as environment variable FMP_API_KEY or pass directly)

Example usage:
    $ export FMP_API_KEY=your_api_key_here
    $ python simple_fmp_example.py
"""

from fin_statement_model.importers.fmp import FMPAdapter
from fin_statement_model.core.financial_statement import FinancialStatementGraph
import pandas as pd


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
    ticker = input("Enter a ticker symbol (default: AAPL): ").strip() or "AAPL"

    print(f"Setting up FMP adapter for {ticker}...")
    fmp_adapter = FMPAdapter(api_key=api_key)

    # Authenticate with the API
    if not fmp_adapter.authenticate():
        print("Failed to authenticate with FMP API. Please check your API key.")
        return

    # Choose statement type
    print("\nAvailable statement types:")
    print("1. Income Statement")
    print("2. Balance Sheet")
    print("3. Cash Flow")

    choice = input("Select statement type (1-3, default: 1): ").strip() or "1"

    statement_types = {"1": "income_statement", "2": "balance_sheet", "3": "cash_flow"}

    statement_type = statement_types.get(choice, "income_statement")

    # Choose period type
    period_choice = (
        input("Select period type (FY for annual, QTR for quarterly, default: FY): ")
        .strip()
        .upper()
        or "FY"
    )
    period_type = "FY" if period_choice not in ["FY", "QTR"] else period_choice

    # Number of periods to fetch
    try:
        limit = int(input("Number of periods to fetch (default: 5): ").strip() or "5")
    except ValueError:
        limit = 5

    # Import statement data based on type
    print(f"\nImporting {statement_type} data for {ticker}...")

    try:
        # For cash flow statements, handle potential conflicts
        if statement_type == "cash_flow":
            # Fetch raw data
            try:
                # Fetch the raw data first
                cash_flow_data = fmp_adapter.fetch_statement(
                    identifier=ticker,
                    period_type=period_type,
                    limit=limit,
                    statement_type=statement_type,
                )

                # Create a new statement graph
                periods = []
                for statement in cash_flow_data:
                    date = statement["date"]  # type: ignore
                    if period_type == "FY":
                        period_label = f"FY{date[:4]}"
                    else:
                        quarter = pd.Timestamp(date).quarter
                        period_label = f"{date[:4]}Q{quarter}"
                    periods.append(period_label)
                periods = sorted(list(set(periods)))

                financial_statement = FinancialStatementGraph(periods=periods)

                # Process the data manually to avoid node name conflicts
                field_mapping = fmp_adapter.get_field_mapping(statement_type)

                # Add a suffix to nodes that might conflict
                conflict_nodes = ["net_income", "operating_cash_flow"]
                for fmp_field, node_name in field_mapping.items():
                    if node_name in conflict_nodes:
                        field_mapping[fmp_field] = f"{node_name}_cf"

                # Add nodes with values
                for fmp_field, node_name in field_mapping.items():
                    values = {}
                    for statement in cash_flow_data:
                        date = statement["date"]  # type: ignore
                        if period_type == "FY":
                            period_label = f"FY{date[:4]}"
                        else:
                            quarter = pd.Timestamp(date).quarter
                            period_label = f"{date[:4]}Q{quarter}"

                        if fmp_field in statement:
                            value = statement[fmp_field]  # type: ignore
                            if value is not None:
                                values[period_label] = float(value)

                    if values:  # Only add node if we have values
                        financial_statement.add_financial_statement_item(
                            node_name, values
                        )

                # Add common calculations
                financial_statement.add_calculation(
                    "free_cash_flow_cf",
                    ["operating_cash_flow_cf", "capital_expenditure"],
                    "addition",
                )

                financial_statement.add_calculation(
                    "total_cash_flow",
                    [
                        "operating_cash_flow_cf",
                        "investing_cash_flow",
                        "financing_cash_flow",
                    ],
                    "addition",
                )
            except Exception as e:
                print(f"Error processing cash flow data manually: {e}")
                # Fall back to using the standard method
                financial_statement = fmp_adapter.create_statement_graph(
                    identifier=ticker,
                    period_type=period_type,
                    limit=limit,
                    statement_type=statement_type,
                )
        else:
            # Use the standard method for income statement and balance sheet
            financial_statement = fmp_adapter.create_statement_graph(
                identifier=ticker,
                period_type=period_type,
                limit=limit,
                statement_type=statement_type,
            )

        # Print financial statement data as DataFrame
        print(f"\n{statement_type.replace('_', ' ').title()}:")
        df = financial_statement.to_dataframe()
        print(df)

        # Export to Excel if requested
        export_choice = (
            input("\nExport to Excel? (y/n, default: n): ").strip().lower() or "n"
        )
        if export_choice == "y":
            excel_file = f"{ticker}_{statement_type}.xlsx"

            try:
                # Export directly using pandas
                df.to_excel(excel_file)
                print(f"Financial statement exported to {excel_file}")
            except Exception as e:
                print(f"Error exporting to Excel: {e}")

    except Exception as e:
        print(f"Error: {e}")

    print("\nDone!")


if __name__ == "__main__":
    main()
