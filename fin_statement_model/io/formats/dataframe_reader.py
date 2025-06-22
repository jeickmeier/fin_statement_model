"""Data reader for in-memory pandas DataFrames.

This module provides the `DataFrameReader`, a `DataReader` implementation for
reading financial data directly from a `pandas.DataFrame` object. It expects
the data to be in a "wide" format, where rows represent items and columns
represent periods.

The reader is built on top of `DataFrameReaderBase`.
"""

import logging
import pandas as pd
from typing import Optional, Any

from fin_statement_model.io.core.registry import register_reader
from fin_statement_model.io.core.dataframe_reader_base import DataFrameReaderBase
from fin_statement_model.io.config.models import DataFrameReaderConfig
from fin_statement_model.io.exceptions import ReadError

logger = logging.getLogger(__name__)


@register_reader("dataframe", schema=DataFrameReaderConfig)
class DataFrameReader(DataFrameReaderBase):
    """Reads financial data from a wide-format pandas DataFrame into a Graph.

    This reader is designed to ingest data from a DataFrame where the index
    contains the financial item names and the columns represent different periods.
    It can also handle a specified subset of period columns.

    Configuration is provided via a `DataFrameReaderConfig` object.

    Attributes:
        layout (str): Specifies the expected data layout, hardcoded to "wide".
    """

    layout = "wide"

    def __init__(self, cfg: Optional[DataFrameReaderConfig] = None) -> None:
        """Initialize the DataFrameReader.

        Args:
            cfg: An optional, validated `DataFrameReaderConfig` instance.
        """
        self.cfg = cfg

    # ------------------------------------------------------------------
    # WideTableReader hook implementation
    # ------------------------------------------------------------------
    def _load_dataframe(self, source: Any, **kwargs: Any) -> pd.DataFrame:
        """Prepare the source DataFrame for parsing.

        This method implements the `_load_dataframe` hook from `DataFrameReaderBase`.
        It validates that the source is a pandas DataFrame, creates a copy, and
        optionally filters it to include only a specified subset of period columns.

        It also resets the DataFrame's index to ensure the item names are in a
        column named 'item', which is the format expected by the base parser.

        Args:
            source (Any): The input pandas DataFrame.
            **kwargs (Any): Additional keyword arguments, including 'periods' to
                specify a subset of columns to read.

        Returns:
            A pandas DataFrame ready for parsing by `DataFrameReaderBase`.

        Raises:
            ReadError: If the source is not a DataFrame or if specified periods
                are not found in the columns.
        """
        if not isinstance(source, pd.DataFrame):
            raise ReadError(
                "Source is not a pandas DataFrame.",
                source="DataFrame",
                reader_type="DataFrameReader",
            )

        df = source.copy()

        # Determine periods subset (kwargs override cfg)
        periods_subset = kwargs.get("periods", self.cfg.periods if self.cfg else None)
        if periods_subset:
            missing = [p for p in periods_subset if p not in df.columns]
            if missing:
                raise ReadError(
                    f"Specified periods not found in DataFrame: {missing}",
                    source="DataFrame",
                    reader_type="DataFrameReader",
                )
            df = df[periods_subset]

        # Reset index and rename the first column to 'item' consistently
        df_reset = df.reset_index()
        first_col = df_reset.columns[0]
        if first_col != "item":
            df_reset.rename(columns={first_col: "item"}, inplace=True)

        return df_reset
