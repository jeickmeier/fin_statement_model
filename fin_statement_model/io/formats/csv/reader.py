"""Data reader for CSV files."""

import logging
from typing import Any, cast

import pandas as pd

from fin_statement_model.io.core.registry import register_reader
from fin_statement_model.io.config.models import CsvReaderConfig
from fin_statement_model.io.core.tabular_reader import TabularReader

logger = logging.getLogger(__name__)


@register_reader("csv", schema=CsvReaderConfig)
class CsvReader(TabularReader):
    """Reads *long-format* CSV into a Graph using the common TabularReader."""

    def __init__(self, cfg: CsvReaderConfig) -> None:  # noqa: D401
        self.cfg = cfg

    # ------------------------------------------------------------------
    # TabularReader hook implementation
    # ------------------------------------------------------------------
    def _load_dataframe(self, source: Any, **kwargs: Any) -> pd.DataFrame:
        """Read the CSV file and return a DataFrame."""
        self.validate_file_exists(source)
        self.validate_file_extension(source, (".csv", ".txt"))

        delimiter = self.get_config_value("delimiter", default=",", value_type=str)
        header_row = self.get_config_value("header_row", default=1, value_type=int)
        index_col = self.get_config_value("index_col")
        user_opts = (
            kwargs.get("pandas_read_csv_kwargs")
            or self.cfg.pandas_read_csv_kwargs
            or {}
        )

        read_opts: dict[str, Any] = {
            "delimiter": delimiter,
            "header": header_row - 1,
        }
        if index_col is not None:
            read_opts["index_col"] = cast(int, index_col) - 1
        read_opts.update(user_opts)
        return pd.read_csv(source, **read_opts)
