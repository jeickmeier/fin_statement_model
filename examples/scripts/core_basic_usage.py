#!/usr/bin/env python
"""Financial Statement Model - Core Basic Usage Example.

This script demonstrates the fundamental features of the fin_statement_model library:

1. Creating and managing financial statement graphs
2. Adding financial statement items and calculation nodes
3. Working with built-in financial metrics
4. Using adjustments for scenario analysis
5. Basic forecasting functionality
6. Graph inspection and analysis

Run this script to see a complete example of how to use the core library features.
"""

import warnings

from fin_statement_model import logging_config
from fin_statement_model.core import Graph
from fin_statement_model.core.adjustments import AdjustmentType, AdjustmentFilter
from fin_statement_model.core.metrics import (
    metric_registry,
    calculate_metric,
    interpret_metric,
)
from fin_statement_model.forecasting import StatementForecaster
import sys

# Configure logging and suppress warnings for cleaner output
warnings.filterwarnings("ignore")
logging_config.setup_logging(level="WARNING")


def create_sample_graph() -> Graph:
    """Create a sample financial statement graph with historical data.

    Returns:
        Graph: A populated graph with 3 years of financial data.
    """
    # Create graph with 3 years of historical periods
    graph = Graph(periods=["2021", "2022", "2023"])

    # Add income statement items
    graph.add_financial_statement_item(
        "Revenue", {"2021": 1000000.0, "2022": 1200000.0, "2023": 1400000.0}
    )

    graph.add_financial_statement_item(
        "COGS", {"2021": 600000.0, "2022": 700000.0, "2023": 800000.0}
    )

    graph.add_financial_statement_item(
        "OperatingExpenses", {"2021": 200000.0, "2022": 240000.0, "2023": 280000.0}
    )

    graph.add_financial_statement_item(
        "InterestExpense", {"2021": 25000.0, "2022": 30000.0, "2023": 35000.0}
    )

    # Add balance sheet items
    graph.add_financial_statement_item(
        "CurrentAssets", {"2021": 500000.0, "2022": 600000.0, "2023": 700000.0}
    )

    graph.add_financial_statement_item(
        "CurrentLiabilities", {"2021": 300000.0, "2022": 350000.0, "2023": 400000.0}
    )

    graph.add_financial_statement_item(
        "TotalAssets", {"2021": 2000000.0, "2022": 2400000.0, "2023": 2800000.0}
    )

    graph.add_financial_statement_item(
        "TotalEquity", {"2021": 1200000.0, "2022": 1400000.0, "2023": 1600000.0}
    )

    graph.add_financial_statement_item(
        "TotalDebt", {"2021": 800000.0, "2022": 1000000.0, "2023": 1200000.0}
    )

    return graph


def add_calculations(graph: Graph) -> None:
    """Add calculation nodes to derive key financial metrics.

    Args:
        graph: The graph to add calculations to.
    """
    # Create Gross Profit calculation (Revenue - COGS)
    graph.add_calculation(
        name="GrossProfit",
        input_names=["Revenue", "COGS"],
        operation_type="subtraction",
    )

    # Create Operating Income (Gross Profit - Operating Expenses)
    graph.add_calculation(
        name="OperatingIncome",
        input_names=["GrossProfit", "OperatingExpenses"],
        operation_type="subtraction",
    )

    # Create EBIT (same as Operating Income for this example)
    graph.add_calculation(
        name="EBIT",
        input_names=["OperatingIncome"],
        operation_type="formula",
        formula="operating_income",
        formula_variable_names=["operating_income"],
    )

    # Create Net Income (EBIT - Interest - Taxes)
    # Assume 25% tax rate
    graph.add_calculation(
        name="NetIncome",
        input_names=["EBIT", "InterestExpense"],
        operation_type="formula",
        formula="(ebit - interest_expense) * 0.75",  # 25% tax rate
        formula_variable_names=["ebit", "interest_expense"],
    )

    # Create percentage calculations
    graph.add_calculation(
        name="GrossProfitMargin",
        input_names=["GrossProfit", "Revenue"],
        operation_type="formula",
        formula="(gross_profit / revenue) * 100",
        formula_variable_names=["gross_profit", "revenue"],
    )

    graph.add_calculation(
        name="OperatingMargin",
        input_names=["OperatingIncome", "Revenue"],
        operation_type="formula",
        formula="(operating_income / revenue) * 100",
        formula_variable_names=["operating_income", "revenue"],
    )

    graph.add_calculation(
        name="NetProfitMargin",
        input_names=["NetIncome", "Revenue"],
        operation_type="formula",
        formula="(net_income / revenue) * 100",
        formula_variable_names=["net_income", "revenue"],
    )


def demonstrate_basic_calculations(graph: Graph) -> None:
    """Show basic calculation functionality.

    Args:
        graph: The graph with financial data and calculations.
    """
    for period in graph.periods:

        # Core values
        graph.calculate("Revenue", period)
        graph.calculate("COGS", period)
        graph.calculate("GrossProfit", period)
        graph.calculate("OperatingIncome", period)
        graph.calculate("NetIncome", period)

        # Margins
        graph.calculate("GrossProfitMargin", period)
        graph.calculate("OperatingMargin", period)
        graph.calculate("NetProfitMargin", period)


def demonstrate_metrics(graph: Graph) -> None:
    """Demonstrate built-in financial metrics functionality.

    Args:
        graph: The graph with financial data.
    """
    # Show available metrics
    available_metrics = metric_registry.list_metrics()
    for metric in available_metrics[:8]:
        pass

    # Add metric nodes to the graph for easy calculation
    graph.add_metric(
        "current_ratio",
        input_node_map={
            "current_assets": "CurrentAssets",
            "current_liabilities": "CurrentLiabilities",
        },
    )

    # Calculate metrics for 2023
    period = "2023"

    # Current Ratio
    cr_value = graph.calculate("current_ratio", period)
    cr_metric_def = metric_registry.get("current_ratio")
    interpret_metric(cr_metric_def, cr_value)

    # Return on Assets (using direct calculation)
    data_nodes = {
        "net_income": graph.nodes["NetIncome"],
        "total_assets": graph.nodes["TotalAssets"],
    }

    roa_value = calculate_metric("return_on_assets", data_nodes, period)
    roa_metric_def = metric_registry.get("return_on_assets")
    interpret_metric(roa_metric_def, roa_value)

    # Debt to Equity Ratio
    data_nodes_de = {
        "total_debt": graph.nodes["TotalDebt"],
        "total_equity": graph.nodes["TotalEquity"],
    }

    de_value = calculate_metric("debt_to_equity_ratio", data_nodes_de, period)
    de_metric_def = metric_registry.get("debt_to_equity_ratio")
    interpret_metric(de_metric_def, de_value)


def demonstrate_adjustments(graph: Graph) -> None:
    """Demonstrate the adjustments system for scenario analysis.

    Args:
        graph: The graph to apply adjustments to.
    """
    period = "2023"

    # Show base case
    graph.calculate("Revenue", period)
    graph.calculate("OperatingIncome", period)
    graph.calculate("OperatingMargin", period)

    # Create bullish scenario adjustments

    # 15% revenue increase
    graph.add_adjustment(
        node_name="Revenue",
        period=period,
        value=1.15,  # 15% increase
        adj_type=AdjustmentType.MULTIPLICATIVE,
        reason="Bullish scenario - strong market expansion",
        scenario="bullish",
        tags={"Scenario/Bullish", "Revenue", "Growth"},
    )

    # 8% reduction in operating expenses (efficiency gains)
    graph.add_adjustment(
        node_name="OperatingExpenses",
        period=period,
        value=0.92,  # 8% reduction
        adj_type=AdjustmentType.MULTIPLICATIVE,
        reason="Operational efficiency improvements",
        scenario="bullish",
        tags={"Scenario/Bullish", "CostReduction", "Efficiency"},
    )

    # Calculate bullish scenario
    bullish_filter = AdjustmentFilter(include_scenarios={"bullish"})
    bullish_revenue = graph.get_adjusted_value(
        "Revenue", period, filter_input=bullish_filter
    )
    bullish_opex = graph.get_adjusted_value(
        "OperatingExpenses", period, filter_input=bullish_filter
    )

    # Manual calculation for demonstration (in practice, you'd want to propagate adjustments)
    bullish_gross_profit = bullish_revenue - graph.calculate("COGS", period)
    bullish_operating_income = bullish_gross_profit - bullish_opex
    (bullish_operating_income / bullish_revenue) * 100

    # Create bearish scenario

    graph.add_adjustment(
        node_name="Revenue",
        period=period,
        value=0.85,  # 15% decrease
        adj_type=AdjustmentType.MULTIPLICATIVE,
        reason="Bearish scenario - economic downturn",
        scenario="bearish",
        tags={"Scenario/Bearish", "Revenue", "Contraction"},
    )

    # Calculate bearish scenario
    bearish_filter = AdjustmentFilter(include_scenarios={"bearish"})
    graph.get_adjusted_value("Revenue", period, filter_input=bearish_filter)

    # List all adjustments
    for adj in graph.list_all_adjustments():
        pass


def demonstrate_forecasting(graph: Graph) -> None:
    """Demonstrate basic forecasting functionality.

    Args:
        graph: The graph to forecast from.
    """
    # Create forecaster
    forecaster = StatementForecaster(graph)

    # Define forecast periods
    forecast_periods = ["2024", "2025", "2026"]

    # Configure different forecast methods for different nodes
    node_configs = {
        "Revenue": {
            "method": "historical_growth",
            "config": {"aggregation": "mean"},  # Use mean of historical growth rates
        },
        "COGS": {"method": "simple", "config": 0.05},  # 5% growth
        "OperatingExpenses": {
            "method": "curve",
            "config": [0.04, 0.06, 0.08],  # Escalating growth rates
        },
        "CurrentAssets": {"method": "simple", "config": 0.08},  # 8% growth
        "CurrentLiabilities": {"method": "simple", "config": 0.06},  # 6% growth
    }

    # Create the forecast (this modifies the graph)
    try:
        forecaster.create_forecast(
            forecast_periods=forecast_periods, node_configs=node_configs
        )

        # Display forecast results

        # Update graph periods to include forecast periods
        all_periods = graph.periods + forecast_periods

        for period in all_periods:
            revenue = graph.calculate("Revenue", period)

            # Only calculate margins if we have the calculation nodes
            try:
                gross_profit = graph.calculate("GrossProfit", period)
                operating_income = graph.calculate("OperatingIncome", period)
                (gross_profit / revenue) * 100 if revenue != 0 else 0
                ((operating_income / revenue) * 100 if revenue != 0 else 0)

            except Exception:
                # If calculations fail for forecast periods, just show revenue
                pass

        # Show growth rates
        prev_revenue = None
        for period in all_periods:
            revenue = graph.calculate("Revenue", period)
            if prev_revenue is not None:
                ((revenue / prev_revenue) - 1) * 100
            else:
                pass
            prev_revenue = revenue

    except Exception:
        pass


def demonstrate_graph_inspection(graph: Graph) -> None:
    """Show graph inspection and analysis capabilities.

    Args:
        graph: The graph to inspect.
    """
    # Categorize nodes
    fs_items = []
    calculations = []
    metrics = []

    for name, node in graph.nodes.items():
        if hasattr(node, "inputs") and node.inputs:
            if hasattr(node, "metric_name") and node.metric_name:
                metrics.append(name)
            else:
                calculations.append(name)
        else:
            fs_items.append(name)

    for item in sorted(fs_items):
        values = graph.nodes[item].values
        values.get(graph.periods[-1], 0)

    for calc in sorted(calculations):
        node = graph.nodes[calc]
        if hasattr(node, "inputs") and node.inputs:
            if isinstance(node.inputs, dict):
                list(node.inputs.keys())
            else:
                [f"input_{i}" for i in range(len(node.inputs))]
        else:
            pass

    if metrics:
        for metric in sorted(metrics):
            node = graph.nodes[metric]

    # Show adjustments summary
    adjustments = graph.list_all_adjustments()
    if adjustments:
        scenarios = set(adj.scenario for adj in adjustments)
        for scenario in sorted(scenarios):
            [adj for adj in adjustments if adj.scenario == scenario]


def main() -> int:
    """Run the complete basic usage demonstration."""
    try:
        # 1. Create sample graph
        graph = create_sample_graph()

        # 2. Add calculations
        add_calculations(graph)

        # 3. Demonstrate basic calculations
        demonstrate_basic_calculations(graph)

        # 4. Demonstrate metrics
        demonstrate_metrics(graph)

        # 5. Demonstrate adjustments
        demonstrate_adjustments(graph)

        # 6. Demonstrate forecasting
        demonstrate_forecasting(graph)

        # 7. Graph inspection
        demonstrate_graph_inspection(graph)

    except Exception:
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
