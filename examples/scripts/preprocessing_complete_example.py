#!/usr/bin/env python
"""
Complete example demonstrating the preprocessing module functionality.

This script shows all major features of the preprocessing module including:
- Normalization methods
- Time series transformations
- Period conversions
- Transformation pipelines
- Custom transformers with safe registration
- Error handling
"""

import warnings

import pandas as pd

# Configure logging before importing fin_statement_model modules
from fin_statement_model import logging_config

# Ignore warnings and set up logging with WARNING level to reduce verbosity in demos
warnings.filterwarnings("ignore")
logging_config.setup_logging(level="WARNING")

from fin_statement_model.preprocessing import (  # noqa: E402
    DataTransformer,
    TransformationService,
    TransformerFactory,
    TransformerRegistrationError,
)


def safe_register_transformer(name: str, transformer_class: type[DataTransformer]):
    """Safely register a transformer, handling re-registration gracefully."""
    try:
        if name in TransformerFactory.list_transformers():
            existing_class = TransformerFactory.get_transformer_class(name)
            if existing_class.__name__ == transformer_class.__name__:
                print(
                    f"Transformer '{name}' already registered with same class name. Skipping."
                )
                return
        TransformerFactory.register_transformer(name, transformer_class)
        print(f"Successfully registered '{name}' transformer.")
    except TransformerRegistrationError as e:
        print(f"Registration warning: {e}")
        print("Using existing registration.")


def main():
    """Run complete preprocessing examples."""
    print("=== Preprocessing Module Demo ===\n")

    # Create sample data
    quarterly_data = pd.DataFrame(
        {
            "revenue": [1000, 1100, 1200, 1300, 1400, 1450, 1500, 1600],
            "cogs": [600, 650, 700, 750, 800, 820, 850, 900],
            "opex": [200, 220, 240, 260, 280, 290, 300, 320],
            "sga": [100, 110, 120, 130, 140, 145, 150, 160],
            "r_and_d": [50, 55, 60, 65, 70, 72, 75, 80],
        },
        index=pd.date_range("2022-03-31", periods=8, freq="QE"),
    )

    print("Sample Quarterly Data:")
    print(quarterly_data.head())
    print()

    # Initialize service
    service = TransformationService()

    # 1. Normalization Examples
    print("1. NORMALIZATION EXAMPLES")
    print("-" * 50)

    # Percent of revenue
    percent_of_revenue = service.normalize_data(
        quarterly_data, normalization_type="percent_of", reference="revenue"
    )
    print("Income Statement as % of Revenue:")
    print(percent_of_revenue.head())
    print()

    # Scale to thousands
    scaled = service.normalize_data(
        quarterly_data, normalization_type="scale_by", scale_factor=0.001
    )
    print("Values in thousands:")
    print(scaled.head())
    print()

    # 2. Time Series Transformations
    print("2. TIME SERIES TRANSFORMATIONS")
    print("-" * 50)

    # Quarter-over-quarter growth
    qoq = service.transform_time_series(
        quarterly_data, transformation_type="qoq", periods=1
    )
    print("Quarter-over-Quarter Growth (%):")
    print(qoq[["revenue_qoq", "cogs_qoq"]].dropna())
    print()

    # Year-over-year growth
    yoy = service.transform_time_series(
        quarterly_data, transformation_type="yoy", periods=4
    )
    print("Year-over-Year Growth (%):")
    print(yoy[["revenue_yoy", "cogs_yoy"]].iloc[4:])
    print()

    # 3. Period Conversions
    print("3. PERIOD CONVERSIONS")
    print("-" * 50)

    # Quarterly to annual
    annual = service.convert_periods(
        quarterly_data, conversion_type="quarterly_to_annual", aggregation="sum"
    )
    print("Annual Totals:")
    print(annual)
    print()

    # TTM calculation
    ttm = service.convert_periods(
        quarterly_data, conversion_type="quarterly_to_ttm", aggregation="sum"
    )
    print("Trailing Twelve Months (from Q4):")
    print(ttm.iloc[3:])
    print()

    # 4. Custom Transformer with Safe Registration
    print("4. CUSTOM TRANSFORMER EXAMPLE")
    print("-" * 50)

    class RatioTransformer(DataTransformer):
        """Calculate financial ratios between columns."""

        def __init__(self, numerator: str, denominator: str, ratio_name: str):
            super().__init__()
            self.numerator = numerator
            self.denominator = denominator
            self.ratio_name = ratio_name

        def _transform_impl(self, data):
            df, was_series = self._coerce_to_dataframe(data)

            if self.numerator not in df.columns:
                raise ValueError(f"Numerator column '{self.numerator}' not found")
            if self.denominator not in df.columns:
                raise ValueError(f"Denominator column '{self.denominator}' not found")

            result = df.copy()
            result[self.ratio_name] = df[self.numerator] / df[self.denominator]

            if was_series:
                return result[self.ratio_name]
            return result

        def validate_input(self, data):
            return isinstance(data, (pd.DataFrame, pd.Series))

    # Safe registration
    safe_register_transformer("ratio", RatioTransformer)

    # Use the custom transformer
    ratio_calc = RatioTransformer(
        numerator="revenue", denominator="cogs", ratio_name="gross_margin_ratio"
    )

    ratio_result = ratio_calc.execute(quarterly_data)
    print("Gross Margin Ratio (Revenue/COGS):")
    print(ratio_result[["revenue", "cogs", "gross_margin_ratio"]].head())
    print()

    # 5. Transformation Pipeline
    print("5. TRANSFORMATION PIPELINE")
    print("-" * 50)

    pipeline_config = [
        {
            "name": "ratio",
            "numerator": "revenue",
            "denominator": "cogs",
            "ratio_name": "gross_margin_ratio",
        },
        {"name": "time_series", "transformation_type": "qoq", "periods": 1},
    ]

    pipeline_result = service.apply_transformation_pipeline(
        quarterly_data, pipeline_config
    )
    print("Pipeline Result - Gross Margin Ratio with QoQ Growth:")
    print(
        pipeline_result[
            ["revenue", "cogs", "gross_margin_ratio", "gross_margin_ratio_qoq"]
        ].dropna()
    )
    print()

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
