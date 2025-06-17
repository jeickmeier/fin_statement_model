# Metrics Module

A comprehensive system for defining, calculating, and interpreting financial metrics in the `fin_statement_model` library.

## Overview

The `core/metrics` package provides:

- **MetricDefinition**: Pydantic model representing a metric loaded from YAML.
- **MetricRegistry**: Class to load, validate, and retrieve metric definitions.
- **metric_registry**: Singleton instance of `MetricRegistry` for global access.
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

### Loading Metrics

```python
from fin_statement_model.core.metrics import metric_registry

# (Re)load metrics from disk (auto-loaded on import)
count = metric_registry.load_metrics_from_directory(
    "fin_statement_model/core/metrics/metric_defn"
)
print(f"Loaded {count} metrics")
```

### Listing Available Metrics

```python
print(metric_registry.list_metrics())
```

### Calculating a Metric

```python
from fin_statement_model.core.metrics import calculate_metric

# Prepare data nodes (e.g., from your statement graph)
# data_nodes = { 'revenue': RevenueNode(...), 'total_assets': AssetNode(...), ... }

value = calculate_metric(
    "current_ratio", data_nodes, period="2023"
)
print(f"Current Ratio for 2023: {value:.2f}")
```

### Interpreting a Metric

```python
from fin_statement_model.core.metrics import interpret_metric

metric_def = metric_registry.get("current_ratio")
analysis = interpret_metric(metric_def, value)
print(analysis)
# Example output:
# {'value': 1.8, 'rating': 'good', 'metric_name': 'Current Ratio', ...}
```

## Advanced Features

### Metric Interpretation and Analysis

The `MetricInterpreter` class and `interpret_metric` function provide detailed analysis and human-readable messages for metric values, using guidelines defined in the YAML files.

```python
from fin_statement_model.core.metrics import MetricInterpreter

metric_def = metric_registry.get("current_ratio")
interpreter = MetricInterpreter(metric_def)
print(interpreter.get_interpretation_message(1.8))  # 'Good performance: 1.80'
print(interpreter.get_detailed_analysis(1.8))
```

### Adding a New Metric Definition

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

### Extending the Registry in Python

You can register metrics programmatically using the `register_definition` method:

```python
from fin_statement_model.core.metrics.models import MetricDefinition
from fin_statement_model.core.metrics.registry import metric_registry

defn = MetricDefinition(
    name="Custom Ratio",
    description="A custom ratio for demonstration.",
    inputs=["a", "b"],
    formula="a / b",
    tags=["custom"],
    units="ratio",
    category="custom"
)
metric_registry.register_definition(defn)
```

### Custom Interpretation

You can provide custom interpretation logic by subclassing `MetricInterpreter` or by providing additional fields in the YAML under `interpretation`.

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

## Error Handling

- All exceptions related to metric calculation or registry access are subclasses of `FinStatementModelError`.
- If a metric is not found, a `KeyError` is raised with available metric suggestions.
- If required input nodes are missing, a `ValueError` is raised.

## See Also

- [Node and Calculation Engine documentation](../nodes/)
- [Metric YAML schema and examples](metric_defn/)
- [Extending the registry in Python](#extending-the-registry-in-python)

---

This documentation reflects the latest features and extensibility of the metrics system in the `fin_statement_model` library. For more details, see the code docstrings and examples in the source files. 