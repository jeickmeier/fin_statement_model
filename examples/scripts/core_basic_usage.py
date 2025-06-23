#!/usr/bin/env python
"""
Financial Statement Model - Core Basic Usage Example

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

# Configure logging and suppress warnings for cleaner output
warnings.filterwarnings("ignore")
logging_config.setup_logging(level="WARNING")


def create_sample_graph() -> Graph:
    """Create a sample financial statement graph with historical data.

    Returns:
        Graph: A populated graph with 3 years of financial data.
    """
    print("Creating sample financial statement graph...")

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

    print(f"✓ Graph created with {len(graph.nodes)} nodes and periods: {graph.periods}")
    return graph


def add_calculations(graph: Graph) -> None:
    """Add calculation nodes to derive key financial metrics.

    Args:
        graph: The graph to add calculations to.
    """
    print("\nAdding calculation nodes...")

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

    print(
        f"✓ Added {len([n for n in graph.nodes.values() if hasattr(n, 'inputs')])} calculation nodes"
    )


def demonstrate_basic_calculations(graph: Graph) -> None:
    """Show basic calculation functionality.

    Args:
        graph: The graph with financial data and calculations.
    """
    print("\n" + "=" * 60)
    print("BASIC FINANCIAL CALCULATIONS")
    print("=" * 60)

    for period in graph.periods:
        print(f"\n{period} Financial Summary:")
        print("-" * 30)

        # Core values
        revenue = graph.calculate("Revenue", period)
        cogs = graph.calculate("COGS", period)
        gross_profit = graph.calculate("GrossProfit", period)
        operating_income = graph.calculate("OperatingIncome", period)
        net_income = graph.calculate("NetIncome", period)

        # Margins
        gross_margin = graph.calculate("GrossProfitMargin", period)
        operating_margin = graph.calculate("OperatingMargin", period)
        net_margin = graph.calculate("NetProfitMargin", period)

        print(f"  Revenue:           ${revenue:,.0f}")
        print(f"  COGS:              ${cogs:,.0f}")
        print(f"  Gross Profit:      ${gross_profit:,.0f} ({gross_margin:.1f}%)")
        print(
            f"  Operating Income:  ${operating_income:,.0f} ({operating_margin:.1f}%)"
        )
        print(f"  Net Income:        ${net_income:,.0f} ({net_margin:.1f}%)")


def demonstrate_metrics(graph: Graph) -> None:
    """Demonstrate built-in financial metrics functionality.

    Args:
        graph: The graph with financial data.
    """
    print("\n" + "=" * 60)
    print("BUILT-IN FINANCIAL METRICS")
    print("=" * 60)

    # Show available metrics
    available_metrics = metric_registry.list_metrics()
    print(f"\nTotal available metrics: {len(available_metrics)}")
    print("Sample metrics:")
    for metric in available_metrics[:8]:
        print(f"  - {metric}")
    print("  ...")

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
    print(f"\nKey Financial Ratios for {period}:")
    print("-" * 40)

    # Current Ratio
    cr_value = graph.calculate("current_ratio", period)
    cr_metric_def = metric_registry.get("current_ratio")
    cr_analysis = interpret_metric(cr_metric_def, cr_value)

    print(f"Current Ratio: {cr_value:.2f}")
    print(f"  Rating: {cr_analysis['rating']}")
    print(f"  Analysis: {cr_analysis['interpretation_message']}")

    # Return on Assets (using direct calculation)
    data_nodes = {
        "net_income": graph.nodes["NetIncome"],
        "total_assets": graph.nodes["TotalAssets"],
    }

    roa_value = calculate_metric("return_on_assets", data_nodes, period)
    roa_metric_def = metric_registry.get("return_on_assets")
    roa_analysis = interpret_metric(roa_metric_def, roa_value)

    print(f"\nReturn on Assets: {roa_value:.1f}%")
    print(f"  Rating: {roa_analysis['rating']}")
    print(f"  Analysis: {roa_analysis['interpretation_message']}")

    # Debt to Equity Ratio
    data_nodes_de = {
        "total_debt": graph.nodes["TotalDebt"],
        "total_equity": graph.nodes["TotalEquity"],
    }

    de_value = calculate_metric("debt_to_equity_ratio", data_nodes_de, period)
    de_metric_def = metric_registry.get("debt_to_equity_ratio")
    de_analysis = interpret_metric(de_metric_def, de_value)

    print(f"\nDebt-to-Equity Ratio: {de_value:.2f}")
    print(f"  Rating: {de_analysis['rating']}")
    print(f"  Analysis: {de_analysis['interpretation_message']}")


def demonstrate_adjustments(graph: Graph) -> None:
    """Demonstrate the adjustments system for scenario analysis.

    Args:
        graph: The graph to apply adjustments to.
    """
    print("\n" + "=" * 60)
    print("ADJUSTMENTS & SCENARIO ANALYSIS")
    print("=" * 60)

    period = "2023"

    # Show base case
    base_revenue = graph.calculate("Revenue", period)
    base_operating_income = graph.calculate("OperatingIncome", period)
    base_operating_margin = graph.calculate("OperatingMargin", period)

    print(f"\nBase Case ({period}):")
    print(f"  Revenue:          ${base_revenue:,.0f}")
    print(f"  Operating Income: ${base_operating_income:,.0f}")
    print(f"  Operating Margin: {base_operating_margin:.1f}%")

    # Create bullish scenario adjustments
    print("\nCreating Bullish Scenario adjustments...")

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
    bullish_operating_margin = (bullish_operating_income / bullish_revenue) * 100

    print(f"\nBullish Scenario ({period}):")
    print(
        f"  Adjusted Revenue:          ${bullish_revenue:,.0f} (+{((bullish_revenue/base_revenue)-1)*100:.1f}%)"
    )
    print(
        f"  Adjusted Operating Expenses: ${bullish_opex:,.0f} (-{((1-(bullish_opex/graph.calculate('OperatingExpenses', period)))*100):.1f}%)"
    )
    print(f"  Adjusted Operating Income: ${bullish_operating_income:,.0f}")
    print(f"  Adjusted Operating Margin: {bullish_operating_margin:.1f}%")

    # Create bearish scenario
    print("\nCreating Bearish Scenario adjustments...")

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
    bearish_revenue = graph.get_adjusted_value(
        "Revenue", period, filter_input=bearish_filter
    )

    print("\nScenario Comparison:")
    print("-" * 30)
    print(f"  Base Case:  ${base_revenue:,.0f}")
    print(
        f"  Bullish:    ${bullish_revenue:,.0f} (+{((bullish_revenue/base_revenue)-1)*100:.1f}%)"
    )
    print(
        f"  Bearish:    ${bearish_revenue:,.0f} ({((bearish_revenue/base_revenue)-1)*100:.1f}%)"
    )

    # List all adjustments
    print(f"\nAll Adjustments ({len(graph.list_all_adjustments())} total):")
    for adj in graph.list_all_adjustments():
        print(
            f"  - {adj.node_name} ({adj.period}): {adj.type.value} {adj.value} [{adj.scenario}]"
        )
        print(f"    Reason: {adj.reason}")


def demonstrate_forecasting(graph: Graph) -> None:
    """Demonstrate basic forecasting functionality.

    Args:
        graph: The graph to forecast from.
    """
    print("\n" + "=" * 60)
    print("BASIC FORECASTING")
    print("=" * 60)

    # Create forecaster
    forecaster = StatementForecaster(graph)

    # Define forecast periods
    forecast_periods = ["2024", "2025", "2026"]

    print(f"Creating forecasts for periods: {forecast_periods}")

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
    print("\nGenerating forecasts...")
    try:
        forecaster.create_forecast(
            forecast_periods=forecast_periods, node_configs=node_configs
        )

        print("✓ Forecasts created successfully")

        # Display forecast results
        print("\nForecast Results:")
        print("-" * 40)

        # Update graph periods to include forecast periods
        all_periods = graph.periods + forecast_periods

        for period in all_periods:
            period_type = "Historical" if period in graph.periods else "Forecast"
            revenue = graph.calculate("Revenue", period)

            # Only calculate margins if we have the calculation nodes
            try:
                gross_profit = graph.calculate("GrossProfit", period)
                operating_income = graph.calculate("OperatingIncome", period)
                gross_margin = (gross_profit / revenue) * 100 if revenue != 0 else 0
                operating_margin = (
                    (operating_income / revenue) * 100 if revenue != 0 else 0
                )

                print(f"\n{period} ({period_type}):")
                print(f"  Revenue:          ${revenue:,.0f}")
                print(f"  Gross Profit:     ${gross_profit:,.0f} ({gross_margin:.1f}%)")
                print(
                    f"  Operating Income: ${operating_income:,.0f} ({operating_margin:.1f}%)"
                )

            except Exception:
                # If calculations fail for forecast periods, just show revenue
                print(f"\n{period} ({period_type}):")
                print(f"  Revenue: ${revenue:,.0f}")

        # Show growth rates
        print("\nRevenue Growth Analysis:")
        print("-" * 30)
        prev_revenue = None
        for period in all_periods:
            revenue = graph.calculate("Revenue", period)
            if prev_revenue is not None:
                growth_rate = ((revenue / prev_revenue) - 1) * 100
                print(f"  {period}: ${revenue:,.0f} ({growth_rate:+.1f}%)")
            else:
                print(f"  {period}: ${revenue:,.0f} (base)")
            prev_revenue = revenue

    except Exception as e:
        print(f"✗ Forecasting failed: {e}")
        print("This may be due to missing dependencies or configuration issues.")


def demonstrate_graph_inspection(graph: Graph) -> None:
    """Show graph inspection and analysis capabilities.

    Args:
        graph: The graph to inspect.
    """
    print("\n" + "=" * 60)
    print("GRAPH INSPECTION & ANALYSIS")
    print("=" * 60)

    print("\nGraph Overview:")
    print(f"  Total nodes: {len(graph.nodes)}")
    print(f"  Periods: {graph.periods}")

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

    print(f"  Financial Statement Items: {len(fs_items)}")
    print(f"  Calculation Nodes: {len(calculations)}")
    print(f"  Metric Nodes: {len(metrics)}")

    print("\nFinancial Statement Items:")
    for item in sorted(fs_items):
        values = graph.nodes[item].values
        latest_value = values.get(graph.periods[-1], 0)
        print(f"  - {item}: ${latest_value:,.0f} (latest)")

    print("\nCalculation Nodes:")
    for calc in sorted(calculations):
        node = graph.nodes[calc]
        if hasattr(node, "inputs") and node.inputs:
            if isinstance(node.inputs, dict):
                inputs = list(node.inputs.keys())
            else:
                inputs = [f"input_{i}" for i in range(len(node.inputs))]
        else:
            inputs = []
        print(f"  - {calc}: inputs={inputs}")

    if metrics:
        print("\nMetric Nodes:")
        for metric in sorted(metrics):
            node = graph.nodes[metric]
            print(f"  - {metric}: {node.metric_name}")

    # Show adjustments summary
    adjustments = graph.list_all_adjustments()
    if adjustments:
        print(f"\nAdjustments Summary ({len(adjustments)} total):")
        scenarios = set(adj.scenario for adj in adjustments)
        for scenario in sorted(scenarios):
            scenario_adjs = [adj for adj in adjustments if adj.scenario == scenario]
            print(f"  - {scenario}: {len(scenario_adjs)} adjustments")


def main():
    """Run the complete basic usage demonstration."""
    print("Financial Statement Model - Core Basic Usage Example")
    print("=" * 60)

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

        print("\n" + "=" * 60)
        print("✓ BASIC USAGE DEMONSTRATION COMPLETE")
        print("=" * 60)
        print("\nThis example covered:")
        print("  • Graph creation and financial statement items")
        print("  • Calculation nodes and derived metrics")
        print("  • Built-in financial metrics and interpretation")
        print("  • Adjustments and scenario analysis")
        print("  • Basic forecasting capabilities")
        print("  • Graph inspection and analysis")
        print(
            "\nFor more advanced features, see other examples in the examples/ directory."
        )

    except Exception as e:
        print(f"\n✗ Error during demonstration: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
