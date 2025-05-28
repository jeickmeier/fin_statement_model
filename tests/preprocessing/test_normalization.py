"""Tests for the NormalizationTransformer."""

import numpy as np
import pandas as pd
import pytest

from fin_statement_model.preprocessing.transformers.normalization import (
    NormalizationTransformer,
)
from fin_statement_model.preprocessing.config.enums import NormalizationType


class TestNormalizationTransformer:
    """Test cases for NormalizationTransformer."""

    def test_percent_of_with_zero_reference(self):
        """Test percent_of normalization handles zero reference values correctly."""
        # Create test data with zero reference values
        df = pd.DataFrame(
            {
                "revenue": [0, 100, 0, 200],
                "costs": [50, 60, 70, 80],
                "profit": [10, 20, 30, 40],
            }
        )

        transformer = NormalizationTransformer(
            normalization_type=NormalizationType.PERCENT_OF, reference="revenue"
        )

        result = transformer.transform(df)

        # Check that rows with zero reference become NaN
        assert pd.isna(result.loc[0, "costs"])
        assert pd.isna(result.loc[0, "profit"])
        assert pd.isna(result.loc[2, "costs"])
        assert pd.isna(result.loc[2, "profit"])

        # Check that rows with non-zero reference are calculated correctly
        assert result.loc[1, "costs"] == 60.0  # 60/100 * 100
        assert result.loc[1, "profit"] == 20.0  # 20/100 * 100
        assert result.loc[3, "costs"] == 40.0  # 80/200 * 100
        assert result.loc[3, "profit"] == 20.0  # 40/200 * 100

    def test_minmax_with_constant_column(self):
        """Test minmax normalization handles constant columns correctly."""
        df = pd.DataFrame({"constant": [5, 5, 5, 5], "variable": [1, 2, 3, 4]})

        transformer = NormalizationTransformer(
            normalization_type=NormalizationType.MINMAX
        )

        result = transformer.transform(df)

        # Constant column should become all zeros
        assert all(result["constant"] == 0.0)

        # Variable column should be normalized to [0, 1]
        assert result["variable"].min() == 0.0
        assert result["variable"].max() == 1.0

    def test_standard_with_constant_column(self):
        """Test standard normalization handles constant columns correctly."""
        df = pd.DataFrame({"constant": [10, 10, 10, 10], "variable": [1, 2, 3, 4]})

        transformer = NormalizationTransformer(
            normalization_type=NormalizationType.STANDARD
        )

        result = transformer.transform(df)

        # Constant column should become all zeros
        assert all(result["constant"] == 0.0)

        # Variable column should have mean 0 and std 1
        assert abs(result["variable"].mean()) < 1e-10
        assert abs(result["variable"].std() - 1.0) < 1e-10
