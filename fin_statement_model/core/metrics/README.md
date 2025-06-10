# Metrics Module

Provide a comprehensive overview of the `fin_statement_model.core.metrics` package for loading, calculating, and interpreting financial metrics defined in YAML files.

## Overview

The `core/metrics` package includes:

- **MetricDefinition**: Pydantic model representing a metric loaded from YAML.
- **MetricRegistry**: Class to load, validate, and retrieve definitions.
- **metric_registry**: Singleton instance of `MetricRegistry`.
- **calculate_metric**: Helper function to compute a metric value by name.
- **MetricInterpreter** and **interpret_metric**: Utilities to rate and explain metric values based on interpretation guidelines.

Metrics are organized in `core/metrics/metric_defn/` by category, such as:

- Liquidity
- Leverage
- Profitability
- Efficiency
- Valuation
- Cash Flow
- Growth
- Credit Risk
- Advanced Analytics (e.g., DuPont)
- Special Calculations (e.g., Gross Profit, Net Income)
- Real Estate Metrics
- Per-Share Metrics

## Basic Usage

```python
from fin_statement_model.core.metrics import (
    metric_registry,
    calculate_metric,
    interpret_metric,
)

# (Re)load metrics from disk (auto-loaded on import)
count = metric_registry.load_metrics_from_directory(
    "fin_statement_model/core/metrics/metric_defn"
)
print(f"Loaded {count} metrics")

# List available metric IDs
print(metric_registry.list_metrics())

# Prepare data nodes (e.g., from your statement graph)
# data_nodes = { 'revenue': RevenueNode(...), 'total_assets': AssetNode(...), ... }

# Calculate a metric
value = calculate_metric(
    "current_ratio", data_nodes, period="2023"
)
print(f"Current Ratio for 2023: {value:.2f}")

# Interpret the result
metric_def = metric_registry.get("current_ratio")
analysis = interpret_metric(metric_def, value)
print(analysis)
```

## Available Metric Categories

Metrics are grouped into the following logical categories:

| Category         | Description                                        |
|------------------|----------------------------------------------------|
| Liquidity        | Current ratio, quick ratio, cash coverage          |
| Leverage         | Debt ratios, coverage, capital structure           |
| Profitability    | Margins, ROA, ROE, ROC                             |
| Efficiency       | Asset & working capital turnover                   |
| Valuation        | Price multiples, EV ratios, yield metrics          |
| Cash Flow        | Operating cash flow, free cash flow, quality       |
| Growth           | Year-over-year growth rates                        |
| Credit Risk      | Altman Z-scores, warning flags                     |
| Advanced         | DuPont analysis, decompositions                    |
| Special          | Calculated items like gross/net profit             |
| Real Estate      | NOI, FFO, cap rates, debt yield                    |
| Per-Share        | Per-share metrics (EPS, FCF/share, NAV/share)      |

## Adding a New Metric Definition

To add a custom metric:

1. Create a new YAML file under `core/metrics/metric_defn/` (or within a subfolder).
2. Follow the schema:

   ```yaml
   - name: My Custom Metric
     description: Description of this metric.
     inputs:
       - input1
       - input2
     formula: input1 / input2
     tags:
       - custom
       - example
     units: ratio
     category: custom
     related_metrics:
       - existing_metric
     interpretation:
       good_range: [0.8, 1.2]
       warning_below: 0.5
       warning_above: 1.5
       excellent_above: 1.2
       poor_below: 0.5
       notes: 'Any additional context or guidance'
   ```

3. Reload the registry (or restart the application):

   ```python
   metric_registry.load_metrics_from_directory(
       "fin_statement_model/core/metrics/metric_defn"
   )
   ```

4. Use `calculate_metric` and `interpret_metric` as demonstrated above. 