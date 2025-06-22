"""Data reader for Microsoft Excel files.

This module provides the `ExcelReader`, a `DataReader` implementation for reading
financial data from Excel worksheets. It expects the data to be in a "wide"
format, where rows represent financial items and columns represent periods.

The reader is built on top of the `DataFrameReaderBase` and uses pandas to
load the data from the specified sheet.
"""

import logging
from typing import Any, Optional

import pandas as pd

from fin_statement_model.io.core.registry import register_reader
from fin_statement_model.io.core.dataframe_reader_base import DataFrameReaderBase
from fin_statement_model.io.config.models import ExcelReaderConfig
from fin_statement_model.io.exceptions import ReadError

logger = logging.getLogger(__name__)


@register_reader("excel", schema=ExcelReaderConfig)
class ExcelReader(DataFrameReaderBase):
    """Reads financial statement data from an Excel file into a Graph.

    This reader is designed to handle "wide" format data from an Excel sheet,
    where rows typically represent financial items and columns represent periods.
    It is highly configurable, allowing the user to specify the sheet name,
    the location of item names, and the location of period headers.

    Configuration is provided via an `ExcelReaderConfig` object. Runtime overrides
    for certain options can be passed as keyword arguments to the `read` method.

    Attributes:
        layout (str): Specifies the expected data layout, hardcoded to "wide".
        file_extensions (tuple[str, ...]): A tuple of valid file extensions.
    """

    layout = "wide"

    file_extensions = (".xls", ".xlsx", ".xlsm")

    def __init__(self, cfg: ExcelReaderConfig) -> None:
        """Initialize the ExcelReader.

        Args:
            cfg: A validated `ExcelReaderConfig` instance.
        """
        self.cfg = cfg

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
        """Read core data and period headers from an Excel sheet.

        This helper method reads a specified sheet from an Excel file into a raw
        pandas DataFrame without a header. It then extracts the period labels from
        the `periods_row` and reconstructs the main DataFrame using the `header_row`.
        This approach provides flexibility in handling various Excel layouts.

        Args:
            file_path: The path to the Excel file.
            sheet_name: The name or index of the sheet to read.
            periods_row: The 1-indexed row number containing the period labels.
            items_col: The 1-indexed column number containing the item names.
            header_row: The 1-indexed row number to use for the DataFrame header.
            nrows: The optional number of rows to read.
            skiprows: The optional number of rows to skip at the beginning.

        Returns:
            A tuple containing:
                - The main pandas DataFrame with the correct header.
                - A list of period header strings.
        """
        # Read sheet without assigning header so we can slice any row later
        raw_df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=None,
            skiprows=skiprows,
            nrows=nrows,
        )

        periods_row_idx = periods_row - 1
        header_row_idx = header_row - 1

        # Extract period headers from requested row
        period_headers = raw_df.iloc[periods_row_idx].astype(str).tolist()

        # Rebuild DataFrame starting from header_row
        df = raw_df.drop(index=list(range(0, header_row_idx + 1))).reset_index(
            drop=True
        )
        df.columns = raw_df.iloc[header_row_idx]

        # Validate items column index
        self.validate_column_bounds(
            df, items_col - 1, file_path, f"items_col ({items_col})"
        )

        return df, period_headers

    # ------------------------------------------------------------------
    # WideTableReader hook implementation
    # ------------------------------------------------------------------
    def _load_dataframe(self, source: Any, **kwargs: Any) -> pd.DataFrame:
        """Load data from an Excel file into a pandas DataFrame.

        This method implements the `_load_dataframe` hook from `DataFrameReaderBase`.
        It validates the file, resolves configuration options for the sheet name,
        row/column locations, and other parameters. It then calls `_read_excel_data`
        to perform the read operation and prepares the resulting DataFrame by ensuring
        its column names are set correctly based on the extracted period headers.

        Args:
            source (Any): The file path to the Excel file.
            **kwargs (Any): Optional runtime overrides for configuration.

        Returns:
            A pandas DataFrame ready for parsing by `DataFrameReaderBase`.
        """
        file_path = source
        # Basic file validation
        self.validate_file_exists(file_path)
        self.validate_file_extension(file_path)

        # Resolve configuration values using DataFrameReaderBase helper
        sheet_name = self._param("sheet_name", kwargs, default="Sheet1")
        periods_row = self._param("periods_row", kwargs, default=1)
        items_col = self._param("items_col", kwargs, default=1)
        header_row = self._param("header_row", kwargs)

        # XOR enforcement – raise early if both provided via kwargs (override) or cfg.
        if (
            header_row is not None
            and "periods_row" in kwargs
            and kwargs.get("periods_row") is not None
        ):
            raise ReadError(
                "Provide either header_row or periods_row, not both.",
                source=str(source),
                reader_type="ExcelReader",
            )

        if header_row is None:
            # Fallback to periods_row if caller omitted header_row
            header_row = periods_row

        nrows = self._param("nrows", kwargs)
        skiprows = self._param("skiprows", kwargs)

        # Read underlying sheet to DataFrame (may include header row)
        df_raw, period_headers = self._read_excel_data(
            file_path,
            sheet_name,
            periods_row,
            items_col,
            header_row,
            nrows,
            skiprows,
        )

        # Use extracted period headers to rename DataFrame columns if needed.
        if header_row - 1 != periods_row - 1:
            # DataFrame columns are from header_row, replace period part
            new_cols = list(df_raw.columns)
            for idx in range(items_col, len(new_cols)):
                # align index offset by items_col
                if idx - items_col < len(period_headers):
                    new_cols[idx] = str(period_headers[idx])
            df_raw.columns = new_cols
        # No else branch needed – when header_row equals periods_row renaming is
        # a no-op *by design* and no longer merits a warning.

        return df_raw
