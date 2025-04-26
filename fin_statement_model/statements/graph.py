"""FinancialStatementGraph module for statement-specific graph operations.

This module defines `FinancialStatementGraph`, which extends the core `Graph`.
It provides a convenient facade for statement-related operations like forecasting
and conversion to DataFrame, leveraging the underlying core Graph capabilities.
Merging is handled by the base Graph class.
Preprocessing should be handled before data population or externally.
"""

from typing import Optional
from fin_statement_model.core.graph import Graph
from fin_statement_model.forecasting.forecaster import StatementForecaster
from fin_statement_model.io import write_data
import pandas as pd


class FinancialStatementGraph(Graph):
    """Main class for managing statement-specific financial data and calculations.

    Extends the core Graph and integrates with other services like forecasting.
    Preprocessing transformations should be applied externally.
    """

    def __init__(self, periods: Optional[list[str]] = None):
        """Initialize a new FinancialStatementGraph.

        Args:
            periods: Optional list of time periods to initialize the graph with.
        """
        super().__init__(periods=periods)
        # Facade services for statement-specific operations
        # Initialize forecaster (depends on self, so initialized here)
        self.forecaster: StatementForecaster = StatementForecaster(self)

    def to_dataframe(self) -> pd.DataFrame:
        """Exports the financial statement graph data to a pandas DataFrame.

        Returns:
            pd.DataFrame: A DataFrame representation of the graph's node values over periods.
        """
        return write_data(format_type="dataframe", graph=self, target=None)
