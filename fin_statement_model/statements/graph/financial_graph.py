"""FinancialStatementGraph module for statement-specific graph operations.

This module defines `FinancialStatementGraph`, which extends the core `Graph`
with mixins for statement analysis, merging, metrics, forecasting, and conversion to DataFrame.
"""

from typing import Optional
from fin_statement_model.core.graph import Graph
from fin_statement_model.preprocessing.transformation_service import (
    TransformationService,
)
from fin_statement_model.statements.forecasting.forecaster import StatementForecaster
from fin_statement_model.statements.merging.merger import StatementMerger
from fin_statement_model.io import write_data
import pandas as pd


class FinancialStatementGraph(Graph):
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
        # Facade services for statement-specific operations
        self.transformer: TransformationService = TransformationService()
        self.forecaster: StatementForecaster = StatementForecaster(self)
        self.merger: StatementMerger = StatementMerger(self)

    def to_dataframe(self) -> pd.DataFrame:
        """Exports the financial statement graph data to a pandas DataFrame.

        Returns:
            pd.DataFrame: A DataFrame representation of the graph's node values over periods.
        """
        return write_data(format_type="dataframe", graph=self, target=None)
