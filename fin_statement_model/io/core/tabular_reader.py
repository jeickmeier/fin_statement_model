"""Shared logic for CSV-style *long format* readers.

A *tabular* reader loads a pandas.DataFrame where **each row** represents a
single data point identified by item, period, and value columns.  Concrete
subclasses only implement `_load_dataframe()` to fetch that DataFrame; the rest
of the graph-building pipeline is handled here.
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


class TabularReader(
    FileBasedReader,
    ConfigurationMixin,
    MappingAwareMixin,
    ValidationMixin,
    ABC,
):
    """Abstract helper for *long-format* financial data tables."""

    # ------------------------------------------------------------------
    # Sub-class hooks
    # ------------------------------------------------------------------
    @abstractmethod
    def _load_dataframe(self, source: Any, **kwargs: Any) -> pd.DataFrame:  # noqa: D401
        """Return the raw DataFrame loaded from *source*.

        Sub-classes implement actual IO (e.g. `pd.read_csv`, `pd.read_excel`).
        """

    # Column names expected in cfg or kwargs -----------------------------
    item_col_attr = "item_col"
    period_col_attr = "period_col"
    value_col_attr = "value_col"

    @handle_read_errors()
    def read(self, source: Any, **kwargs: Any) -> Graph:
        # ------------------------------------------------------------------
        # 1. Load DataFrame -------------------------------------------------
        df = self._load_dataframe(source, **kwargs)
        if df.empty:
            raise ReadError(
                "Input data has no rows",
                source=str(source),
                reader_type=self.__class__.__name__,
            )

        # ------------------------------------------------------------------
        # 2. Resolve column names ------------------------------------------
        item_col = cast(
            str,
            kwargs.get(self.item_col_attr)
            or self.get_config_value(self.item_col_attr, required=True),
        )
        period_col = cast(
            str,
            kwargs.get(self.period_col_attr)
            or self.get_config_value(self.period_col_attr, required=True),
        )
        value_col = cast(
            str,
            kwargs.get(self.value_col_attr)
            or self.get_config_value(self.value_col_attr, required=True),
        )

        self.validate_required_columns(
            df, [item_col, period_col, value_col], str(source)
        )

        # ------------------------------------------------------------------
        # 3. Build periods list --------------------------------------------
        df[period_col] = df[period_col].astype(str)
        periods = sorted(df[period_col].unique().tolist())
        self.validate_periods_exist(periods, str(source))
        graph = Graph(periods=periods)

        # Mapping context (statement_type optional)
        mapping_ctx = kwargs.get(
            "statement_type", self.get_config_value("statement_type")
        )
        mapping = self._get_mapping(mapping_ctx)

        # ------------------------------------------------------------------
        # 4. Iterate rows and build nodes ----------------------------------
        validator = ValidationResultCollector()
        grouped = df.groupby(item_col)
        for item_name_raw, group in grouped:
            is_valid, item_name = self.validate_node_name(item_name_raw)
            if not is_valid or item_name is None:
                continue
            node_name = self._apply_mapping(item_name, mapping)
            period_values: dict[str, float] = {}
            for _, row in group.iterrows():
                period = row[period_col]
                raw_val = row[value_col]
                ok, val = self.validate_numeric_value(
                    raw_val, item_name, period, validator, allow_conversion=True
                )
                if ok and val is not None:
                    period_values[period] = float(val)
            if period_values:
                graph.add_node(
                    FinancialStatementItemNode(name=node_name, values=period_values)
                )

        if validator.has_errors():
            raise ReadError(
                self.create_validation_summary(validator, str(source)),
                source=str(source),
                reader_type=self.__class__.__name__,
            )

        logger.info(
            "Loaded %s nodes from long-format table (%s)", len(graph.nodes), source
        )
        return graph


__all__ = ["TabularReader"]
