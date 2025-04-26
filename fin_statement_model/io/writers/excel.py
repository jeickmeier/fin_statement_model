"""Data writer for Excel files."""

import logging
from pathlib import Path
from typing import Any


from fin_statement_model.core.graph import Graph
from fin_statement_model.io.base import DataWriter
from fin_statement_model.io.registry import register_writer
from fin_statement_model.io.exceptions import WriteError
from fin_statement_model.io.writers.dataframe import DataFrameWriter

logger = logging.getLogger(__name__)


@register_writer("excel")
class ExcelWriter(DataWriter):
    """Writes graph data to an Excel file.

    Converts the graph data to a pandas DataFrame first, then writes to an Excel file.

    Note:
        When using the `write_data` facade, writer initialization has no specific kwargs,
        and writer-specific options (`sheet_name`, `recalculate`, `include_nodes`,
        `excel_writer_kwargs`) should be passed to the `write()` method. Direct
        instantiation of `ExcelWriter` is also supported.
    """

    def write(self, graph: Graph, target: str, **kwargs: dict[str, Any]) -> None:
        """Write data from the Graph object to an Excel file.

        Args:
            graph (Graph): The Graph object containing the data to write.
            target (str): Path to the target Excel file.
            **kwargs: Writer-specific keyword arguments:
                sheet_name (str): Name of the sheet to write to (default: "Sheet1").
                recalculate (bool): Recalculate graph before export (default: True).
                include_nodes (list[str]): Optional list of node names to include.
                excel_writer_kwargs (dict): Additional args passed directly to
                    `pandas.DataFrame.to_excel()`.

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
            # 1. Convert graph to DataFrame using DataFrameWriter
            df_writer = DataFrameWriter()
            df = df_writer.write(graph=graph, target=None, recalculate=recalculate, include_nodes=include_nodes)

            # 2. Write DataFrame to Excel
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
