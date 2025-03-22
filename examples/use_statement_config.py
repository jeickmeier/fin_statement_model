#!/usr/bin/env python
"""
Example script to demonstrate using the config-driven statement structure.

This script shows how to:
1. Load statement configurations
2. Create a graph with data nodes
3. Generate financial statements from configurations
4. Format and export statements
"""

import os
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import DataNode, NodeType
from fin_statement_model.statements import StatementManager

# Create a new graph
graph = Graph()

# Set up periods
periods = ["2022-Q1", "2022-Q2", "2022-Q3", "2022-Q4", "2023-Q1", "2023-Q2"]
graph.set_periods(periods)

# Create some sample data nodes
# Revenue data
revenue_data = {
    "2022-Q1": 1000000, "2022-Q2": 1100000, "2022-Q3": 1150000, "2022-Q4": 1250000,
    "2023-Q1": 1200000, "2023-Q2": 1300000
}
graph.add_node(DataNode("revenue", "Revenue", NodeType.DATA, revenue_data))

# Returns and allowances
returns_data = {
    "2022-Q1": -50000, "2022-Q2": -55000, "2022-Q3": -57500, "2022-Q4": -62500,
    "2023-Q1": -60000, "2023-Q2": -65000
}
graph.add_node(DataNode("returns_allowances", "Returns and Allowances", NodeType.DATA, returns_data))

# Cost of goods sold
cogs_data = {
    "2022-Q1": -400000, "2022-Q2": -440000, "2022-Q3": -460000, "2022-Q4": -500000,
    "2023-Q1": -480000, "2023-Q2": -520000
}
graph.add_node(DataNode("cogs", "Cost of Goods Sold", NodeType.DATA, cogs_data))

# Selling expenses
selling_expenses_data = {
    "2022-Q1": -150000, "2022-Q2": -165000, "2022-Q3": -172500, "2022-Q4": -187500,
    "2023-Q1": -180000, "2023-Q2": -195000
}
graph.add_node(DataNode("selling_expenses", "Selling Expenses", NodeType.DATA, selling_expenses_data))

# General and administrative expenses
g_and_a_data = {
    "2022-Q1": -200000, "2022-Q2": -220000, "2022-Q3": -230000, "2022-Q4": -250000,
    "2023-Q1": -240000, "2023-Q2": -260000
}
graph.add_node(DataNode("g_and_a", "G&A Expenses", NodeType.DATA, g_and_a_data))

# Research and development expenses
r_and_d_data = {
    "2022-Q1": -100000, "2022-Q2": -110000, "2022-Q3": -115000, "2022-Q4": -125000,
    "2023-Q1": -120000, "2023-Q2": -130000
}
graph.add_node(DataNode("r_and_d", "R&D Expenses", NodeType.DATA, r_and_d_data))

# Interest income
interest_income_data = {
    "2022-Q1": 5000, "2022-Q2": 5500, "2022-Q3": 5750, "2022-Q4": 6250,
    "2023-Q1": 6000, "2023-Q2": 6500
}
graph.add_node(DataNode("interest_income", "Interest Income", NodeType.DATA, interest_income_data))

# Interest expense
interest_expense_data = {
    "2022-Q1": -10000, "2022-Q2": -11000, "2022-Q3": -11500, "2022-Q4": -12500,
    "2023-Q1": -12000, "2023-Q2": -13000
}
graph.add_node(DataNode("interest_expense", "Interest Expense", NodeType.DATA, interest_expense_data))

# Other income
other_income_data = {
    "2022-Q1": 2000, "2022-Q2": 2200, "2022-Q3": 2300, "2022-Q4": 2500,
    "2023-Q1": 2400, "2023-Q2": 2600
}
graph.add_node(DataNode("other_income", "Other Income", NodeType.DATA, other_income_data))

# Other expense
other_expense_data = {
    "2022-Q1": -3000, "2022-Q2": -3300, "2022-Q3": -3450, "2022-Q4": -3750,
    "2023-Q1": -3600, "2023-Q2": -3900
}
graph.add_node(DataNode("other_expense", "Other Expense", NodeType.DATA, other_expense_data))

# Income tax
income_tax_data = {
    "2022-Q1": -25000, "2022-Q2": -27500, "2022-Q3": -28750, "2022-Q4": -31250,
    "2023-Q1": -30000, "2023-Q2": -32500
}
graph.add_node(DataNode("income_tax", "Income Tax", NodeType.DATA, income_tax_data))

# Weighted average shares outstanding - basic
weighted_avg_shares_basic_data = {
    "2022-Q1": 1000000, "2022-Q2": 1000000, "2022-Q3": 1000000, "2022-Q4": 1000000,
    "2023-Q1": 1100000, "2023-Q2": 1100000
}
graph.add_node(DataNode("weighted_avg_shares_basic", "Weighted Avg Shares (Basic)", NodeType.DATA, weighted_avg_shares_basic_data))

# Weighted average shares outstanding - diluted
weighted_avg_shares_diluted_data = {
    "2022-Q1": 1050000, "2022-Q2": 1050000, "2022-Q3": 1050000, "2022-Q4": 1050000,
    "2023-Q1": 1150000, "2023-Q2": 1150000
}
graph.add_node(DataNode("weighted_avg_shares_diluted", "Weighted Avg Shares (Diluted)", NodeType.DATA, weighted_avg_shares_diluted_data))

# Create statement manager
statement_manager = StatementManager(graph)

# Get the absolute path to the config examples directory
script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
config_dir = script_dir.parent / "fin_statement_model" / "config" / "examples"

# Load income statement configuration
income_statement = statement_manager.load_statement(str(config_dir / "income_statement.json"))
print(f"Loaded income statement: {income_statement.name}")

# Create calculation nodes based on the structure
created_nodes = statement_manager.create_calculations(income_statement.id)
print(f"Created {len(created_nodes)} calculation nodes for income statement")

# Format the income statement as a DataFrame
income_df = statement_manager.format_statement(
    income_statement.id, 
    format_type='dataframe',
    apply_sign_convention=True
)

# Display the income statement
print("\nIncome Statement:")
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
print(income_df)

# Export to Excel
output_dir = script_dir / "output"
output_dir.mkdir(exist_ok=True)
statement_manager.export_to_excel(
    income_statement.id,
    str(output_dir / "income_statement.xlsx")
)
print(f"\nExported income statement to {output_dir / 'income_statement.xlsx'}")

# Generate HTML representation
html_output = statement_manager.format_statement(
    income_statement.id,
    format_type='html',
    apply_sign_convention=True,
    title="Quarterly Income Statement"
)

# Save HTML to file
with open(output_dir / "income_statement.html", "w") as f:
    f.write(html_output)
print(f"Exported income statement HTML to {output_dir / 'income_statement.html'}")

# Create a simple visualization of net income trend
net_income_values = []
for period in periods:
    try:
        value = graph.calculate("net_income", period)
        net_income_values.append(value)
    except Exception as e:
        print(f"Error calculating net income for {period}: {e}")
        net_income_values.append(0)

plt.figure(figsize=(10, 6))
plt.bar(periods, net_income_values)
plt.title('Net Income by Quarter')
plt.xlabel('Quarter')
plt.ylabel('Net Income')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.savefig(output_dir / "net_income_trend.png")
print(f"Created net income trend chart at {output_dir / 'net_income_trend.png'}")

# To demonstrate loading another statement configuration:
# Uncomment if you want to load and process the balance sheet
"""
# Load balance sheet configuration
balance_sheet = statement_manager.load_statement(str(config_dir / "balance_sheet.json"))
print(f"\nLoaded balance sheet: {balance_sheet.name}")

# Create calculation nodes based on the balance sheet structure
balance_sheet_nodes = statement_manager.create_calculations(balance_sheet.id)
print(f"Created {len(balance_sheet_nodes)} calculation nodes for balance sheet")

# Format the balance sheet as a DataFrame
balance_df = statement_manager.format_statement(
    balance_sheet.id, 
    format_type='dataframe',
    apply_sign_convention=True
)

# Display the balance sheet
print("\nBalance Sheet:")
print(balance_df)

# Export to Excel
statement_manager.export_to_excel(
    balance_sheet.id,
    str(output_dir / "balance_sheet.xlsx")
)
print(f"Exported balance sheet to {output_dir / 'balance_sheet.xlsx'}")
"""

print("\nExample completed successfully!")

if __name__ == "__main__":
    pass 