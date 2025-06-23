"""Provide statistical node implementations for time-series analyses.

This module defines nodes that perform statistical operations on node values across periods:
- YoYGrowthNode: Compute year-over-year percentage growth.
- MultiPeriodStatNode: Compute statistics (mean, stddev) over multiple periods.
- TwoPeriodAverageNode: Compute simple average over two periods.

Features:
    - YoYGrowthNode computes (current - prior) / prior for two periods.
    - MultiPeriodStatNode applies a statistical function (mean, stdev, etc.) to values across periods.
    - TwoPeriodAverageNode computes the average of two periods' values.
    - All nodes support serialization to and from dictionary representations.
    - All nodes provide dependency inspection and error handling.

Example:
    >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
    >>> from fin_statement_model.core.nodes.stats_nodes import YoYGrowthNode, MultiPeriodStatNode, TwoPeriodAverageNode
    >>> data = {"2022": 100.0, "2023": 120.0}
    >>> base = FinancialStatementItemNode("revenue", data)
    >>> yoy = YoYGrowthNode("rev_yoy", input_node=base, prior_period="2022", current_period="2023")
    >>> round(yoy.calculate(), 2)
    0.2
    >>> data2 = {"Q1": 10, "Q2": 12, "Q3": 11, "Q4": 13}
    >>> sales = FinancialStatementItemNode("sales", data2)
    >>> import statistics
    >>> avg = MultiPeriodStatNode(
    ...     "avg_sales", input_node=sales, periods=["Q1", "Q2", "Q3", "Q4"], stat_func=statistics.mean
    ... )
    >>> avg.calculate()
    11.5
    >>> avg2 = TwoPeriodAverageNode("avg2", input_node=sales, period1="Q1", period2="Q2")
    >>> avg2.calculate()
    11.0
"""

from collections.abc import Callable
import logging
import math
import statistics

# Use lowercase built-in types for annotations
from typing import Any

from fin_statement_model.core.errors import CalculationError
from fin_statement_model.core.node_factory.registries import node_type

# Use absolute imports
from fin_statement_model.core.nodes.base import Node

# Added logger instance
logger = logging.getLogger(__name__)

Numeric = int | float
StatFunc = Callable[..., Any]  # Widen callable type to accept any callable returning Numeric


@node_type("yoy_growth")
class YoYGrowthNode(Node):
    """Compute year-over-year percentage growth.

    Compare values of an input node for two periods and compute
    (current_value - prior_value) / prior_value.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary.
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> YoYGrowthNode`:
            Classmethod to deserialize a node from a dictionary. `context` is required to resolve input nodes.

    Attributes:
        input_node (Node): Node providing source values.
        prior_period (str): Identifier for the earlier period.
        current_period (str): Identifier for the later period.

    Example:
        >>> from fin_statement_model.core.nodes import FinancialStatementItemNode, YoYGrowthNode
        >>> data = {"2022": 100.0, "2023": 120.0}
        >>> base = FinancialStatementItemNode("revenue", data)
        >>> yoy = YoYGrowthNode("rev_yoy", input_node=base, prior_period="2022", current_period="2023")
        >>> d = yoy.to_dict()
        >>> yoy2 = YoYGrowthNode.from_dict(d, {"revenue": base})
        >>> round(yoy2.calculate(), 2)
        0.2
    """

    def __init__(self, name: str, input_node: Node, prior_period: str, current_period: str):
        """Create a YoYGrowthNode.

        Args:
            name (str): Unique identifier for this node.
            input_node (Node): Node supplying values for comparison.
            prior_period (str): Identifier for the earlier period.
            current_period (str): Identifier for the later period.

        Raises:
            TypeError: If `input_node` is not a Node or periods are not strings.
        """
        super().__init__(name)
        if not isinstance(input_node, Node):
            raise TypeError("YoYGrowthNode input_node must be a Node instance.")
        if not isinstance(prior_period, str) or not isinstance(current_period, str):
            raise TypeError("YoYGrowthNode prior_period and current_period must be strings.")

        self.input_node = input_node
        self.prior_period = prior_period
        self.current_period = current_period

    def calculate(self, period: str | None = None) -> float:
        """Compute the YoY growth rate.

        Ignore the `period` parameter; use configured periods.

        Args:
            period (str | None): Ignored.

        Returns:
            float: (current - prior) / prior, or NaN if prior is zero or non-finite.

        Raises:
            CalculationError: On errors retrieving or validating input values.
        """
        _ = period  # Parameter intentionally unused
        try:
            prior_value = self.input_node.calculate(self.prior_period)
            current_value = self.input_node.calculate(self.current_period)

            # Validate input types
            if not isinstance(prior_value, int | float):
                raise TypeError(f"Prior period ('{self.prior_period}') value is non-numeric.")
            if not isinstance(current_value, int | float):
                raise TypeError(f"Current period ('{self.current_period}') value is non-numeric.")

            # Handle division by zero or non-finite prior value
            if prior_value == 0 or not math.isfinite(prior_value):
                logger.warning(
                    "YoYGrowthNode '%s': Prior period '%s' value is zero or non-finite (%s). Returning NaN.",
                    self.name,
                    self.prior_period,
                    prior_value,
                )
                return float("nan")

            # Calculate growth
            growth = (float(current_value) - float(prior_value)) / float(prior_value)
        except Exception as e:
            # Wrap any exception during calculation
            raise CalculationError(
                message=f"Failed to calculate YoY growth for node '{self.name}'",
                node_id=self.name,
                period=f"{self.prior_period}_to_{self.current_period}",  # Indicate period span
                details={
                    "input_node": self.input_node.name,
                    "prior_period": self.prior_period,
                    "current_period": self.current_period,
                    "original_error": str(e),
                },
            ) from e
        else:
            return growth

    def get_dependencies(self) -> list[str]:
        """Get names of nodes this node depends on."""
        return [self.input_node.name]

    def to_dict(self) -> dict[str, Any]:
        """Serialize this node to a dictionary.

        Returns:
            dict[str, Any]: Serialized representation with type, name, and periods.
        """
        return {
            "type": "yoy_growth",
            "name": self.name,
            "input_node_name": self.input_node.name,
            "prior_period": self.prior_period,
            "current_period": self.current_period,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, Node] | None = None,
    ) -> "YoYGrowthNode":
        """Recreate a YoYGrowthNode from serialized data.

        Args:
            data (dict[str, Any]): Serialized node data.
            context (dict[str, Node] | None): Existing nodes for dependencies.

        Returns:
            YoYGrowthNode: Reconstructed node.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        if data.get("type") != "yoy_growth":
            raise ValueError(f"Invalid type for YoYGrowthNode: {data.get('type')}")

        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in YoYGrowthNode data")

        input_node_name = data.get("input_node_name")
        if not input_node_name:
            raise ValueError("Missing 'input_node_name' field in YoYGrowthNode data")

        if context is None:
            raise ValueError("'context' must be provided to deserialize YoYGrowthNode")
        input_node = context[input_node_name]

        prior_period = data.get("prior_period")
        current_period = data.get("current_period")

        if not prior_period:
            raise ValueError("Missing 'prior_period' field in YoYGrowthNode data")
        if not current_period:
            raise ValueError("Missing 'current_period' field in YoYGrowthNode data")

        return cls(
            name=name,
            input_node=input_node,
            prior_period=prior_period,
            current_period=current_period,
        )


@node_type("multi_period_stat")
class MultiPeriodStatNode(Node):
    """Compute a statistical measure over multiple periods.

    Apply a statistical function (e.g., mean, stdev) to values from an input node across specified periods.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary (includes a warning if stat_func is custom).
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> MultiPeriodStatNode`:
            Classmethod to deserialize a node from a dictionary. `context` is required to resolve input nodes. Custom stat functions may require manual reconstruction.

    Attributes:
        input_node (Node): Node providing source values.
        periods (list[str]): Period identifiers to include.
        stat_func (StatFunc): Function to apply to collected values.

    Example:
        >>> from fin_statement_model.core.nodes import FinancialStatementItemNode, MultiPeriodStatNode
        >>> data = {"Q1": 10, "Q2": 12, "Q3": 11, "Q4": 13}
        >>> sales = FinancialStatementItemNode("sales", data)
        >>> import statistics
        >>> avg = MultiPeriodStatNode(
        ...     "avg_sales", input_node=sales, periods=["Q1", "Q2", "Q3", "Q4"], stat_func=statistics.mean
        ... )
        >>> d = avg.to_dict()
        >>> avg2 = MultiPeriodStatNode.from_dict(d, {"sales": sales})
        >>> avg2.calculate()
        11.5
    """

    def __init__(
        self,
        name: str,
        input_node: Node,
        periods: list[str],
        stat_func: StatFunc = statistics.stdev,  # Default to standard deviation
    ):
        """Create a MultiPeriodStatNode.

        Args:
            name (str): Unique identifier for this node.
            input_node (Node): Node supplying values.
            periods (list[str]): Period identifiers to analyze.
            stat_func (StatFunc): Function applied to collected values. Defaults to statistics.stdev.

        Raises:
            ValueError: If `periods` is empty or not a list.
            TypeError: If `input_node` is not a Node or `stat_func` is not callable.
        """
        super().__init__(name)
        if not isinstance(input_node, Node):
            raise TypeError("MultiPeriodStatNode input_node must be a Node instance.")
        if not isinstance(periods, list) or not periods:
            raise ValueError("MultiPeriodStatNode periods must be a non-empty list.")
        if not all(isinstance(p, str) for p in periods):
            raise TypeError("MultiPeriodStatNode periods must contain only strings.")
        if not callable(stat_func):
            raise TypeError("MultiPeriodStatNode stat_func must be a callable function.")

        self.input_node = input_node
        self.periods = periods
        self.stat_func = stat_func

    def calculate(self, period: str | None = None) -> float:
        """Compute the statistical measure across specified periods.

        Args:
            period (str | None): Ignored.

        Returns:
            float: Result of `stat_func` on collected values, or NaN if insufficient valid data.

        Raises:
            CalculationError: If input retrieval fails or unexpected errors occur.
        """
        _ = period  # Parameter intentionally unused
        values: list[Numeric] = []
        retrieval_errors = []
        try:
            for p in self.periods:
                try:
                    value = self.input_node.calculate(p)
                    if isinstance(value, int | float) and math.isfinite(value):
                        values.append(float(value))
                    else:
                        # Log non-numeric/non-finite values but continue if possible
                        logger.warning(
                            "MultiPeriodStatNode '%s': Input '%s' gave non-numeric/non-finite value (%s) for period '%s'. Skipping.",
                            self.name,
                            self.input_node.name,
                            value,
                            p,
                        )
                except Exception:
                    # Log error fetching data for a specific period but continue
                    logger.exception(
                        "MultiPeriodStatNode '%s': Error getting value for period '%s' from '%s'",
                        self.name,
                        p,
                        self.input_node.name,
                    )
                    retrieval_errors.append(p)

            # If no valid numeric values were collected
            if not values:
                logger.warning(
                    "MultiPeriodStatNode '%s': No valid numeric data points found across periods %s. Returning NaN.",
                    self.name,
                    self.periods,
                )
                return float("nan")

            # Attempt the statistical calculation
            try:
                result = self.stat_func(values)
                # Ensure result is float, handle potential NaN from stat_func
                return float(result) if math.isfinite(result) else float("nan")
            except (statistics.StatisticsError, ValueError, TypeError) as stat_err:
                # Handle errors specific to statistical functions (e.g., stdev needs >= 2 points)
                logger.warning(
                    "MultiPeriodStatNode '%s': Stat function '%s' failed (%s). Values: %s. Returning NaN.",
                    self.name,
                    self.stat_func.__name__,
                    stat_err,
                    values,
                )
                return float("nan")

        except Exception as e:
            # Catch any other unexpected errors during the process
            raise CalculationError(
                message=f"Failed to calculate multi-period stat for node '{self.name}'",
                node_id=self.name,
                period="multi-period",  # Indicate calculation context
                details={
                    "input_node": self.input_node.name,
                    "periods": self.periods,
                    "stat_func": self.stat_func.__name__,
                    "collected_values_count": len(values),
                    "retrieval_errors_periods": retrieval_errors,
                    "original_error": str(e),
                },
            ) from e

    def get_dependencies(self) -> list[str]:
        """Get names of nodes this statistical node depends on."""
        return [self.input_node.name]

    def to_dict(self) -> dict[str, Any]:
        """Serialize this node to a dictionary.

        Returns:
            dict[str, Any]: Serialized data with function name and periods.

        Note:
            `stat_func` may not be fully serializable; manual reconstruction may be required.
        """
        return {
            "type": "multi_period_stat",
            "name": self.name,
            "input_node_name": self.input_node.name,
            "periods": self.periods.copy(),
            "stat_func_name": self.stat_func.__name__,
            "serialization_warning": (
                "MultiPeriodStatNode uses a statistical function which may not be fully serializable. "
                "Manual reconstruction may be required for custom functions."
            ),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, Node] | None = None,
    ) -> "MultiPeriodStatNode":
        """Recreate a MultiPeriodStatNode from serialized data.

        Args:
            data (dict[str, Any]): Serialized node data.
            context (dict[str, Node] | None): Existing nodes for dependencies.

        Returns:
            MultiPeriodStatNode: Reconstructed node.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        if data.get("type") != "multi_period_stat":
            raise ValueError(f"Invalid type for MultiPeriodStatNode: {data.get('type')}")

        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in MultiPeriodStatNode data")

        input_node_name = data.get("input_node_name")
        if not input_node_name:
            raise ValueError("Missing 'input_node_name' field in MultiPeriodStatNode data")

        if context is None:
            raise ValueError("'context' must be provided to deserialize MultiPeriodStatNode")
        if input_node_name not in context:
            raise ValueError(f"Input node '{input_node_name}' not found in context")

        input_node = context[input_node_name]
        periods = data.get("periods", [])
        stat_func_name = data.get("stat_func_name", "stdev")

        if not periods:
            raise ValueError("Missing or empty 'periods' field in MultiPeriodStatNode data")

        # Map common statistical function names to their implementations
        stat_func_map: dict[str, StatFunc] = {
            "mean": statistics.mean,
            "stdev": statistics.stdev,
            "median": statistics.median,
            "variance": statistics.variance,
            "pstdev": statistics.pstdev,
            "pvariance": statistics.pvariance,
        }

        stat_func = stat_func_map.get(stat_func_name, statistics.stdev)
        if stat_func_name not in stat_func_map:
            logger.warning(
                "Unknown stat_func_name '%s' for MultiPeriodStatNode '%s'. Using default statistics.stdev.",
                stat_func_name,
                name,
            )

        return cls(
            name=name,
            input_node=input_node,
            periods=periods,
            stat_func=stat_func,
        )


@node_type("two_period_average")
class TwoPeriodAverageNode(Node):
    """Compute the average of an input node's values over two periods.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary.
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> TwoPeriodAverageNode`:
            Classmethod to deserialize a node from a dictionary. `context` is required to resolve input nodes.

    Attributes:
        input_node (Node): Node supplying values.
        period1 (str): Identifier for the first period.
        period2 (str): Identifier for the second period.

    Example:
        >>> from fin_statement_model.core.nodes import FinancialStatementItemNode, TwoPeriodAverageNode
        >>> data = {"Jan": 10.0, "Feb": 11.0}
        >>> price = FinancialStatementItemNode("price", data)
        >>> avg = TwoPeriodAverageNode("avg_price", input_node=price, period1="Jan", period2="Feb")
        >>> d = avg.to_dict()
        >>> avg2 = TwoPeriodAverageNode.from_dict(d, {"price": price})
        >>> avg2.calculate()
        10.5
    """

    def __init__(self, name: str, input_node: Node, period1: str, period2: str):
        """Create a TwoPeriodAverageNode.

        Args:
            name (str): Unique identifier for the node.
            input_node (Node): Node supplying values.
            period1 (str): Identifier for the first period.
            period2 (str): Identifier for the second period.

        Raises:
            TypeError: If `input_node` is not a Node or periods are not strings.
        """
        super().__init__(name)
        if not isinstance(input_node, Node):
            raise TypeError(f"TwoPeriodAverageNode input_node must be a Node instance, got {type(input_node).__name__}")
        if not isinstance(period1, str) or not isinstance(period2, str):
            raise TypeError("TwoPeriodAverageNode period1 and period2 must be strings.")

        self.input_node = input_node
        self.period1 = period1
        self.period2 = period2

    def calculate(self, period: str | None = None) -> float:
        """Compute the average value for the two configured periods.

        Args:
            period (str | None): Ignored.

        Returns:
            float: (value1 + value2) / 2, or NaN if either value is non-numeric.

        Raises:
            CalculationError: On errors retrieving input node values.
        """
        _ = period  # Parameter intentionally unused
        try:
            val1 = self.input_node.calculate(self.period1)
            val2 = self.input_node.calculate(self.period2)

            # Ensure values are numeric and finite
            if not isinstance(val1, int | float) or not math.isfinite(val1):
                logger.warning(
                    "TwoPeriodAverageNode '%s': Value for period '%s' is non-numeric/non-finite (%s). Returning NaN.",
                    self.name,
                    self.period1,
                    val1,
                )
                return float("nan")
            if not isinstance(val2, int | float) or not math.isfinite(val2):
                logger.warning(
                    "TwoPeriodAverageNode '%s': Value for period '%s' is non-numeric/non-finite (%s). Returning NaN.",
                    self.name,
                    self.period2,
                    val2,
                )
                return float("nan")

            # Calculate the average
            return (float(val1) + float(val2)) / 2.0

        except Exception as e:
            # Wrap potential errors during input node calculation
            raise CalculationError(
                message=f"Failed to calculate two-period average for node '{self.name}'",
                node_id=self.name,
                period=f"{self.period1}_and_{self.period2}",  # Indicate context
                details={
                    "input_node": self.input_node.name,
                    "period1": self.period1,
                    "period2": self.period2,
                    "original_error": str(e),
                },
            ) from e

    def get_dependencies(self) -> list[str]:
        """Get names of nodes this average node depends on."""
        return [self.input_node.name]

    def to_dict(self) -> dict[str, Any]:
        """Serialize this node to a dictionary.

        Returns:
            dict[str, Any]: Serialized representation with type, name, and periods.
        """
        return {
            "type": "two_period_average",
            "name": self.name,
            "input_node_name": self.input_node.name,
            "period1": self.period1,
            "period2": self.period2,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, Node] | None = None,
    ) -> "TwoPeriodAverageNode":
        """Recreate a TwoPeriodAverageNode from serialized data.

        Args:
            data (dict[str, Any]): Serialized node data.
            context (dict[str, Node] | None): Existing nodes for dependencies.

        Returns:
            TwoPeriodAverageNode: Reconstructed node.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        if data.get("type") != "two_period_average":
            raise ValueError(f"Invalid type for TwoPeriodAverageNode: {data.get('type')}")

        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in TwoPeriodAverageNode data")

        input_node_name = data.get("input_node_name")
        if not input_node_name:
            raise ValueError("Missing 'input_node_name' field in TwoPeriodAverageNode data")

        if context is None:
            raise ValueError("'context' must be provided to deserialize TwoPeriodAverageNode")
        if input_node_name not in context:
            raise ValueError(f"Input node '{input_node_name}' not found in context")

        input_node = context[input_node_name]
        period1 = data.get("period1")
        period2 = data.get("period2")

        if not period1:
            raise ValueError("Missing 'period1' field in TwoPeriodAverageNode data")
        if not period2:
            raise ValueError("Missing 'period2' field in TwoPeriodAverageNode data")

        return cls(
            name=name,
            input_node=input_node,
            period1=period1,
            period2=period2,
        )


__all__ = [
    "MultiPeriodStatNode",
    "TwoPeriodAverageNode",
    "YoYGrowthNode",
]
