"""Data reader for pandas DataFrames."""

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
    """Reads *wide-format* pandas DataFrames into a Graph using DataFrameReaderBase."""

    layout = "wide"

    def __init__(
        self, cfg: Optional[DataFrameReaderConfig] = None
    ) -> None:  # noqa: D401
        self.cfg = cfg

    # ------------------------------------------------------------------
    # WideTableReader hook implementation
    # ------------------------------------------------------------------
    def _load_dataframe(self, source: Any, **kwargs: Any) -> pd.DataFrame:
        """Return DataFrame after optional period filtering and index reset."""
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

        # Reset index to a column so WideTableReader treats it as items_col=1
        df_reset = df.reset_index()
        # Ensure first column is items names
        items_col_name = df_reset.columns[0]
        if items_col_name is None or items_col_name == "index":
            df_reset.rename(columns={items_col_name: "item"}, inplace=True)

        return df_reset
