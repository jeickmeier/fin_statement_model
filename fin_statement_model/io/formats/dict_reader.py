"""Data reader for Python dictionaries.

This refactor removes the bespoke validation loop and instead leverages the
shared :class:`ValidationMixin` helpers used by other tabular readers.  The
behaviour (error reporting via :class:`ReadError`) remains identical but with
less duplicated code.
"""

from __future__ import annotations

import logging
from typing import Optional, Any

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io.core.base import DataReader
from fin_statement_model.io.core.registry import register_reader
from fin_statement_model.io.exceptions import ReadError
from fin_statement_model.io.config.models import DictReaderConfig
from fin_statement_model.io.core.mixins import (
    ValidationMixin,
    ValidationResultCollector,
    ConfigurationMixin,
    handle_read_errors,
)

logger = logging.getLogger(__name__)


@register_reader("dict", schema=DictReaderConfig)
class DictReader(DataReader, ValidationMixin, ConfigurationMixin):
    """Reads data from a Python dictionary to create a new Graph.

    Expects a dictionary format: {node_name: {period: value, ...}, ...}
    Creates FinancialStatementItemNode instances for each entry.

    Note:
        Configuration is handled via `DictReaderConfig` during initialization.
        The `read()` method takes the source dictionary directly and an optional
        `periods` keyword argument.
    """

    def __init__(self, cfg: Optional[DictReaderConfig] = None) -> None:
        """Initialize the DictReader.

        Args:
            cfg: Optional validated `DictReaderConfig` instance.
                 Currently unused but kept for registry symmetry and future options.
        """
        self.cfg = cfg

    @handle_read_errors()
    def read(self, source: dict[str, dict[str, float]], **kwargs: Any) -> Graph:
        """Read data from a dictionary and create a new Graph.

        This method expects the source dictionary to have a specific structure:
        `{node_name: {period: value, ...}, ...}`.

        It validates the structure of the input dictionary and the types of its
        keys and values. If any validation errors are found, it raises a `ReadError`
        with a detailed summary.

        If the data is valid, it constructs a new `Graph` object, populates it with
        `FinancialStatementItemNode` instances created from the dictionary data,
        and returns it.

        Args:
            source: A dictionary containing the graph data.
            **kwargs: Optional runtime arguments, such as `periods` to specify
                which periods to include in the resulting graph.

        Returns:
            A new `Graph` object populated with the data from the source dictionary.

        Raises:
            ReadError: If the source dictionary has an invalid format or contains
                non-numeric values.
        """

        # 1. Basic structure validation ------------------------------------------------
        if not isinstance(source, dict):
            raise ReadError(
                message="DictReader expects `source` to be a dict[str, dict[str, float]]",
                source="dict_input",
                reader_type="DictReader",
            )

        collector = ValidationResultCollector()
        all_periods: set[str] = set()

        # 2. Per-node validation --------------------------------------------------------
        for raw_name, period_values in source.items():
            ok_name, node_name = self.validate_node_name(raw_name)
            if not ok_name or node_name is None:
                collector.add_result(str(raw_name), False, "Invalid or empty node name")
                continue

            if not isinstance(period_values, dict):
                collector.add_result(
                    node_name,
                    False,
                    f"Expected dict for period values, got {type(period_values).__name__}",
                )
                continue

            for period_raw, value_raw in period_values.items():
                # period must be str
                if not isinstance(period_raw, str):
                    collector.add_result(
                        node_name,
                        False,
                        f"Invalid period key '{period_raw}' – expected str.",
                    )
                    continue

                ok_val, _ = self.validate_numeric_value(
                    value_raw, node_name, period_raw, collector, allow_conversion=False
                )
                if ok_val:
                    all_periods.add(period_raw)

        if collector.has_errors():
            raise ReadError(
                self.create_validation_summary(collector, "dict_input"),
                source="dict_input",
                reader_type="DictReader",
            )

        # 3. Graph creation ------------------------------------------------------------
        graph_periods = kwargs.get(
            "periods", self.cfg.periods if self.cfg else None
        ) or sorted(all_periods)

        graph = Graph(periods=graph_periods)

        for node_name, period_values in source.items():
            # Skip nodes that failed validation earlier
            if (
                collector.get_items_with_errors()
                and node_name in collector.get_items_with_errors()
            ):
                continue

            filtered_values = {
                p: v for p, v in period_values.items() if p in graph_periods
            }
            if filtered_values:
                graph.add_node(
                    FinancialStatementItemNode(
                        name=node_name, values=filtered_values.copy()
                    )
                )

        logger.info("Created graph with %s nodes from dictionary.", len(graph.nodes))
        return graph
