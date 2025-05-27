"""Examples of metric interpretation functionality.

This module demonstrates how to use the enhanced metric definitions
with interpretation guidelines.
"""

from fin_statement_model.core.metrics import (
    metric_registry,
    MetricInterpreter,
    interpret_metric,
    MetricRating,
)


def example_basic_interpretation():
    """Example: Basic metric interpretation."""
    print("=== Basic Metric Interpretation Example ===")

    # Get a metric definition (use metric ID, not name)
    current_ratio_def = metric_registry.get("current_ratio")
    if not current_ratio_def:
        print("Current Ratio metric not found!")
        return

    # Test different values
    test_values = [0.5, 0.9, 1.2, 2.0, 2.8, 5.0]

    print(f"\nMetric: {current_ratio_def.name}")
    print(f"Description: {current_ratio_def.description}")
    print(f"Category: {current_ratio_def.category}")
    print("\nValue Interpretations:")
    print("-" * 60)

    interpreter = MetricInterpreter(current_ratio_def)

    for value in test_values:
        rating = interpreter.rate_value(value)
        message = interpreter.get_interpretation_message(value)
        print(f"{value:4.1f} | {rating.value:10} | {message}")


def example_detailed_analysis():
    """Example: Detailed metric analysis."""
    print("\n=== Detailed Analysis Example ===")

    # Get debt-to-equity ratio metric
    debt_equity_def = metric_registry.get("debt_to_equity_ratio")
    if not debt_equity_def:
        print("Debt-to-Equity Ratio metric not found!")
        return

    # Analyze a specific value
    test_value = 0.8

    analysis = interpret_metric(debt_equity_def, test_value)

    print(f"\nDetailed Analysis for {debt_equity_def.name}:")
    print(f"Value: {analysis['value']}")
    print(f"Rating: {analysis['rating']}")
    print(f"Category: {analysis['category']}")
    print(f"Units: {analysis['units']}")
    print(f"\nInterpretation: {analysis['interpretation_message']}")

    if "guidelines" in analysis:
        guidelines = analysis["guidelines"]
        print("\nGuidelines:")
        if guidelines["good_range"]:
            print(f"  Good range: {guidelines['good_range']}")
        if guidelines["warning_above"]:
            print(f"  Warning above: {guidelines['warning_above']}")
        if guidelines["excellent_above"]:
            print(f"  Excellent above: {guidelines['excellent_above']}")

    if "related_metrics" in analysis:
        print(f"\nRelated Metrics: {', '.join(analysis['related_metrics'])}")

    if "notes" in analysis:
        print(f"\nNotes:\n{analysis['notes']}")


def example_multiple_metrics_analysis():
    """Example: Analyzing multiple metrics together."""
    print("\n=== Multiple Metrics Analysis Example ===")

    # Company financial data
    company_data = {
        "current_assets": 500_000,
        "current_liabilities": 300_000,
        "total_debt": 800_000,
        "total_equity": 1_200_000,
        "net_income": 180_000,
        "ebit": 250_000,
        "interest_expense": 40_000,
    }

    # Calculate and interpret multiple metrics (use metric IDs)
    metrics_to_analyze = [
        (
            "current_ratio",
            company_data["current_assets"] / company_data["current_liabilities"],
        ),
        (
            "debt_to_equity_ratio",
            company_data["total_debt"] / company_data["total_equity"],
        ),
        (
            "return_on_equity",
            (company_data["net_income"] / company_data["total_equity"]) * 100,
        ),
        (
            "times_interest_earned",
            company_data["ebit"] / company_data["interest_expense"],
        ),
    ]

    print("\nFinancial Analysis:")
    print("=" * 60)

    for metric_id, calculated_value in metrics_to_analyze:
        try:
            metric_def = metric_registry.get(metric_id)
        except KeyError:
            print(f"Metric '{metric_id}' not found!")
            continue

        interpreter = MetricInterpreter(metric_def)
        rating = interpreter.rate_value(calculated_value)
        message = interpreter.get_interpretation_message(calculated_value)

        print(f"\n{metric_def.name}:")
        print(f"  Value: {calculated_value:.2f} {metric_def.units or ''}")
        print(f"  Rating: {rating.value.upper()}")
        print(f"  {message}")


def example_rating_summary():
    """Example: Summary of ratings across metrics."""
    print("\n=== Rating Summary Example ===")

    # Sample metric values (use metric IDs)
    metric_values = {
        "current_ratio": 2.1,
        "debt_to_equity_ratio": 0.45,
        "return_on_equity": 16.5,
        "times_interest_earned": 7.2,
    }

    ratings_summary = {}

    print("\nCredit Analysis Summary:")
    print("-" * 40)

    for metric_id, value in metric_values.items():
        try:
            metric_def = metric_registry.get(metric_id)
        except KeyError:
            print(f"Metric '{metric_id}' not found!")
            continue

        interpreter = MetricInterpreter(metric_def)
        rating = interpreter.rate_value(value)
        category = metric_def.category or "other"
        if category not in ratings_summary:
            ratings_summary[category] = []
        ratings_summary[category].append((metric_def.name, rating, value))

    # Group by category
    for category, metrics in ratings_summary.items():
        print(f"\n{category.upper()} METRICS:")
        for metric_name, rating, value in metrics:
            status_icon = {
                MetricRating.EXCELLENT: "🟢",
                MetricRating.GOOD: "🟢",
                MetricRating.ADEQUATE: "🟡",
                MetricRating.WARNING: "🟠",
                MetricRating.POOR: "🔴",
                MetricRating.UNKNOWN: "⚪",
            }
            print(f"  {status_icon[rating]} {metric_name}: {rating.value} ({value})")

    # Overall assessment
    all_ratings = [rating for _, metrics in ratings_summary.items() for _, rating, _ in metrics]
    excellent_count = sum(1 for r in all_ratings if r == MetricRating.EXCELLENT)
    good_count = sum(1 for r in all_ratings if r == MetricRating.GOOD)
    warning_count = sum(1 for r in all_ratings if r in [MetricRating.WARNING, MetricRating.POOR])

    print("\nOVERALL ASSESSMENT:")
    if warning_count == 0 and (excellent_count + good_count) >= len(all_ratings) * 0.8:
        print("🟢 STRONG - Good financial health across key metrics")
    elif warning_count <= 1:
        print("🟡 MODERATE - Generally healthy with some areas for improvement")
    else:
        print("🔴 WEAK - Multiple areas of concern requiring attention")


def example_threshold_analysis():
    """Example: Understanding metric thresholds and ranges."""
    print("\n=== Threshold Analysis Example ===")

    # Get current ratio metric
    current_ratio_def = metric_registry.get("current_ratio")
    if not current_ratio_def:
        print("Current Ratio metric not found!")
        return

    interpreter = MetricInterpreter(current_ratio_def)

    print(f"\nThreshold Analysis for {current_ratio_def.name}:")
    print("-" * 50)

    # Test values around thresholds
    test_values = [0.7, 0.8, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]

    for value in test_values:
        rating = interpreter.rate_value(value)
        analysis = interpreter.get_detailed_analysis(value)

        print(f"\nValue: {value:.1f}")
        print(f"  Rating: {rating.value}")
        print(f"  Message: {analysis['interpretation_message']}")

        # Show which threshold was triggered
        if rating == MetricRating.POOR:
            print(f"  → Below poor threshold ({analysis['guidelines']['poor_below']})")
        elif rating == MetricRating.WARNING:
            if value < analysis["guidelines"]["warning_below"]:
                print(f"  → Below warning threshold ({analysis['guidelines']['warning_below']})")
            elif value > analysis["guidelines"]["warning_above"]:
                print(f"  → Above warning threshold ({analysis['guidelines']['warning_above']})")
        elif rating == MetricRating.EXCELLENT:
            print(f"  → Above excellent threshold ({analysis['guidelines']['excellent_above']})")
        elif rating == MetricRating.GOOD:
            good_range = analysis["guidelines"]["good_range"]
            print(f"  → Within good range ({good_range[0]} - {good_range[1]})")


if __name__ == "__main__":
    # Run all examples
    example_basic_interpretation()
    example_detailed_analysis()
    example_multiple_metrics_analysis()
    example_rating_summary()
    example_threshold_analysis()
