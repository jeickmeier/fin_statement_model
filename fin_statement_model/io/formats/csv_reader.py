"""Data reader for comma-separated value (CSV) files.

This module provides the `CsvReader`, a `DataReader` implementation for reading
financial data from CSV files. It expects the data to be in a "long" format, where
each row represents a single observation (i.e., one item for one period).

The reader is built on top of the `DataFrameReaderBase` and leverages its
parsing and validation logic, using pandas to load the data from the file.
"""

import logging
from typing import Any, cast

import pandas as pd

from fin_statement_model.io.config.models import CsvReaderConfig
from fin_statement_model.io.core.dataframe_reader_base import DataFrameReaderBase
from fin_statement_model.io.core.registry import register_reader

logger = logging.getLogger(__name__)


@register_reader("csv", schema=CsvReaderConfig)
class CsvReader(DataFrameReaderBase):
    """Reads financial data from long-format CSV files into a Graph.

    This reader is configured to handle CSV files where each row contains data
    for a single item in a single period. It requires the configuration to specify
    which columns correspond to the item name, period, and value.

    Configuration is provided via a `CsvReaderConfig` object.

    Attributes:
        layout (str): Specifies the expected data layout, hardcoded to "long".
        file_extensions (tuple[str, ...]): A tuple of valid file extensions ('.csv', '.txt').
    """

    # Specify long layout (rows = observations)
    layout = "long"

    # Valid file extensions handled by this reader
    file_extensions = (".csv", ".txt")

    def __init__(self, cfg: CsvReaderConfig) -> None:
        """Initialize the CsvReader.

        Args:
            cfg: A validated `CsvReaderConfig` instance.
        """
        self.cfg = cfg

    # ------------------------------------------------------------------
    # DataFrameReaderBase hook implementation
    # ------------------------------------------------------------------
    def _load_dataframe(self, source: Any, **kwargs: Any) -> pd.DataFrame:
        """Load data from a CSV file into a pandas DataFrame.

        This method implements the `_load_dataframe` hook from `DataFrameReaderBase`.
        It validates the file's existence and extension, then uses `pandas.read_csv`
        to load the data. Configuration options like the delimiter and header row
        are retrieved from the `CsvReaderConfig` object.

        Args:
            source (Any): The file path to the CSV file.
            **kwargs (Any): Additional keyword arguments, including pandas-specific options.

        Returns:
            A pandas DataFrame containing the data from the CSV file.
        """
        self.validate_file_exists(source)
        self.validate_file_extension(source)

        delimiter = self.get_config_value("delimiter", default=",", value_type=str)
        header_row = self.get_config_value("header_row", default=1, value_type=int)
        index_col = self.get_config_value("index_col")
        user_opts = kwargs.get("pandas_read_csv_kwargs") or self.cfg.pandas_read_csv_kwargs or {}

        read_opts: dict[str, Any] = {
            "delimiter": delimiter,
            "header": header_row - 1,
        }
        if index_col is not None:
            read_opts["index_col"] = cast("int", index_col) - 1
        read_opts.update(user_opts)
        return cast("pd.DataFrame", pd.read_csv(source, **read_opts))
