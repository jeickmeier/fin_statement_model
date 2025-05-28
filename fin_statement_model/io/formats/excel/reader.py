"""Data reader for Excel files."""

import logging
from typing import Optional, Any

import pandas as pd

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io.core.mixins import (
    FileBasedReader,
    ConfigurableReaderMixin,
    handle_read_errors,
    ValidationResultCollector,
)
from fin_statement_model.io.core.registry import register_reader
from fin_statement_model.io.exceptions import ReadError
from fin_statement_model.io.core.utils import normalize_mapping
from fin_statement_model.io.config.models import ExcelReaderConfig

logger = logging.getLogger(__name__)


@register_reader("excel")
class ExcelReader(FileBasedReader, ConfigurableReaderMixin):
    """Reads financial statement data from an Excel file into a Graph.

    Expects data in a tabular format where rows typically represent items
    and columns represent periods, or vice-versa.
    Requires specifying sheet name, period identification, and item identification.

    Configuration (sheet_name, items_col, periods_row, mapping_config) is passed
    via an `ExcelReaderConfig` object during initialization (typically by the `read_data` facade).
    Method-specific options (`statement_type`, `header_row`, `nrows`, `skiprows`)
    are passed as keyword arguments to the `read()` method.
    """

    def __init__(self, cfg: ExcelReaderConfig) -> None:
        """Initialize the ExcelReader with validated configuration.

        Args:
            cfg: A validated `ExcelReaderConfig` instance containing parameters like
                 `source`, `sheet_name`, `items_col`, `periods_row`, and `mapping_config`.
        """
        self.cfg = cfg

    def _get_mapping(self, statement_type: Optional[str]) -> dict[str, str]:
        """Get the appropriate mapping based on statement type and the stored config."""
        # Use the mapping config stored in the validated Pydantic config object
        config = self.get_config_value("mapping_config")
        # Normalize and overlay user-provided mappings
        mapping = normalize_mapping(config, context_key=statement_type)
        return mapping

    @handle_read_errors()
    def read(self, source: str, **kwargs: dict[str, Any]) -> Graph:
        """Read data from an Excel file sheet into a new Graph based on instance config.

        Args:
            source (str): Path to the Excel file.
            **kwargs: Optional runtime keyword arguments:
                statement_type (str, optional): Type of statement ('income_statement', 'balance_sheet', 'cash_flow').
                    Used to select a scope within the `mapping_config` provided during initialization.
                header_row (int, optional): 1-based index for pandas header reading.
                    Defaults to `self.cfg.periods_row` if not provided.
                nrows (int, optional): Number of rows to read from the sheet.
                skiprows (int, optional): Number of rows to skip at the beginning.

        Returns:
            A new Graph instance populated with FinancialStatementItemNodes.

        Raises:
            ReadError: If the file cannot be read or the configuration is invalid.
        """
        file_path = source
        logger.info(f"Starting import from Excel file: {file_path}")

        # Use base class validation
        self.validate_file_exists(file_path)
        self.validate_file_extension(file_path, (".xls", ".xlsx", ".xlsm"))

        # Get configuration values
        sheet_name = self.require_config_value("sheet_name")
        periods_row = self.require_config_value("periods_row")
        items_col = self.require_config_value("items_col")

        # Runtime options from kwargs
        statement_type = kwargs.get("statement_type")
        header_row = kwargs.get("header_row", periods_row)
        nrows = kwargs.get("nrows")
        skiprows = kwargs.get("skiprows")

        # Get mapping
        mapping = self._get_mapping(statement_type)
        logger.debug(f"Using mapping for statement type '{statement_type}': {mapping}")

        # Read Excel data
        df, period_headers = self._read_excel_data(
            file_path, sheet_name, periods_row, items_col, header_row, nrows, skiprows
        )

        # Extract periods
        graph_periods = self._extract_periods(period_headers, items_col)

        # Create and populate graph
        return self._create_graph(df, graph_periods, items_col, mapping, file_path, sheet_name)

    def _read_excel_data(
        self,
        file_path: str,
        sheet_name: str,
        periods_row: int,
        items_col: int,
        header_row: int,
        nrows: Optional[int],
        skiprows: Optional[int],
    ) -> tuple[pd.DataFrame, list[str]]:
        """Read Excel file and extract data and period headers."""
        # Convert to 0-based indices for pandas
        periods_row_0idx = periods_row - 1
        items_col_0idx = items_col - 1
        header_row_0idx = header_row - 1

        # Read the main data
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=header_row_0idx,
            skiprows=skiprows,
            nrows=nrows,
        )

        # Get period headers
        if header_row_0idx != periods_row_0idx:
            # Read periods row separately if different from header
            periods_df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                header=None,
                skiprows=periods_row_0idx,
                nrows=1,
            )
            period_headers = periods_df.iloc[0].astype(str).tolist()
        else:
            # Periods are in the main header row
            period_headers = df.columns.astype(str).tolist()

        # Validate items column index
        if items_col_0idx >= len(df.columns):
            raise ReadError(
                f"items_col index ({items_col}) is out of bounds for sheet '{sheet_name}'. "
                f"Found {len(df.columns)} columns.",
                source=file_path,
                reader_type=self.__class__.__name__,
            )

        return df, period_headers

    def _extract_periods(self, period_headers: list[str], items_col: int) -> list[str]:
        """Extract valid period names from headers."""
        items_col_0idx = items_col - 1

        # Filter period headers: exclude the item column and empty values
        graph_periods = [
            p for i, p in enumerate(period_headers) if i > items_col_0idx and p and p.strip()
        ]

        if not graph_periods:
            raise ReadError(
                f"Could not identify period columns after column {items_col}. "
                f"Headers found: {period_headers}",
                source="Excel file",
                reader_type=self.__class__.__name__,
            )

        logger.info(f"Identified periods: {graph_periods}")
        return graph_periods

    def _create_graph(
        self,
        df: pd.DataFrame,
        graph_periods: list[str],
        items_col: int,
        mapping: dict[str, str],
        file_path: str,
        sheet_name: str,
    ) -> Graph:
        """Create and populate the graph from DataFrame."""
        items_col_0idx = items_col - 1
        graph = Graph(periods=graph_periods)

        # Use validation collector
        validator = ValidationResultCollector()
        nodes_added = 0

        for index, row in df.iterrows():
            # Get item name
            item_name_excel = row.iloc[items_col_0idx]
            if pd.isna(item_name_excel) or not item_name_excel:
                continue

            item_name_excel = str(item_name_excel).strip()
            node_name = mapping.get(item_name_excel, item_name_excel)

            # Extract values for all periods
            period_values = self._extract_row_values(
                row, df, graph_periods, node_name, item_name_excel, index, validator
            )

            if period_values:
                if graph.has_node(node_name):
                    logger.warning(
                        f"Node '{node_name}' (from Excel item '{item_name_excel}') already exists. "
                        "Overwriting data is not standard for readers."
                    )
                else:
                    new_node = FinancialStatementItemNode(name=node_name, values=period_values)
                    graph.add_node(new_node)
                    nodes_added += 1

        # Check for validation errors
        if validator.has_errors():
            summary = validator.get_summary()
            raise ReadError(
                f"Validation errors occurred while reading {file_path} sheet '{sheet_name}': "
                f"{'; '.join(summary['errors'])}",
                source=file_path,
                reader_type=self.__class__.__name__,
            )

        logger.info(
            f"Successfully created graph with {nodes_added} nodes from {file_path} sheet '{sheet_name}'."
        )
        return graph

    def _extract_row_values(
        self,
        row: pd.Series,
        df: pd.DataFrame,
        graph_periods: list[str],
        node_name: str,
        item_name_excel: str,
        row_index: int,
        validator: ValidationResultCollector,
    ) -> dict[str, float]:
        """Extract period values from a row with validation."""
        period_values: dict[str, float] = {}

        for period in graph_periods:
            if period not in df.columns:
                logger.warning(
                    f"Period header '{period}' not found in DataFrame columns for row {row_index}."
                )
                continue

            value = row[period]

            if pd.isna(value):
                continue  # Skip NaN values

            if isinstance(value, int | float):
                period_values[period] = float(value)
            else:
                # Try to convert to float
                try:
                    period_values[period] = float(value)
                    logger.warning(
                        f"Converted non-numeric value '{value}' to float for "
                        f"node '{node_name}' period '{period}'"
                    )
                except (ValueError, TypeError):
                    validator.add_result(
                        f"Row {row_index}",
                        False,
                        f"Non-numeric value '{value}' for node '{node_name}' "
                        f"(from '{item_name_excel}') period '{period}'",
                    )

        return period_values
