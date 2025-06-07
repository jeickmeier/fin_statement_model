"""Data writer for Excel files."""

import logging
from pathlib import Path
from typing import Any, Optional

from fin_statement_model.core.graph import Graph
from fin_statement_model.io.core.base import DataWriter
from fin_statement_model.io.core.mixins import (
    ConfigurableReaderMixin,
    handle_write_errors,
)
from fin_statement_model.io.core.registry import register_writer
from fin_statement_model.io.formats.dataframe.writer import DataFrameWriter
from fin_statement_model.io.config.models import (
    ExcelWriterConfig,
    DataFrameWriterConfig,
)

logger = logging.getLogger(__name__)


@register_writer("excel")
class ExcelWriter(DataWriter, ConfigurableReaderMixin):
    """Writes graph data to an Excel file.

    Converts the graph data to a pandas DataFrame first (using `DataFrameWriter`),
    then writes that DataFrame to an Excel file using `pandas.to_excel()`.

    Configuration (sheet_name, recalculate, include_nodes, excel_writer_kwargs) is
    provided via an `ExcelWriterConfig` object during initialization.
    """

    def __init__(self, cfg: Optional[ExcelWriterConfig] = None) -> None:
        """Initialize the ExcelWriter.

        Args:
            cfg: Optional validated `ExcelWriterConfig` instance.
        """
        super().__init__()
        self.cfg = cfg

    @handle_write_errors()
    def write(self, graph: Graph, target: str, **kwargs: dict[str, Any]) -> None:
        """Write graph data to an Excel file, converting via DataFrame first.

        Args:
            graph (Graph): The Graph object containing the data to write.
            target (str): Path to the target Excel file.
            **kwargs: Currently unused. Configuration is handled by the ExcelWriterConfig.

        Raises:
            WriteError: If an error occurs during the writing process.
        """
        file_path = target

        # Get configuration values using the mixin
        sheet_name = self.get_config_value("sheet_name", "Sheet1")
        recalculate = self.get_config_value("recalculate", True)
        include_nodes = self.get_config_value("include_nodes")
        excel_writer_options = self.get_config_value("excel_writer_kwargs", {})

        logger.info(f"Exporting graph to Excel file: {file_path}, sheet: {sheet_name}")

        # Convert graph to DataFrame
        df = self._create_dataframe(graph, recalculate, include_nodes)

        # Write DataFrame to Excel
        self._write_to_excel(df, file_path, sheet_name, excel_writer_options)

        logger.info(f"Successfully exported graph to {file_path}, sheet '{sheet_name}'")

    def _create_dataframe(
        self, graph: Graph, recalculate: bool, include_nodes: Optional[list[str]]
    ) -> Any:
        """Convert graph to DataFrame using DataFrameWriter.

        Args:
            graph: The graph to convert.
            recalculate: Whether to recalculate before export.
            include_nodes: Optional list of nodes to include.

        Returns:
            pandas DataFrame with the graph data.
        """
        # Create a config for DataFrameWriter
        df_config = DataFrameWriterConfig(
            format_type="dataframe",
            recalculate=recalculate,
            include_nodes=include_nodes,
        )

        df_writer = DataFrameWriter(df_config)
        return df_writer.write(graph=graph, target=None)

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
