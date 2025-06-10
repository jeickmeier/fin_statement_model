"""Data reader for pandas DataFrames."""

import logging
import pandas as pd
import numpy as np
from typing import Optional, Any

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io.core.base import DataReader
from fin_statement_model.io.core.registry import register_reader
from fin_statement_model.io.exceptions import ReadError
from fin_statement_model.io.config.models import DataFrameReaderConfig

logger = logging.getLogger(__name__)


@register_reader("dataframe", schema=DataFrameReaderConfig)
class DataFrameReader(DataReader):
    """Reads data from a pandas DataFrame into a Graph.

    Assumes the DataFrame index contains node names and columns contain periods.
    Values should be numeric.
    """

    def __init__(self, cfg: Optional[DataFrameReaderConfig] = None) -> None:
        """Initialize the DataFrameReader.

        Args:
            cfg: Optional validated `DataFrameReaderConfig` instance.
                 Currently unused but kept for registry symmetry and future options.
        """
        self.cfg = cfg  # For future use; currently no configuration options.

    def read(self, source: pd.DataFrame, **kwargs: Any) -> Graph:
        """Read data from a pandas DataFrame into a new Graph.

        Assumes DataFrame index = node names, columns = periods.

        Args:
            source (pd.DataFrame): The DataFrame to read data from.
            **kwargs: Optional runtime argument overriding config defaults:
                periods (list[str], optional): List of periods (columns) to include. Overrides `cfg.periods`.

        Returns:
            A new Graph instance populated with FinancialStatementItemNodes.

        Raises:
            ReadError: If the source is not a DataFrame or has invalid structure.
        """
        df = source
        logger.info("Starting import from DataFrame.")

        # --- Validate Inputs ---
        if not isinstance(df, pd.DataFrame):
            raise ReadError(
                "Source is not a pandas DataFrame.",
                source="DataFrame",
                reader_type="DataFrameReader",
            )

        if df.index.name is None and df.index.empty:
            logger.warning(
                "DataFrame index is unnamed and empty, assuming columns are nodes if periods kwarg is provided."
            )
            # Handle case where DF might be oriented differently if periods kwarg is present?
            # For now, stick to index=nodes assumption.

        # Determine periods: runtime kwargs override config, else config defaults, else infer
        graph_periods_arg = kwargs.get(
            "periods", self.cfg.periods if self.cfg else None
        )
        if graph_periods_arg:
            if not isinstance(graph_periods_arg, list):
                raise ReadError("'periods' argument must be a list of column names.")
            missing_cols = [p for p in graph_periods_arg if p not in df.columns]
            if missing_cols:
                raise ReadError(
                    f"Specified periods (columns) not found in DataFrame: {missing_cols}"
                )
            graph_periods = sorted(graph_periods_arg)
            df_subset = df[graph_periods]  # Select only specified period columns
        else:
            # No explicit periods provided; infer from columns
            graph_periods = sorted(df.columns.astype(str).tolist())
            df_subset = df

        if not graph_periods:
            raise ReadError(
                "No periods identified in DataFrame columns.",
                source="DataFrame",
                reader_type="DataFrameReader",
            )

        logger.info(f"Using periods (columns): {graph_periods}")
        graph = Graph(periods=graph_periods)

        # --- Populate Graph ---
        validation_errors = []
        nodes_added = 0
        for node_name_df, row in df_subset.iterrows():
            if pd.isna(node_name_df) or not node_name_df:
                logger.debug("Skipping row with empty index name.")
                continue

            node_name = str(node_name_df).strip()
            period_values: dict[str, float] = {}
            for period in graph_periods:
                value = row[period]
                if pd.isna(value):
                    continue  # Skip NaN values

                if not isinstance(value, int | float | np.number):
                    try:
                        value = float(value)
                        logger.warning(
                            f"Converted non-numeric value '{row[period]}' to float for node '{node_name}' period '{period}'"
                        )
                    except (ValueError, TypeError):
                        validation_errors.append(
                            f"Node '{node_name}': Non-numeric value '{value}' for period '{period}'"
                        )
                        continue  # Skip invalid value

                period_values[period] = float(value)

            if period_values:
                if graph.has_node(node_name):
                    logger.warning(
                        f"Node '{node_name}' already exists. Overwriting data is not standard for readers."
                    )
                    # Update existing? Log for now.
                else:
                    new_node = FinancialStatementItemNode(
                        name=node_name, values=period_values
                    )
                    graph.add_node(new_node)
                    nodes_added += 1

        if validation_errors:
            raise ReadError(
                f"Validation errors occurred while reading DataFrame: {'; '.join(validation_errors)}",
                source="DataFrame",
                reader_type="DataFrameReader",
            )

        logger.info(
            f"Successfully created graph with {nodes_added} nodes from DataFrame."
        )
        return graph

        # No specific file operations, so less need for broad Exception catch
        # Specific errors handled above (TypeError, ValueError from float conversion)
