"""Generic helper for readers that ingest pandas.DataFrame-like sources.

This module unifies the two historical reader bases (*long*-layout and
*wide*-layout) into a single implementation.  Concrete subclasses only need

1. to declare a class-level ``layout`` attribute – either ``"long"`` or
   ``"wide"``; and
2. implement ``_load_dataframe(self, source, **kwargs)`` which returns the raw
   :class:`pandas.DataFrame` loaded from *source* (file path, in-memory frame,
   etc.).

Everything else – mapping, validation and Graph construction – is handled by
this base class.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, cast

import pandas as pd

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io.core.mixins import (
    ConfigurationMixin,
    MappingAwareMixin,
    ValidationMixin,
    ValidationResultCollector,
    FileBasedReader,
    handle_read_errors,
)
from fin_statement_model.io.exceptions import ReadError

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Main helper class
# -----------------------------------------------------------------------------


class DataFrameReaderBase(  # pylint: disable=too-many-public-methods
    FileBasedReader,
    MappingAwareMixin,  # must precede ConfigurationMixin for mypy clarity
    ConfigurationMixin,
    ValidationMixin,
    ABC,
):
    """Common reader for *DataFrame* sources supporting *long* + *wide* layouts."""

    #: expected subclass override – either ``"long"`` or ``"wide"``
    layout: str = "long"

    # Whether to coerce non-numeric strings to floats during value validation
    allow_conversion: bool = True

    # ------------------------------------------------------------------
    # Sub-class contract
    # ------------------------------------------------------------------
    @abstractmethod
    def _load_dataframe(self, source: Any, **kwargs: Any) -> pd.DataFrame:  # noqa: D401
        """Return the pandas.DataFrame loaded from *source*.

        Sub-classes implement actual IO (reading CSV, Excel, DataFrame copy, …).
        """

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    LONG_REQUIRED_COLS = ("item_col", "period_col", "value_col")
    WIDE_REQUIRED_ATTR = "items_col"  # single int

    # private util ------------------------------------------------------
    def _resolve_long_columns(self, kwargs: dict[str, Any]) -> tuple[str, str, str]:
        """Resolve the names of the item, period, and value columns."""
        item_col = cast(
            str,
            kwargs.get("item_col") or self.get_config_value("item_col", required=True),
        )
        period_col = cast(
            str,
            kwargs.get("period_col")
            or self.get_config_value("period_col", required=True),
        )
        value_col = cast(
            str,
            kwargs.get("value_col")
            or self.get_config_value("value_col", required=True),
        )
        return item_col, period_col, value_col

    def _resolve_wide_items_col(self, kwargs: dict[str, Any]) -> int:
        """Resolve the 0-indexed column number for item names in wide format."""
        items_col_idx_1 = cast(
            int,
            kwargs.get(self.WIDE_REQUIRED_ATTR)
            or self.get_config_value(
                self.WIDE_REQUIRED_ATTR, default=1, value_type=int
            ),
        )
        if items_col_idx_1 < 1:
            raise ReadError(
                "items_col must be >=1",
                reader_type=self.__class__.__name__,
            )
        return items_col_idx_1 - 1  # return 0-indexed

    def _resolve_mapping(self, kwargs: dict[str, Any]) -> dict[str, str]:
        """Resolve the appropriate name mapping for the current read operation."""
        ctx = kwargs.get("statement_type", self.get_config_value("statement_type"))
        return self._get_mapping(ctx)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
        # Forward to mixin initialisers (super() resolves MRO)
        super().__init__(*args, **kwargs)
        # Allow individual readers to override via subclass attribute or ctor kwarg
        if "allow_conversion" in kwargs:
            self.allow_conversion = bool(kwargs["allow_conversion"])

    # ------------------------------------------------------------------
    # Parameter helper to DRY cfg/kwargs merging
    # ------------------------------------------------------------------
    def _param(
        self, name: str, overrides: dict[str, Any], *, default: Any = None
    ) -> Any:  # noqa: D401
        """Return effective value for *name* with precedence: overrides → cfg → default."""
        if name in overrides:
            return overrides[name]
        if hasattr(self, "cfg") and self.cfg is not None and hasattr(self.cfg, name):
            return getattr(self.cfg, name)
        return default

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    @handle_read_errors()
    def read(self, source: Any, **kwargs: Any) -> Graph:
        # 1. Load the dataframe ---------------------------------------------------
        df = self._load_dataframe(source, **kwargs)
        if df.empty:
            raise ReadError(
                "Input data has no rows",
                source=str(source),
                reader_type=self.__class__.__name__,
            )

        # 2. Determine layout handler -------------------------------------------
        layout = getattr(self, "layout", "long")
        if layout not in ("long", "wide"):
            raise ReadError(
                f"Invalid layout '{layout}' – expected 'long' or 'wide'",
                source=str(source),
                reader_type=self.__class__.__name__,
            )

        mapping = self._resolve_mapping(kwargs)

        if layout == "long":
            return self._parse_long(df, source, mapping, **kwargs)
        return self._parse_wide(df, source, mapping, **kwargs)

    # ------------------------------------------------------------------
    # Long-format parser (rows = observations)
    # ------------------------------------------------------------------
    def _parse_long(
        self,
        df: pd.DataFrame,
        source_identifier: Any,
        mapping: dict[str, str],
        **kwargs: Any,
    ) -> Graph:
        """Parse a long-format DataFrame and populate a Graph."""
        item_col, period_col, value_col = self._resolve_long_columns(kwargs)

        self.validate_required_columns(
            df, [item_col, period_col, value_col], str(source_identifier)
        )

        df[period_col] = df[period_col].astype(str)
        periods = sorted(df[period_col].unique().tolist())
        self.validate_periods_exist(periods, str(source_identifier))
        graph = Graph(periods=periods)

        validator = ValidationResultCollector()
        grouped = df.groupby(item_col)
        for raw_name, group in grouped:
            ok, item_name = self.validate_node_name(raw_name)
            if not ok or item_name is None:
                continue
            node_name = self._apply_mapping(item_name, mapping)
            period_values: dict[str, float] = {}
            for _, row in group.iterrows():
                per = row[period_col]
                val_raw = row[value_col]
                ok_val, num = self.validate_numeric_value(
                    val_raw,
                    item_name,
                    per,
                    validator,
                    allow_conversion=self.allow_conversion,
                )
                if ok_val and num is not None:
                    period_values[str(per)] = float(num)
            if period_values:
                graph.add_node(
                    FinancialStatementItemNode(name=node_name, values=period_values)
                )

        if validator.has_errors():
            raise ReadError(
                self.create_validation_summary(validator, str(source_identifier)),
                source=str(source_identifier),
                reader_type=self.__class__.__name__,
            )
        logger.info(
            "Loaded %s nodes from long-format table (%s)",
            len(graph.nodes),
            source_identifier,
        )
        return graph

    # ------------------------------------------------------------------
    # Wide-format parser (rows = items, columns = periods)
    # ------------------------------------------------------------------
    def _extract_periods(self, df: pd.DataFrame, items_col_idx0: int) -> list[str]:
        """Extract period names from the columns of a wide-format DataFrame."""
        periods = [c for i, c in enumerate(df.columns) if i > items_col_idx0 and str(c)]
        return list(map(str, periods))

    def _parse_wide(
        self,
        df: pd.DataFrame,
        source_identifier: Any,
        mapping: dict[str, str],
        **kwargs: Any,
    ) -> Graph:
        """Parse a wide-format DataFrame and populate a Graph."""
        items_col_idx0 = self._resolve_wide_items_col(kwargs)
        self.validate_column_bounds(
            df, items_col_idx0, str(source_identifier), "items_col"
        )

        periods = self._extract_periods(df, items_col_idx0)
        self.validate_periods_exist(periods, str(source_identifier))
        graph = Graph(periods=periods)

        validator = ValidationResultCollector()
        nodes_added = 0
        for _, row in df.iterrows():
            raw_item = row.iloc[items_col_idx0]
            ok, item_name = self.validate_node_name(raw_item)
            if not ok or item_name is None:
                continue
            node_name = self._apply_mapping(item_name, mapping)
            period_values: dict[str, float] = {}
            for col_idx, period in enumerate(df.columns):
                if col_idx <= items_col_idx0:
                    continue
                val_raw = row[period]
                ok_val, num = self.validate_numeric_value(
                    val_raw,
                    item_name,
                    str(period),
                    validator,
                    allow_conversion=self.allow_conversion,
                )
                if ok_val and num is not None:
                    period_values[str(period)] = float(num)
            if period_values:
                graph.add_node(
                    FinancialStatementItemNode(name=node_name, values=period_values)
                )
                nodes_added += 1

        if validator.has_errors():
            raise ReadError(
                self.create_validation_summary(validator, str(source_identifier)),
                source=str(source_identifier),
                reader_type=self.__class__.__name__,
            )
        logger.info(
            "Loaded %s nodes from wide table (%s)", nodes_added, source_identifier
        )
        return graph


__all__ = ["DataFrameReaderBase"]
