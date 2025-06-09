"""Data reader for CSV files."""

import logging
from typing import Any, cast

import pandas as pd

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io.core.mixins import (
    FileBasedReader,
    ConfigurationMixin,
    MappingAwareMixin,
    ValidationMixin,
    handle_read_errors,
    ValidationResultCollector,
)
from fin_statement_model.io.core.registry import register_reader
from fin_statement_model.io.exceptions import ReadError
from fin_statement_model.io.config.models import CsvReaderConfig

logger = logging.getLogger(__name__)


@register_reader("csv")
class CsvReader(
    FileBasedReader, ConfigurationMixin, MappingAwareMixin, ValidationMixin
):
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
    def read(self, source: str, **kwargs: Any) -> Graph:
        """Read data from a CSV file into a new Graph.

        Args:
            source (str): Path to the CSV file.
            **kwargs: Optional runtime arguments overriding config defaults:
                statement_type (str): Statement type ('income_statement', 'balance_sheet', 'cash_flow').
                item_col (str): Name of the column containing item identifiers.
                period_col (str): Name of the column containing period identifiers.
                value_col (str): Name of the column containing numeric values.
                pandas_read_csv_kwargs (dict): Additional kwargs for pandas.read_csv.

        Returns:
            A new Graph instance populated with FinancialStatementItemNodes.

        Raises:
            ReadError: If the file cannot be read or required columns are missing.
        """
        file_path = source
        logger.info(f"Starting import from CSV file: {file_path}")

        # Set configuration context for better error reporting
        self.set_config_context(file_path=file_path, operation="read")

        # Use base class validation
        self.validate_file_exists(file_path)
        self.validate_file_extension(file_path, (".csv", ".txt"))

        # Runtime overrides: kwargs override configured defaults (statement_type handled in _process_dataframe)
        item_col = kwargs.get("item_col", self.cfg.item_col)
        period_col = kwargs.get("period_col", self.cfg.period_col)
        value_col = kwargs.get("value_col", self.cfg.value_col)
        pandas_read_csv_kwargs = (
            kwargs.get("pandas_read_csv_kwargs")
            or self.cfg.pandas_read_csv_kwargs
            or {}
        )

        if not all([item_col, period_col, value_col]):
            raise ReadError(
                "Missing required arguments: 'item_col', 'period_col', 'value_col' must be provided.",
                source=file_path,
                reader_type=self.__class__.__name__,
            )

        # Cast columns to str after validation
        item_col_str = cast(str, item_col)
        period_col_str = cast(str, period_col)
        value_col_str = cast(str, value_col)
        # Read CSV Data
        df = self._read_csv_file(file_path, pandas_read_csv_kwargs)

        # Validate columns
        self._validate_columns(
            df, item_col_str, period_col_str, value_col_str, file_path
        )

        # Process data
        return self._process_dataframe(
            df, item_col_str, period_col_str, value_col_str, file_path, kwargs
        )

    def _read_csv_file(
        self, file_path: str, user_options: dict[str, Any]
    ) -> pd.DataFrame:
        """Read CSV file with configuration options."""
        # Use configuration from self.cfg with enhanced validation
        from fin_statement_model.config.helpers import cfg

        delimiter = self.get_config_value(
            "delimiter",
            default=cfg("io.default_csv_delimiter"),
            value_type=str,
            validator=lambda x: len(x) >= 1,
        )
        header_row = self.get_config_value(
            "header_row", default=1, value_type=int, validator=lambda x: x >= 1
        )

        read_options = {
            "delimiter": delimiter,
            "header": header_row - 1,  # Convert to 0-indexed
        }

        # Handle optional index_col with validation
        index_col = self.get_config_value(
            "index_col",
            value_type=int,
            validator=lambda x: x is None or x >= 1,
        )
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
        # Use ValidationMixin for column validation
        self.validate_required_columns(df, [item_col, period_col, value_col], file_path)

    def _process_dataframe(
        self,
        df: pd.DataFrame,
        item_col: str,
        period_col: str,
        value_col: str,
        file_path: str,
        kwargs: dict[str, Any],
    ) -> Graph:
        """Process the DataFrame and create a Graph."""
        # Convert period column to string
        df[period_col] = df[period_col].astype(str)
        all_periods = sorted(df[period_col].unique().tolist())

        # Use ValidationMixin for periods validation
        self.validate_periods_exist(all_periods, file_path)

        logger.info(f"Identified periods: {all_periods}")
        graph = Graph(periods=all_periods)

        # Use validation collector for better error reporting
        validator = ValidationResultCollector()

        # Group data by item name
        grouped = df.groupby(item_col)
        nodes_added = 0

        # Determine mapping context
        context_key = kwargs.get("statement_type", self.cfg.statement_type)
        mapping = self._get_mapping(context_key)

        for item_name_csv, group in grouped:
            if pd.isna(item_name_csv) or not item_name_csv:
                logger.debug("Skipping group with empty item name.")
                continue

            item_name_csv_str = str(item_name_csv).strip()
            node_name = self._apply_mapping(item_name_csv_str, mapping)

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

            # Use ValidationMixin for numeric validation
            is_valid, converted_value = self.validate_numeric_value(
                value, item_name_csv, period, validator, allow_conversion=True
            )

            if not is_valid or converted_value is None:
                continue

            value = converted_value

            if period in period_values:
                logger.warning(
                    f"Duplicate value found for node '{node_name}' "
                    f"(from CSV item '{item_name_csv}') period '{period}'. "
                    "Using the last one found."
                )

            period_values[period] = float(value)

        return period_values
