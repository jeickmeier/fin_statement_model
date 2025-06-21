"""Shared logic for *wide format* readers (rows = items, columns = periods)."""

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


class WideTableReader(
    FileBasedReader,
    ConfigurationMixin,
    MappingAwareMixin,
    ValidationMixin,
    ABC,
):
    """Base class for table layouts where **rows** = items and **columns** = periods."""

    # Expected config names
    items_col_attr = (
        "items_col"  # 1-indexed int specifying column of item names (default 1)
    )

    # ------------------------------------------------------------------
    # Hooks sub-classes must implement
    # ------------------------------------------------------------------
    @abstractmethod
    def _load_dataframe(self, source: Any, **kwargs: Any) -> pd.DataFrame:  # noqa: D401
        """Return DataFrame such that items row labels are accessible via iloc[:, items_col]."""

    # Helper to extract periods from dataframe header (allows override)
    def _extract_periods(
        self, df: pd.DataFrame, items_col_idx: int
    ) -> list[str]:  # noqa: D401
        periods = [
            c for i, c in enumerate(df.columns) if i > items_col_idx and str(c).strip()
        ]
        return list(map(str, periods))

    # ------------------------------------------------------------------
    # Main reader entry point
    # ------------------------------------------------------------------
    @handle_read_errors()
    def read(self, source: Any, **kwargs: Any) -> Graph:
        df = self._load_dataframe(source, **kwargs)
        if df.empty:
            raise ReadError(
                "Input sheet has no data rows",
                source=str(source),
                reader_type=self.__class__.__name__,
            )

        items_col_idx_1 = cast(
            int,
            kwargs.get(self.items_col_attr)
            or self.get_config_value(self.items_col_attr, default=1, value_type=int),
        )
        if items_col_idx_1 < 1:
            raise ReadError(
                "items_col must be >=1",
                source=str(source),
                reader_type=self.__class__.__name__,
            )
        items_col_idx0 = items_col_idx_1 - 1

        self.validate_column_bounds(
            df, items_col_idx0, str(source), context="items_col"
        )

        periods = self._extract_periods(df, items_col_idx0)
        self.validate_periods_exist(periods, str(source))
        graph = Graph(periods=periods)

        mapping_ctx = kwargs.get(
            "statement_type", self.get_config_value("statement_type")
        )
        mapping = self._get_mapping(mapping_ctx)

        validator = ValidationResultCollector()
        nodes_added = 0
        for idx, row in df.iterrows():
            item_raw = row.iloc[items_col_idx0]
            valid, item_name = self.validate_node_name(item_raw)
            if not valid or item_name is None:
                continue
            node_name = self._apply_mapping(item_name, mapping)
            period_values: dict[str, float] = {}
            for col_idx, period in enumerate(df.columns):
                if col_idx <= items_col_idx0:
                    continue
                value = row[period]
                ok, num = self.validate_numeric_value(
                    value, item_name, str(period), validator, allow_conversion=True
                )
                if ok and num is not None:
                    period_values[str(period)] = float(num)
            if period_values:
                graph.add_node(
                    FinancialStatementItemNode(name=node_name, values=period_values)
                )
                nodes_added += 1

        if validator.has_errors():
            raise ReadError(
                self.create_validation_summary(validator, str(source)),
                source=str(source),
                reader_type=self.__class__.__name__,
            )
        logger.info("Loaded %s nodes from wide table (%s)", nodes_added, source)
        return graph


__all__ = ["WideTableReader"]
