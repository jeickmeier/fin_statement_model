"""Data writer for Excel files."""

import logging
from pathlib import Path
from typing import Any

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.core.mixins import ConfigurationMixin, handle_write_errors
from fin_statement_model.io.core.base_table_writer import BaseTableWriter
from fin_statement_model.io.core.registry import register_writer
from fin_statement_model.io.config.models import (
    ExcelWriterConfig,
)

logger = logging.getLogger(__name__)


@register_writer("excel", schema=ExcelWriterConfig)
class ExcelWriter(BaseTableWriter, ConfigurationMixin):
    """Writes graph data to an Excel file.

    Converts the graph data to a pandas DataFrame first (using `DataFrameWriter`),
    then writes that DataFrame to an Excel file using `pandas.to_excel()`.

    Configuration (sheet_name, recalculate, include_nodes, excel_writer_kwargs) is
    provided via an `ExcelWriterConfig` object during initialization.
    """

    def __init__(self, cfg: ExcelWriterConfig) -> None:
        """Initialize the ExcelWriter.

        Args:
            cfg: Non-optional validated `ExcelWriterConfig` instance.
        """
        super().__init__()
        self.cfg = cfg

    @handle_write_errors()
    def write(self, graph: Graph, target: Any = None, **kwargs: Any) -> None:
        """Write graph data to an Excel file, converting via DataFrame first.

        Args:
            graph (Graph): The Graph object containing the data to write.
            target (str): Path to the target Excel file.
            **kwargs: Optional runtime overrides of configured defaults:
                sheet_name (str): Excel sheet name.
                recalculate (bool): Whether to recalculate graph before export.
                include_nodes (list[str]): List of node names to include in export.
                excel_writer_kwargs (dict): Additional kwargs for pandas.DataFrame.to_excel.

        Raises:
            WriteError: If an error occurs during the writing process.
        """
        file_path = str(target)

        # Runtime overrides: kwargs override configured defaults
        sheet_name = self._param("sheet_name", kwargs, self.cfg, default="Sheet1")
        recalculate = self._param("recalculate", kwargs, self.cfg, default=True)
        include_nodes = self._param("include_nodes", kwargs, self.cfg)
        excel_writer_options = self._param(
            "excel_writer_kwargs", kwargs, self.cfg, default={}
        )

        logger.info(f"Exporting graph to Excel file: {file_path}, sheet: {sheet_name}")

        # Convert graph to DataFrame
        df = self.to_dataframe(graph, include_nodes=include_nodes, recalc=recalculate)

        # Write DataFrame to Excel
        self._write_to_excel(df, file_path, sheet_name, excel_writer_options)

        logger.info(f"Successfully exported graph to {file_path}, sheet '{sheet_name}'")

    def _write_to_excel(
        self,
        df: Any,
        file_path: str,
        sheet_name: str,
        excel_writer_options: dict[str, Any],
    ) -> None:
        """Write DataFrame to Excel file.

        Args:
            df: The pandas DataFrame to write.
            file_path: Path to the output file.
            sheet_name: Name of the Excel sheet.
            excel_writer_options: Additional options for pandas.to_excel().
        """
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df.to_excel(
            output_path,
            sheet_name=sheet_name,
            index=True,  # Keep node names as index column
            **excel_writer_options,
        )
