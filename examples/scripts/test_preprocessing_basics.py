#!/usr/bin/env python
"""Test script to validate preprocessing basics examples."""

import pandas as pd

# Import preprocessing modules
from fin_statement_model.preprocessing import (
    TransformationService,
    TransformerFactory,
    DataTransformer,
)
import contextlib


# Create sample data
quarterly_data = pd.DataFrame(
    {
        "revenue": [1000, 1100, 1200, 1300, 1400, 1450, 1500, 1600],
        "cogs": [600, 650, 700, 750, 800, 820, 850, 900],
        "opex": [200, 220, 240, 260, 280, 290, 300, 320],
    },
    index=pd.date_range("2022-03-31", periods=8, freq="QE"),
)


# Initialize service
service = TransformationService()

# Test 1: Normalization
percent_of_revenue = service.normalize_data(
    quarterly_data, normalization_type="percent_of", reference="revenue"
)

# Test 2: Time Series
yoy_growth = service.transform_time_series(
    quarterly_data, transformation_type="yoy", periods=4
)

# Test 3: Period Conversion
annual_data = service.convert_periods(
    quarterly_data, conversion_type="quarterly_to_annual", aggregation="sum"
)


# Test 4: Custom Transformer
class SimpleScalerTransformer(DataTransformer):
    """A simple transformer that scales numeric values by a constant factor."""

    def __init__(self, scale=1.0):
        """Create a new scaler.

        Args:
            scale: Multiplicative factor applied to each numeric value.
        """
        super().__init__({"scale": scale})
        self.scale = scale

    def _transform_impl(self, data):
        df, was_series = self._coerce_to_dataframe(data)
        result = df * self.scale
        if was_series:
            return result.iloc[:, 0]
        return result

    def validate_input(self, data):
        """Return True if *data* is a DataFrame or Series."""
        return isinstance(data, pd.DataFrame | pd.Series)


# Safe registration
with contextlib.suppress(Exception):
    TransformerFactory.register_transformer("simple_scaler", SimpleScalerTransformer)

# Test pipeline
pipeline_config = [
    {"name": "normalization", "normalization_type": "scale_by", "scale_factor": 0.001},
    {"name": "time_series", "transformation_type": "moving_avg", "window_size": 3},
]

pipeline_result = service.apply_transformation_pipeline(
    quarterly_data[["revenue"]], pipeline_config
)
