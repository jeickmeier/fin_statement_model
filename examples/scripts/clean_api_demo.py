#!/usr/bin/env python3
"""Minimal modern API demonstration."""

import logging
from fin_statement_model.io import read_data
from fin_statement_model.core.nodes import FixedGrowthForecastNode


def main():
    logging.basicConfig(level=logging.INFO)
    # Sample data: map of node names to period values
    data = {"revenue": {"2021": 100_000_000, "2022": 110_000_000}}

    # 1. Read data into a graph from a simple dict
    graph = read_data(format_type="dict", source=data)

    # 2. Forecast next periods using default growth rate from config
    revenue_node = graph.get_node("revenue")
    forecast = FixedGrowthForecastNode(
        revenue_node,
        last_period="2022",
        forecast_periods=["2023", "2024"],
    )

    # 3. Display forecast results
    print(f"Default growth rate: {forecast.growth_rate:.0%}")
    for period in ["2023", "2024"]:
        print(f"Forecast for {period}: {forecast.calculate(period):,.0f}")


if __name__ == "__main__":
    main()
