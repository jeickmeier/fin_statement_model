"""Data reader for CSV files."""

import logging
from typing import Any

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
from fin_statement_model.io.config.models import CsvReaderConfig

logger = logging.getLogger(__name__)


@register_reader("csv")
class CsvReader(FileBasedReader, ConfigurableReaderMixin):
    """Reads financial statement data from a CSV file into a Graph.

    Assumes a 'long' format where each row represents a single data point
    (item, period, value).
    Requires specifying the columns containing item names, period identifiers,
    and values.

    Supports a `mapping_config` constructor parameter for name mapping,
    accepting either a flat mapping or a statement-type scoped mapping.

    Configuration (delimiter, header_row, index_col, mapping_config) is passed
    via a `CsvReaderConfig` object during initialization (typically by the `read_data` facade).
    Method-specific options (`item_col`, `period_col`, `value_col`, `pandas_read_csv_kwargs`)
    are passed as keyword arguments to the `read()` method.
    """

    def __init__(self, cfg: CsvReaderConfig) -> None:
        """Initialize the CsvReader with validated configuration.

        Args:
            cfg: A validated `CsvReaderConfig` instance containing parameters like
                 `source`, `delimiter`, `header_row`, `index_col`, and `mapping_config`.
        """
        self.cfg = cfg

    @handle_read_errors()
    def read(self, source: str, **kwargs: dict[str, Any]) -> Graph:
        """Read data from a CSV file into a new Graph.

        Args:
            source (str): Path to the CSV file.
            **kwargs: Read-time keyword arguments:
                item_col (str): Name of the column containing item identifiers.
                period_col (str): Name of the column containing period identifiers.
                value_col (str): Name of the column containing numeric values.
                pandas_read_csv_kwargs (dict): Additional arguments passed
                    directly to `pandas.read_csv()`. These can override settings
                    from the `CsvReaderConfig` (e.g., `delimiter`).

        Returns:
            A new Graph instance populated with FinancialStatementItemNodes.

        Raises:
            ReadError: If the file cannot be read or required columns are missing.
        """
        file_path = source
        logger.info(f"Starting import from CSV file: {file_path}")

        # Use base class validation
        self.validate_file_exists(file_path)
        self.validate_file_extension(file_path, (".csv", ".txt"))

        # Get required column names
        item_col = kwargs.get("item_col")
        period_col = kwargs.get("period_col")
        value_col = kwargs.get("value_col")

        if not all([item_col, period_col, value_col]):
            raise ReadError(
                "Missing required arguments: 'item_col', 'period_col', 'value_col' must be provided.",
                source=file_path,
                reader_type=self.__class__.__name__,
            )

        # Read CSV Data
        df = self._read_csv_file(file_path, kwargs.get("pandas_read_csv_kwargs", {}))

        # Validate columns
        self._validate_columns(df, item_col, period_col, value_col, file_path)

        # Process data
        return self._process_dataframe(df, item_col, period_col, value_col, file_path)

    def _read_csv_file(
        self, file_path: str, user_options: dict[str, Any]
    ) -> pd.DataFrame:
        """Read CSV file with configuration options."""
        # Use configuration from self.cfg, allow overrides via user_options
        read_options = {
            "delimiter": self.get_config_value("delimiter", ","),
            "header": self.get_config_value("header_row", 1)
            - 1,  # Convert to 0-indexed
        }

        # Handle optional index_col
        index_col = self.get_config_value("index_col")
        if index_col is not None:
            read_options["index_col"] = index_col - 1  # Convert to 0-indexed

        # Merge user-provided kwargs, allowing them to override config
        read_options.update(user_options)

        return pd.read_csv(file_path, **read_options)

    def _validate_columns(
        self,
        df: pd.DataFrame,
        item_col: str,
        period_col: str,
        value_col: str,
        file_path: str,
    ) -> None:
        """Validate that required columns exist in the DataFrame."""
        required_cols = {item_col, period_col, value_col}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise ReadError(
                f"Missing required columns in CSV: {missing_cols}",
                source=file_path,
                reader_type=self.__class__.__name__,
            )

    def _process_dataframe(
        self,
        df: pd.DataFrame,
        item_col: str,
        period_col: str,
        value_col: str,
        file_path: str,
    ) -> Graph:
        """Process the DataFrame and create a Graph."""
        # Convert period column to string
        df[period_col] = df[period_col].astype(str)
        all_periods = sorted(df[period_col].unique().tolist())

        if not all_periods:
            raise ReadError(
                "No periods found in the specified period column.",
                source=file_path,
                reader_type=self.__class__.__name__,
            )

        logger.info(f"Identified periods: {all_periods}")
        graph = Graph(periods=all_periods)

        # Use validation collector for better error reporting
        validator = ValidationResultCollector()

        # Group data by item name
        grouped = df.groupby(item_col)
        nodes_added = 0

        # Get mapping config
        mapping_config = self.get_config_value("mapping_config", {})
        if mapping_config is None:
            mapping_config = {}

        for item_name_csv, group in grouped:
            if pd.isna(item_name_csv) or not item_name_csv:
                logger.debug("Skipping group with empty item name.")
                continue

            item_name_csv_str = str(item_name_csv).strip()
            node_name = mapping_config.get(item_name_csv_str, item_name_csv_str)

            period_values = self._extract_period_values(
                group, period_col, value_col, item_name_csv_str, node_name, validator
            )

            if period_values:
                if graph.has_node(node_name):
                    logger.warning(
                        f"Node '{node_name}' (from CSV item '{item_name_csv_str}') already exists. "
                        "Overwriting data is not standard for readers."
                    )
                else:
                    new_node = FinancialStatementItemNode(
                        name=node_name, values=period_values
                    )
                    graph.add_node(new_node)
                    nodes_added += 1

        # Check for validation errors
        if validator.has_errors():
            summary = validator.get_summary()
            raise ReadError(
                f"Validation errors occurred while reading {file_path}: {'; '.join(summary['errors'])}",
                source=file_path,
                reader_type=self.__class__.__name__,
            )

        logger.info(
            f"Successfully created graph with {nodes_added} nodes from {file_path}."
        )
        return graph

    def _extract_period_values(
        self,
        group: pd.DataFrame,
        period_col: str,
        value_col: str,
        item_name_csv: str,
        node_name: str,
        validator: ValidationResultCollector,
    ) -> dict[str, float]:
        """Extract period values from a group with validation."""
        period_values: dict[str, float] = {}

        for _, row in group.iterrows():
            period = row[period_col]
            value = row[value_col]

            if pd.isna(value):
                continue  # Skip missing values

            # Validate and convert value
            if not isinstance(value, int | float):
                try:
                    value = float(value)
                    logger.warning(
                        f"Converted non-numeric value '{row[value_col]}' to float "
                        f"for node '{node_name}' period '{period}'"
                    )
                except (ValueError, TypeError):
                    validator.add_result(
                        item_name_csv,
                        False,
                        f"Non-numeric value '{value}' for period '{period}'",
                    )
                    continue

            if period in period_values:
                logger.warning(
                    f"Duplicate value found for node '{node_name}' "
                    f"(from CSV item '{item_name_csv}') period '{period}'. "
                    "Using the last one found."
                )

            period_values[period] = float(value)

        return period_values
