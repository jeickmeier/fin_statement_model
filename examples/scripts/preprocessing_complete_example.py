#!/usr/bin/env python
"""Complete example demonstrating the preprocessing module functionality.

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

from fin_statement_model.preprocessing import (
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
                return
        TransformerFactory.register_transformer(name, transformer_class)
    except TransformerRegistrationError:
        pass


def main():
    """Run complete preprocessing examples."""
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

    # Initialize service
    service = TransformationService()

    # 1. Normalization Examples

    # Percent of revenue
    service.normalize_data(
        quarterly_data, normalization_type="percent_of", reference="revenue"
    )

    # Scale to thousands
    service.normalize_data(
        quarterly_data, normalization_type="scale_by", scale_factor=0.001
    )

    # 2. Time Series Transformations

    # Quarter-over-quarter growth
    service.transform_time_series(quarterly_data, transformation_type="qoq", periods=1)

    # Year-over-year growth
    service.transform_time_series(quarterly_data, transformation_type="yoy", periods=4)

    # 3. Period Conversions

    # Quarterly to annual
    service.convert_periods(
        quarterly_data, conversion_type="quarterly_to_annual", aggregation="sum"
    )

    # TTM calculation
    service.convert_periods(
        quarterly_data, conversion_type="quarterly_to_ttm", aggregation="sum"
    )

    # 4. Custom Transformer with Safe Registration

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
            return isinstance(data, pd.DataFrame | pd.Series)

    # Safe registration
    safe_register_transformer("ratio", RatioTransformer)

    # Use the custom transformer
    ratio_calc = RatioTransformer(
        numerator="revenue", denominator="cogs", ratio_name="gross_margin_ratio"
    )

    ratio_calc.execute(quarterly_data)

    # 5. Transformation Pipeline

    pipeline_config = [
        {
            "name": "ratio",
            "numerator": "revenue",
            "denominator": "cogs",
            "ratio_name": "gross_margin_ratio",
        },
        {"name": "time_series", "transformation_type": "qoq", "periods": 1},
    ]

    service.apply_transformation_pipeline(quarterly_data, pipeline_config)


if __name__ == "__main__":
    main()
