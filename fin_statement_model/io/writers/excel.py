"""Data writer for Excel files."""

import logging
from pathlib import Path
from typing import Any, Optional

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.base import DataWriter
from fin_statement_model.io.registry import register_writer
from fin_statement_model.io.exceptions import WriteError
from fin_statement_model.io.writers.dataframe import DataFrameWriter
from fin_statement_model.io.config.models import ExcelWriterConfig

logger = logging.getLogger(__name__)


@register_writer("excel")
class ExcelWriter(DataWriter):
    """Writes graph data to an Excel file.

    Converts the graph data to a pandas DataFrame first (using `DataFrameWriter`),
    then writes that DataFrame to an Excel file using `pandas.to_excel()`.

    Default configuration for options like `sheet_name`, `recalculate`, `include_nodes`,
    and `excel_writer_kwargs` is provided via an `ExcelWriterConfig` object during
    initialization. However, these settings can be overridden for a specific call
    by passing them as keyword arguments to the `.write()` method.
    """

    def __init__(self, cfg: Optional[ExcelWriterConfig] = None) -> None:
        """Initialize the ExcelWriter.

        Args:
            cfg: Optional validated `ExcelWriterConfig` instance.
        """
        self.cfg = cfg

    def write(self, graph: Graph, target: str, **kwargs: dict[str, Any]) -> None:
        """Write graph data to an Excel file, converting via DataFrame first.

        Args:
            graph (Graph): The Graph object containing the data to write.
            target (str): Path to the target Excel file.
            **kwargs: Optional keyword arguments to override settings from the
                `ExcelWriterConfig` provided during initialization, or to provide
                defaults if no config was used.
                - sheet_name (str): Name of the sheet. Defaults to `cfg.sheet_name` or "Sheet1".
                - recalculate (bool): Recalculate before export. Defaults to `cfg.recalculate` or True.
                - include_nodes (list[str], optional): Nodes to include. Defaults to `cfg.include_nodes` or all nodes.
                - excel_writer_kwargs (dict): Additional args for `pandas.to_excel()`. Defaults to `cfg.excel_writer_kwargs` or {}.

        Raises:
            WriteError: If an error occurs during the writing process.
        """
        file_path = target
        # Combine configuration defaults with method overrides
        if self.cfg:
            sheet_name = kwargs.get("sheet_name", self.cfg.sheet_name)
            recalculate = kwargs.get("recalculate", self.cfg.recalculate)
            include_nodes = kwargs.get("include_nodes", self.cfg.include_nodes)
            excel_writer_options = kwargs.get("excel_writer_kwargs", self.cfg.excel_writer_kwargs)
        else:
            sheet_name = kwargs.get("sheet_name", "Sheet1")
            recalculate = kwargs.get("recalculate", True)
            include_nodes = kwargs.get("include_nodes")
            excel_writer_options = kwargs.get("excel_writer_kwargs", {})

        logger.info(f"Exporting graph to Excel file: {file_path}, sheet: {sheet_name}")

        try:
            # 1. Convert graph to DataFrame using DataFrameWriter
            df_writer = DataFrameWriter()
            df = df_writer.write(
                graph=graph, target=None, recalculate=recalculate, include_nodes=include_nodes
            )

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
