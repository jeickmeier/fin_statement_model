"""Data writer for Excel files."""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.base import DataWriter
from fin_statement_model.io.registry import register_writer
from fin_statement_model.io.exceptions import WriteError

logger = logging.getLogger(__name__)


@register_writer("excel")
class ExcelWriter(DataWriter):
    """Writes graph data to an Excel file.

    Converts the graph data to a pandas DataFrame first, then writes to Excel.
    """

    def _graph_to_dataframe(self, graph: Graph, recalculate: bool = True) -> pd.DataFrame:
        """Convert the graph data to a pandas DataFrame.

        Internal helper method adapted from exporters.dataframe.

        Args:
            graph: The Graph instance to export.
            recalculate: Whether to recalculate all nodes before conversion.

        Returns:
            pd.DataFrame: DataFrame with node names as index and periods as columns.
        """
        if recalculate:
            try:
                if graph.periods:  # Only recalculate if graph has periods defined
                    graph.recalculate_all(periods=graph.periods)
                    logger.info(
                        "Recalculated graph before converting to DataFrame for Excel export."
                    )
                else:
                    logger.warning("Graph has no periods defined, skipping recalculation.")
            except Exception as e:
                logger.error(f"Error during recalculation for Excel export: {e}", exc_info=True)
                logger.warning("Proceeding to export Excel without successful recalculation.")

        periods = sorted(graph.periods) if graph.periods else []
        data: dict[str, dict[str, float]] = {}

        for node_id, node in graph.nodes.items():
            row: dict[str, float] = {}
            for period in periods:
                value = np.nan  # Default to NaN
                try:
                    # Prioritize calculated value
                    if hasattr(node, "calculate") and callable(node.calculate):
                        value = node.calculate(period)
                    # Fallback to stored values
                    elif (
                        hasattr(node, "values")
                        and isinstance(node.values, dict)
                        and period in node.values
                    ):
                        value = node.values.get(period, np.nan)

                    if not isinstance(value, (int, float, np.number)) or not np.isfinite(value):
                        value = np.nan  # Ensure non-numeric/infinite become NaN

                except Exception as e:
                    logger.debug(
                        f"Could not get value for node '{node_id}' period '{period}' for Excel export: {e}"
                    )
                    value = np.nan
                row[period] = float(value)  # Ensure float type, handles NaN
            data[node_id] = row

        df = pd.DataFrame.from_dict(data, orient="index", columns=periods)
        df.index.name = "node_name"
        return df

    def write(self, graph: Graph, target: str, **kwargs: dict[str, Any]) -> None:
        """Write data from the Graph object to an Excel file.

        Args:
            graph: The Graph object containing the data to write.
            target (str): Path to the target Excel file.
            **kwargs: Optional keyword arguments:
                sheet_name (str): Name of the sheet to write to (default: "Sheet1").
                recalculate (bool): Recalculate graph before export (default: True).
                include_nodes (list[str]): Optional list of node names to include.
                excel_writer_kwargs (dict): Additional kwargs passed directly to
                                            pandas.DataFrame.to_excel().

        Raises:
            WriteError: If an error occurs during the writing process.
        """
        file_path = target
        sheet_name = kwargs.get("sheet_name", "Sheet1")
        recalculate = kwargs.get("recalculate", True)
        include_nodes = kwargs.get("include_nodes")
        excel_writer_options = kwargs.get("excel_writer_kwargs", {})

        logger.info(f"Exporting graph to Excel file: {file_path}, sheet: {sheet_name}")

        try:
            # 1. Convert graph to DataFrame
            df = self._graph_to_dataframe(graph, recalculate=recalculate)

            # 2. Filter nodes if requested
            if include_nodes:
                if not isinstance(include_nodes, list):
                    logger.warning("'include_nodes' provided but is not a list. Ignoring filter.")
                else:
                    missing_nodes = [n for n in include_nodes if n not in df.index]
                    if missing_nodes:
                        logger.warning(
                            f"Nodes specified in include_nodes not found in graph data: {missing_nodes}"
                        )
                    nodes_to_keep = [n for n in include_nodes if n in df.index]
                    if not nodes_to_keep:
                        logger.warning(
                            "No nodes left to export after filtering with include_nodes."
                        )
                        df = pd.DataFrame()  # Write empty DataFrame
                    else:
                        df = df.loc[nodes_to_keep]

            # 3. Write DataFrame to Excel
            output_path = Path(file_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            df.to_excel(
                output_path,
                sheet_name=sheet_name,
                index=True,  # Keep node names as index column
                **excel_writer_options,
            )
            logger.info(f"Successfully exported graph to {file_path}, sheet '{sheet_name}'")

        except Exception as e:
            logger.error(
                f"Failed to export graph to Excel file '{file_path}': {e}",
                exc_info=True,
            )
            raise WriteError(
                message=f"Failed to export graph to Excel: {e}",
                target=file_path,
                writer_type="ExcelWriter",
                original_error=e,
            ) from e
