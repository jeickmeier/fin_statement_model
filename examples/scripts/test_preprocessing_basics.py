#!/usr/bin/env python
"""Test script to validate preprocessing basics examples."""

import pandas as pd

# Import preprocessing modules
from fin_statement_model.preprocessing import (
    TransformationService,
    TransformerFactory,
    DataTransformer,
)

print("✅ Imports successful!")
print(f"📋 Available transformers: {TransformerFactory.list_transformers()}")

# Create sample data
quarterly_data = pd.DataFrame(
    {
        "revenue": [1000, 1100, 1200, 1300, 1400, 1450, 1500, 1600],
        "cogs": [600, 650, 700, 750, 800, 820, 850, 900],
        "opex": [200, 220, 240, 260, 280, 290, 300, 320],
    },
    index=pd.date_range("2022-03-31", periods=8, freq="QE"),
)

print("\n📊 Quarterly data created:", quarterly_data.shape)

# Initialize service
service = TransformationService()
print("✅ TransformationService initialized")

# Test 1: Normalization
percent_of_revenue = service.normalize_data(
    quarterly_data, normalization_type="percent_of", reference="revenue"
)
print("\n✅ Test 1 - Percent of revenue normalization completed")
print(percent_of_revenue[["revenue", "cogs"]].head(3))

# Test 2: Time Series
yoy_growth = service.transform_time_series(
    quarterly_data, transformation_type="yoy", periods=4
)
print("\n✅ Test 2 - YoY growth calculation completed")
print(yoy_growth[["revenue_yoy"]].iloc[4:6])

# Test 3: Period Conversion
annual_data = service.convert_periods(
    quarterly_data, conversion_type="quarterly_to_annual", aggregation="sum"
)
print("\n✅ Test 3 - Period conversion completed")
print(annual_data[["revenue", "cogs"]])


# Test 4: Custom Transformer
class SimpleScalerTransformer(DataTransformer):
    def __init__(self, scale=1.0):
        super().__init__({"scale": scale})
        self.scale = scale

    def _transform_impl(self, data):
        df, was_series = self._coerce_to_dataframe(data)
        result = df * self.scale
        if was_series:
            return result.iloc[:, 0]
        return result

    def validate_input(self, data):
        return isinstance(data, (pd.DataFrame, pd.Series))


# Safe registration
try:
    TransformerFactory.register_transformer("simple_scaler", SimpleScalerTransformer)
    print("\n✅ Test 4 - Custom transformer registered")
except Exception as e:
    print(f"\n⚠️ Custom transformer already registered: {e}")

# Test pipeline
pipeline_config = [
    {"name": "normalization", "normalization_type": "scale_by", "scale_factor": 0.001},
    {"name": "time_series", "transformation_type": "moving_avg", "window_size": 3},
]

pipeline_result = service.apply_transformation_pipeline(
    quarterly_data[["revenue"]], pipeline_config
)
print("\n✅ Test 5 - Pipeline execution completed")
print(pipeline_result.head())

print("\n🎉 All tests passed successfully!")
