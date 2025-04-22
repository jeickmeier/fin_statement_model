"""FinancialStatementGraph module for statement-specific graph operations.

This module defines `FinancialStatementGraph`, which extends the core `Graph`
with mixins for statement analysis, merging, metrics, forecasting, and conversion to DataFrame.
"""

from typing import Optional
from fin_statement_model.core.graph import Graph
from fin_statement_model.preprocessing.transformation_service import (
    TransformationService,
)
from fin_statement_model.statements.mixins.analysis_mixin import AnalysisOperationsMixin
from fin_statement_model.statements.mixins.merge_mixin import MergeOperationsMixin
from fin_statement_model.statements.mixins.metrics_mixin import MetricsOperationsMixin
from fin_statement_model.statements.mixins.forecast_mixin import ForecastOperationsMixin
from fin_statement_model.io import write_data
import pandas as pd


class FinancialStatementGraph(
    Graph,
    TransformationService,
    AnalysisOperationsMixin,
    MergeOperationsMixin,
    MetricsOperationsMixin,
    ForecastOperationsMixin,
):
    """Main class for managing financial statement data and calculations.

    This class combines functionality from multiple mixins to provide a complete
    financial statement modeling solution.
    """

    def __init__(self, periods: Optional[list[str]] = None):
        """Initialize a new FinancialStatementGraph.

        Args:
            periods: Optional list of time periods to initialize the graph with.
        """
        super().__init__(periods=periods)

    @property
    def graph(self) -> Graph:
        """Alias to self for compatibility with importer expecting a graph attribute."""
        return self

    def to_dataframe(self) -> pd.DataFrame:
        """Exports the financial statement graph data to a pandas DataFrame.

        Returns:
            pd.DataFrame: A DataFrame representation of the graph's node values over periods.
        """
        return write_data(format_type="dataframe", graph=self, target=None)
