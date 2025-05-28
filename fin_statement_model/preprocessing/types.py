"""Define types and TypedDicts for preprocessing transformers.

This module provides a TabularData alias (pd.DataFrame only) and configuration TypedDicts.
"""

import pandas as pd

# Alias for tabular data inputs (DataFrame-only) accepted by transformers
TabularData = pd.DataFrame
