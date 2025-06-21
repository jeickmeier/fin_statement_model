"""Data reader for Excel files."""

import logging
from typing import Any, Optional

import pandas as pd

from fin_statement_model.io.core.registry import register_reader
from fin_statement_model.io.core.wide_table_reader import WideTableReader
from fin_statement_model.io.config.models import ExcelReaderConfig

logger = logging.getLogger(__name__)


@register_reader("excel", schema=ExcelReaderConfig)
class ExcelReader(WideTableReader):
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

        # Validate items column index using ValidationMixin
        self.validate_column_bounds(
            df, items_col_0idx, file_path, f"items_col ({items_col})"
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
        self.validate_file_extension(file_path, (".xls", ".xlsx", ".xlsm"))

        # Resolve configuration values (config → kwargs override)
        sheet_name = kwargs.get("sheet_name", self.cfg.sheet_name)
        periods_row = kwargs.get("periods_row", self.cfg.periods_row)
        items_col = kwargs.get("items_col", self.cfg.items_col)
        header_row = kwargs.get("header_row", self.cfg.header_row or periods_row)
        nrows = kwargs.get("nrows", self.cfg.nrows)
        skiprows = kwargs.get("skiprows", self.cfg.skiprows)

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

        # Use extracted period headers to rename DataFrame columns if needed
        if header_row - 1 != periods_row - 1:
            # DataFrame columns are from header_row, replace period part
            new_cols = list(df_raw.columns)
            for idx in range(items_col, len(new_cols)):
                # align index offset by items_col
                if idx - items_col < len(period_headers):
                    new_cols[idx] = str(period_headers[idx])
            df_raw.columns = new_cols

        return df_raw
