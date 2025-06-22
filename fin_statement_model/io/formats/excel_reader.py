"""Data reader for Excel files."""

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

    Expects data in a tabular format where rows typically represent items
    and columns represent periods, or vice-versa.
    Requires specifying sheet name, period identification, and item identification.

    Configuration (sheet_name, items_col, periods_row, mapping_config) is passed
    via an `ExcelReaderConfig` object during initialization (typically by the `read_data` facade).
    The optional ``header_row`` parameter controls which
    row pandas uses as column names.  When ``header_row`` equals
    ``periods_row`` (the default) the reader assumes the period labels already
    reside in the header row – no column renaming is attempted.  If callers set
    ``header_row`` *explicitly* to the same value as ``periods_row`` **while
    expecting the overwrite behaviour**, a warning is issued so the mismatch is
    obvious.

    Method-specific options (`statement_type`, `header_row`, `nrows`, `skiprows`)
    are passed as keyword arguments to the `read()` method.
    """

    layout = "wide"

    file_extensions = (".xls", ".xlsx", ".xlsm")

    def __init__(self, cfg: ExcelReaderConfig) -> None:
        """Store validated configuration object."""
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
        """Read Excel file once and extract data + period headers efficiently."""
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
        """Read Excel sheet and return DataFrame suitable for WideTableReader."""
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
