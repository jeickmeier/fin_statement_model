"""Data reader for CSV files."""

import logging
import os
from typing import Any

import pandas as pd

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io.base import DataReader
from fin_statement_model.io.registry import register_reader
from fin_statement_model.io.exceptions import ReadError
from fin_statement_model.io.readers.base import MappingConfig, normalize_mapping

logger = logging.getLogger(__name__)


@register_reader("csv")
class CsvReader(DataReader):
    """Reads financial statement data from a CSV file into a Graph.

    Assumes a 'long' format where each row represents a single data point
    (item, period, value).
    Requires specifying the columns containing item names, period identifiers,
    and values.

    Supports a `mapping_config` constructor parameter for name mapping,
    accepting either a flat mapping or a statement-type scoped mapping.

    Note:
        When using the `read_data` facade, pass `mapping_config` via init,
        and reader-specific options (`item_col`, `period_col`, `value_col`,
        `pandas_read_csv_kwargs`) to `read()`. Direct instantiation is also supported.
    """

    def __init__(self, mapping_config: MappingConfig = None, **kwargs: Any) -> None:
        """Initialize the CsvReader.

        Args:
            mapping_config (MappingConfig): Optional mapping configuration to
                map CSV item names to canonical node names. Can be either:
                  - Dict[str, str] for a flat mapping.
                  - Dict[Optional[str], Dict[str, str]] for scoped mappings
                    keyed by statement type (or None for default).
            **kwargs: Not used by CsvReader init; reserved for API consistency.
        """
        # Store a normalized flat mapping for default use
        self.mapping = normalize_mapping(mapping_config)

    def read(self, source: str, **kwargs: dict[str, Any]) -> Graph:
        """Read data from a CSV file into a new Graph.

        Args:
            source (str): Path to the CSV file.
            **kwargs: Keyword arguments supported by this reader:
                item_col (str): Name of the column containing item identifiers.
                period_col (str): Name of the column containing period identifiers.
                value_col (str): Name of the column containing numeric values.
                mapping_config (MappingConfig): Overrides the mapping config
                    provided at initialization.
                pandas_read_csv_kwargs (dict): Additional arguments passed
                    directly to `pandas.read_csv()`.

        Returns:
            A new Graph instance populated with FinancialStatementItemNodes.

        Raises:
            ReadError: If the file cannot be read or required columns are missing.
        """
        file_path = source
        logger.info(f"Starting import from CSV file: {file_path}")

        # --- Validate Inputs ---
        if not os.path.exists(file_path):
            raise ReadError(
                f"File not found: {file_path}",
                source=file_path,
                reader_type="CsvReader",
            )

        item_col = kwargs.get("item_col")
        period_col = kwargs.get("period_col")
        value_col = kwargs.get("value_col")
        read_csv_options = kwargs.get("pandas_read_csv_kwargs", {})

        if not item_col or not period_col or not value_col:
            raise ReadError(
                "Missing required arguments: 'item_col', 'period_col', 'value_col' must be provided.",
                source=file_path,
                reader_type="CsvReader",
            )

        # Normalize mapping config for this read operation
        current_mapping_config = kwargs.get("mapping_config", self.mapping)
        try:
            mapping = normalize_mapping(current_mapping_config)
        except TypeError as te:
            raise ReadError(
                "Invalid mapping_config provided.",
                source=file_path,
                reader_type="CsvReader",
                original_error=te,
            )
        logger.debug(f"Using mapping: {mapping}")

        # --- Read CSV Data ---
        try:
            df = pd.read_csv(file_path, **read_csv_options)

            # Validate required columns exist
            required_cols = {item_col, period_col, value_col}
            missing_cols = required_cols - set(df.columns)
            if missing_cols:
                raise ReadError(
                    f"Missing required columns in CSV: {missing_cols}",
                    source=file_path,
                    reader_type="CsvReader",
                )

            # Convert period column to string
            df[period_col] = df[period_col].astype(str)
            all_periods = sorted(df[period_col].unique().tolist())
            if not all_periods:
                raise ReadError(
                    "No periods found in the specified period column.",
                    source=file_path,
                    reader_type="CsvReader",
                )

            logger.info(f"Identified periods: {all_periods}")
            graph = Graph(periods=all_periods)

            # --- Populate Graph ---
            # Group data by item name
            grouped = df.groupby(item_col)
            validation_errors = []
            nodes_added = 0

            for item_name_csv, group in grouped:
                if pd.isna(item_name_csv) or not item_name_csv:
                    logger.debug("Skipping group with empty item name.")
                    continue

                item_name_csv_str = str(item_name_csv).strip()
                node_name = mapping.get(item_name_csv_str, item_name_csv_str)

                period_values: dict[str, float] = {}
                for _, row in group.iterrows():
                    period = row[period_col]
                    value = row[value_col]

                    if pd.isna(value):
                        continue  # Skip missing values

                    if not isinstance(value, (int, float)):
                        try:
                            value = float(value)
                            logger.warning(
                                f"Converted non-numeric value '{row[value_col]}' to float for node '{node_name}' period '{period}'"
                            )
                        except (ValueError, TypeError):
                            validation_errors.append(
                                f"Item '{item_name_csv_str}': Non-numeric value '{value}' for period '{period}'"
                            )
                            continue  # Skip this invalid value

                    if period in period_values:
                        logger.warning(
                            f"Duplicate value found for node '{node_name}' (from CSV item '{item_name_csv_str}') period '{period}'. Using the last one found."
                        )

                    period_values[period] = float(value)

                if period_values:
                    if graph.has_node(node_name):
                        logger.warning(
                            f"Node '{node_name}' (from CSV item '{item_name_csv_str}') already exists. Overwriting data is not standard for readers."
                        )
                        # Potentially update existing node? For now, log.
                    else:
                        new_node = FinancialStatementItemNode(name=node_name, values=period_values)
                        graph.add_node(new_node)
                        nodes_added += 1

            if validation_errors:
                raise ReadError(
                    f"Validation errors occurred while reading {file_path}: {'; '.join(validation_errors)}",
                    source=file_path,
                    reader_type="CsvReader",
                )

            logger.info(f"Successfully created graph with {nodes_added} nodes from {file_path}.")
            return graph

        except FileNotFoundError:
            raise ReadError(
                f"File not found: {file_path}",
                source=file_path,
                reader_type="CsvReader",
            )
        except ValueError as ve:
            raise ReadError(
                f"Error reading CSV file: {ve}",
                source=file_path,
                reader_type="CsvReader",
                original_error=ve,
            )
        except KeyError as ke:
            raise ReadError(
                f"Column not found error (check item/period/value_col names): {ke}",
                source=file_path,
                reader_type="CsvReader",
                original_error=ke,
            )
        except Exception as e:
            logger.error(f"Failed to read CSV file {file_path}: {e}", exc_info=True)
            raise ReadError(
                message=f"Failed to process CSV file: {e}",
                source=file_path,
                reader_type="CsvReader",
                original_error=e,
            ) from e
