"""Data writer for exporting graph data to Microsoft Excel files.

This module provides the `ExcelWriter`, a `DataWriter` implementation that
serializes a `Graph` object into a Microsoft Excel file (`.xlsx`). It first
converts the graph data to a pandas DataFrame and then uses pandas' Excel
writing capabilities.
"""

import logging
from pathlib import Path
from typing import Any

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.config.models import (
    ExcelWriterConfig,
)
from fin_statement_model.io.core.base_table_writer import BaseTableWriter
from fin_statement_model.io.core.mixins import ConfigurationMixin, handle_write_errors
from fin_statement_model.io.core.registry import register_writer

logger = logging.getLogger(__name__)


@register_writer("excel", schema=ExcelWriterConfig)
class ExcelWriter(BaseTableWriter, ConfigurationMixin):
    """Writes graph data to an Excel file.

    This writer serializes a `Graph` object to a Microsoft Excel file. The process
    involves an intermediate step of converting the graph data into a pandas
    DataFrame, with node names as the index and periods as columns.

    The behavior of the writer, such as the output sheet name and whether to
    recalculate the graph, is controlled by an `ExcelWriterConfig` object.
    Additional pandas-specific options can also be passed.
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
            target (Any): Path to the target Excel file.
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
        excel_writer_options = self._param("excel_writer_kwargs", kwargs, self.cfg, default={})

        logger.info("Exporting graph to Excel file: %s, sheet: %s", file_path, sheet_name)

        # Convert graph to DataFrame
        df = self.to_dataframe(graph, include_nodes=include_nodes, recalc=recalculate)

        # Write DataFrame to Excel
        self._write_to_excel(df, file_path, sheet_name, excel_writer_options)

        logger.info("Successfully exported graph to %s, sheet '%s'", file_path, sheet_name)

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
