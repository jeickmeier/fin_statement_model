"""Period inference and management utilities for forecasting.

This module provides tools for inferring historical and forecast periods, determining base periods,
validating period sequences, and ensuring that required periods exist in the financial statement graph.

Features:
    - Infer historical periods from graph state and forecast periods
    - Determine the base period for forecasting (supports multiple strategies)
    - Validate period sequences for duplicates and emptiness
    - Ensure forecast periods exist in the graph, optionally adding them

Example:
    >>> from fin_statement_model.forecasting.period_manager import PeriodManager
    >>> class DummyGraph:
    ...     periods = ["2022", "2023", "2024"]
    ...     def add_periods(self, periods): self.periods.extend(periods)
    >>> graph = DummyGraph()
    >>> PeriodManager.infer_historical_periods(graph, ["2024"])
    ['2022', '2023']
    >>> PeriodManager.ensure_periods_exist(graph, ["2025"], add_missing=True)
    ['2025']
"""

import logging
from typing import Any, Optional

from fin_statement_model.core.nodes import Node
from fin_statement_model.config.access import cfg

logger = logging.getLogger(__name__)


class PeriodManager:
    """Infer and manage forecasting periods.

    Provides utilities to infer historical periods, determine base periods,
    validate period sequences, and manage period transitions on the graph.
    """

    @staticmethod
    def infer_historical_periods(
        graph: Any,
        forecast_periods: list[str],
        provided_periods: Optional[list[str]] = None,
    ) -> list[str]:
        """Infer historical periods from graph state.

        Args:
            graph: The financial statement graph instance.
            forecast_periods: List of periods to forecast.
            provided_periods: Optional explicitly provided historical periods.

        Returns:
            List of historical periods.

        Raises:
            ValueError: If historical periods cannot be determined.

        Example:
            >>> class DummyGraph:
            ...     periods = ["2022", "2023", "2024"]
            >>> PeriodManager.infer_historical_periods(DummyGraph, ["2024"])
            ['2022', '2023']
        """
        # If explicitly provided, use them
        if provided_periods is not None:
            logger.debug(
                f"Using explicitly provided historical periods: {provided_periods}"
            )
            return provided_periods

        # Infer from graph periods and forecast periods
        if not hasattr(graph, "periods") or not graph.periods:
            raise ValueError(
                "Cannot infer historical periods: graph has no periods attribute"
            )

        if not forecast_periods:
            raise ValueError(
                "Cannot infer historical periods: no forecast periods provided"
            )

        # Try to find where forecast periods start
        first_forecast = forecast_periods[0]
        try:
            idx = graph.periods.index(first_forecast)
            historical_periods = graph.periods[:idx]
            logger.debug(
                f"Inferred historical periods by splitting at {first_forecast}: "
                f"{historical_periods}"
            )
        except ValueError:
            # First forecast period not in graph periods
            # Assume all current periods are historical
            historical_periods = list(graph.periods)
            logger.warning(
                f"First forecast period {first_forecast} not found in graph periods. "
                f"Using all existing periods as historical: {historical_periods}"
            )

        if not historical_periods:
            raise ValueError(
                "No historical periods found. Ensure graph has periods before "
                "the first forecast period."
            )

        return historical_periods

    @staticmethod
    def determine_base_period(
        node: Node,
        historical_periods: list[str],
        preferred_period: Optional[str] = None,
    ) -> str:
        """Determine the base period for forecasting a node.

        Args:
            node: The node to forecast.
            historical_periods: List of available historical periods.
            preferred_period: Optional preferred base period.

        Returns:
            The base period to use for forecasting.

        Raises:
            ValueError: If no valid base period can be determined.

        Example:
            >>> class DummyNode:
            ...     name = "revenue"
            ...     values = {"2022": 100, "2023": 110}
            >>> PeriodManager.determine_base_period(DummyNode, ["2022", "2023"])
            '2023'
        """
        if not historical_periods:
            raise ValueError("No historical periods provided")

        # Determine strategy for selecting base period
        strategy = cfg("forecasting.base_period_strategy")

        # Validate strategy
        valid_strategies = {
            "preferred_then_most_recent",
            "most_recent",
            "last_historical",
        }
        if strategy not in valid_strategies:
            logger.warning(
                f"Unknown base period strategy '{strategy}', falling back to 'preferred_then_most_recent'"
            )
            strategy = "preferred_then_most_recent"

        # 1. preferred_then_most_recent: check preferred first
        if strategy == "preferred_then_most_recent" and preferred_period:
            if preferred_period in historical_periods and hasattr(node, "values"):
                values = getattr(node, "values", {})
                if isinstance(values, dict) and preferred_period in values:
                    return preferred_period

        # 2. most_recent: pick most recent available data
        if strategy in ("preferred_then_most_recent", "most_recent"):
            if hasattr(node, "values") and isinstance(
                getattr(node, "values", None), dict
            ):
                values_dict = node.values
                available_periods = [p for p in historical_periods if p in values_dict]
                if available_periods:
                    return available_periods[-1]

        # 3. last_historical: always use last in historical_periods
        if strategy == "last_historical":
            return historical_periods[-1]

        # Final fallback: use last historical period
        base_period = historical_periods[-1]
        logger.info(
            f"Using last historical period as base for {node.name}: {base_period} "
            "(node may lack values)"
        )
        return base_period

    @staticmethod
    def validate_period_sequence(periods: list[str]) -> None:
        """Validate that a period sequence is valid.

        Args:
            periods: List of periods to validate.

        Raises:
            ValueError: If the period sequence is invalid.

        Example:
            >>> PeriodManager.validate_period_sequence(["2022", "2023", "2024"])
            >>> PeriodManager.validate_period_sequence(["2022", "2022"])
            Traceback (most recent call last):
                ...
            ValueError: Period sequence contains duplicates: {'2022'}
        """
        if not periods:
            raise ValueError("Period sequence cannot be empty")

        if len(periods) != len(set(periods)):
            duplicates = [p for p in periods if periods.count(p) > 1]
            raise ValueError(f"Period sequence contains duplicates: {set(duplicates)}")

    @staticmethod
    def get_period_index(period: str, periods: list[str]) -> int:
        """Get the index of a period in a period list.

        Args:
            period: The period to find.
            periods: List of periods.

        Returns:
            The index of the period.

        Raises:
            ValueError: If period not found in list.

        Example:
            >>> PeriodManager.get_period_index("2023", ["2022", "2023", "2024"])
            1
        """
        try:
            return periods.index(period)
        except ValueError:
            raise ValueError(f"Period '{period}' not found in period list") from None

    @staticmethod
    def ensure_periods_exist(
        graph: Any, periods: list[str], add_missing: bool = True
    ) -> list[str]:
        """Ensure periods exist in the graph.

        Args:
            graph: The financial statement graph instance.
            periods: List of periods that should exist.
            add_missing: Whether to add missing periods to the graph.

        Returns:
            List of periods that were added (empty if none).

        Raises:
            ValueError: If add_missing is False and periods are missing.

        Example:
            >>> class DummyGraph:
            ...     periods = ["2022", "2023"]
            ...     def add_periods(self, periods): self.periods.extend(periods)
            >>> graph = DummyGraph()
            >>> PeriodManager.ensure_periods_exist(graph, ["2024"], add_missing=True)
            ['2024']
        """
        if not hasattr(graph, "periods"):
            raise ValueError("Graph does not have a periods attribute")

        existing_periods = set(graph.periods)
        missing_periods = [p for p in periods if p not in existing_periods]

        if missing_periods:
            if add_missing:
                # Add missing periods to graph
                if hasattr(graph, "add_periods") and callable(graph.add_periods):
                    graph.add_periods(missing_periods)
                    logger.info(f"Added missing periods to graph: {missing_periods}")
                else:
                    raise ValueError(
                        f"Graph is missing periods {missing_periods} but has no add_periods method"
                    )
            else:
                raise ValueError(
                    f"The following periods do not exist in the graph: {missing_periods}"
                )

        return missing_periods
