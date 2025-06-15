"""Provide statistical node implementations for time-series analyses.

This module defines nodes that perform statistical operations on node values across periods:
- YoYGrowthNode: Compute year-over-year percentage growth.
- MultiPeriodStatNode: Compute statistics (mean, stddev) over multiple periods.
- TwoPeriodAverageNode: Compute simple average over two periods.
"""

import logging
import math
import statistics

# Use lowercase built-in types for annotations
from typing import Any, Callable, Optional, Union

from fin_statement_model.core.errors import CalculationError

# Use absolute imports
from fin_statement_model.core.nodes.base import Node

# Added logger instance
logger = logging.getLogger(__name__)

Numeric = Union[int, float]
StatFunc = Callable[
    ..., Any
]  # Widen callable type to accept any callable returning Numeric


class YoYGrowthNode(Node):
    """Compute year-over-year percentage growth.

    Compare values of an input node for two periods and compute
    (current_value - prior_value) / prior_value.

    Attributes:
        input_node (Node): Node providing source values.
        prior_period (str): Identifier for the earlier period.
        current_period (str): Identifier for the later period.

    Examples:
        >>> from fin_statement_model.core.nodes import FinancialStatementItemNode, YoYGrowthNode
        >>> data = {"2022": 100.0, "2023": 120.0}
        >>> base = FinancialStatementItemNode("revenue", data)
        >>> yoy = YoYGrowthNode("rev_yoy", input_node=base, prior_period="2022", current_period="2023")
        >>> round(yoy.calculate(), 2)
        0.2
    """

    def __init__(
        self, name: str, input_node: Node, prior_period: str, current_period: str
    ):
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
            raise TypeError(
                "YoYGrowthNode prior_period and current_period must be strings."
            )

        self.input_node = input_node
        self.prior_period = prior_period
        self.current_period = current_period

    def calculate(self, period: Optional[str] = None) -> float:
        """Compute the YoY growth rate.

        Ignore the `period` parameter; use configured periods.

        Args:
            period (str | None): Ignored.

        Returns:
            float: (current - prior) / prior, or NaN if prior is zero or non-finite.

        Raises:
            CalculationError: On errors retrieving or validating input values.
        """
        try:
            prior_value = self.input_node.calculate(self.prior_period)
            current_value = self.input_node.calculate(self.current_period)

            # Validate input types
            if not isinstance(prior_value, int | float):
                raise TypeError(
                    f"Prior period ('{self.prior_period}') value is non-numeric."
                )
            if not isinstance(current_value, int | float):
                raise TypeError(
                    f"Current period ('{self.current_period}') value is non-numeric."
                )

            # Handle division by zero or non-finite prior value
            if prior_value == 0 or not math.isfinite(prior_value):
                logger.warning(
                    f"YoYGrowthNode '{self.name}': Prior period '{self.prior_period}' value is zero or non-finite ({prior_value}). Returning NaN."
                )
                return float("nan")

            # Calculate growth
            growth = (float(current_value) - float(prior_value)) / float(prior_value)
            return growth

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

    @staticmethod
    def from_dict_with_context(
        data: dict[str, Any], context: dict[str, Node]
    ) -> "YoYGrowthNode":
        """Recreate a YoYGrowthNode from serialized data.

        Args:
            data (dict[str, Any]): Serialized node data.
            context (dict[str, Node]): Existing nodes for dependencies.

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

        if input_node_name not in context:
            raise ValueError(f"Input node '{input_node_name}' not found in context")

        input_node = context[input_node_name]
        prior_period = data.get("prior_period")
        current_period = data.get("current_period")

        if not prior_period:
            raise ValueError("Missing 'prior_period' field in YoYGrowthNode data")
        if not current_period:
            raise ValueError("Missing 'current_period' field in YoYGrowthNode data")

        return YoYGrowthNode(
            name=name,
            input_node=input_node,
            prior_period=prior_period,
            current_period=current_period,
        )


class MultiPeriodStatNode(Node):
    """Compute a statistical measure over multiple periods.

    Apply a statistical function (e.g., mean, stdev) to values from an input node across specified periods.

    Attributes:
        input_node (Node): Node providing source values.
        periods (list[str]): Period identifiers to include.
        stat_func (StatFunc): Function to apply to collected values.

    Examples:
        >>> from fin_statement_model.core.nodes import FinancialStatementItemNode, MultiPeriodStatNode
        >>> data = {"Q1": 10, "Q2": 12, "Q3": 11, "Q4": 13}
        >>> sales = FinancialStatementItemNode("sales", data)
        >>> avg = MultiPeriodStatNode("avg_sales", input_node=sales, periods=["Q1","Q2","Q3","Q4"], stat_func=statistics.mean)
        >>> avg.calculate()
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
            raise TypeError(
                "MultiPeriodStatNode stat_func must be a callable function."
            )

        self.input_node = input_node
        self.periods = periods
        self.stat_func = stat_func

    def calculate(self, period: Optional[str] = None) -> float:
        """Compute the statistical measure across specified periods.

        Args:
            period (str | None): Ignored.

        Returns:
            float: Result of `stat_func` on collected values, or NaN if insufficient valid data.

        Raises:
            CalculationError: If input retrieval fails or unexpected errors occur.
        """
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
                            f"MultiPeriodStatNode '{self.name}': Input '{self.input_node.name}' gave non-numeric/non-finite value ({value}) for period '{p}'. Skipping."
                        )
                except Exception as node_err:
                    # Log error fetching data for a specific period but continue
                    logger.error(
                        f"MultiPeriodStatNode '{self.name}': Error getting value for period '{p}' from '{self.input_node.name}': {node_err}",
                        exc_info=True,
                    )
                    retrieval_errors.append(p)

            # If no valid numeric values were collected
            if not values:
                logger.warning(
                    f"MultiPeriodStatNode '{self.name}': No valid numeric data points found across periods {self.periods}. Returning NaN."
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
                    f"MultiPeriodStatNode '{self.name}': Stat function '{self.stat_func.__name__}' failed ({stat_err}). Values: {values}. Returning NaN."
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

    @staticmethod
    def from_dict_with_context(
        data: dict[str, Any], context: dict[str, Node]
    ) -> "MultiPeriodStatNode":
        """Recreate a MultiPeriodStatNode from serialized data.

        Args:
            data (dict[str, Any]): Serialized node data.
            context (dict[str, Node]): Existing nodes for dependencies.

        Returns:
            MultiPeriodStatNode: Reconstructed node.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        if data.get("type") != "multi_period_stat":
            raise ValueError(
                f"Invalid type for MultiPeriodStatNode: {data.get('type')}"
            )

        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in MultiPeriodStatNode data")

        input_node_name = data.get("input_node_name")
        if not input_node_name:
            raise ValueError(
                "Missing 'input_node_name' field in MultiPeriodStatNode data"
            )

        if input_node_name not in context:
            raise ValueError(f"Input node '{input_node_name}' not found in context")

        input_node = context[input_node_name]
        periods = data.get("periods", [])
        stat_func_name = data.get("stat_func_name", "stdev")

        if not periods:
            raise ValueError(
                "Missing or empty 'periods' field in MultiPeriodStatNode data"
            )

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
                f"Unknown stat_func_name '{stat_func_name}' for MultiPeriodStatNode '{name}'. "
                f"Using default statistics.stdev."
            )

        return MultiPeriodStatNode(
            name=name,
            input_node=input_node,
            periods=periods,
            stat_func=stat_func,
        )


class TwoPeriodAverageNode(Node):
    """Compute the average of an input node's values over two periods.

    Attributes:
        input_node (Node): Node supplying values.
        period1 (str): Identifier for the first period.
        period2 (str): Identifier for the second period.

    Examples:
        >>> from fin_statement_model.core.nodes import FinancialStatementItemNode, TwoPeriodAverageNode
        >>> data = {"Jan": 10.0, "Feb": 11.0}
        >>> price = FinancialStatementItemNode("price", data)
        >>> avg = TwoPeriodAverageNode("avg_price", input_node=price, period1="Jan", period2="Feb")
        >>> avg.calculate()
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
            raise TypeError(
                f"TwoPeriodAverageNode input_node must be a Node instance, got {type(input_node).__name__}"
            )
        if not isinstance(period1, str) or not isinstance(period2, str):
            raise TypeError("TwoPeriodAverageNode period1 and period2 must be strings.")

        self.input_node = input_node
        self.period1 = period1
        self.period2 = period2

    def calculate(self, period: Optional[str] = None) -> float:
        """Compute the average value for the two configured periods.

        Args:
            period (str | None): Ignored.

        Returns:
            float: (value1 + value2) / 2, or NaN if either value is non-numeric.

        Raises:
            CalculationError: On errors retrieving input node values.
        """
        try:
            val1 = self.input_node.calculate(self.period1)
            val2 = self.input_node.calculate(self.period2)

            # Ensure values are numeric and finite
            if not isinstance(val1, int | float) or not math.isfinite(val1):
                logger.warning(
                    f"TwoPeriodAverageNode '{self.name}': Value for period '{self.period1}' is non-numeric/non-finite ({val1}). Returning NaN."
                )
                return float("nan")
            if not isinstance(val2, int | float) or not math.isfinite(val2):
                logger.warning(
                    f"TwoPeriodAverageNode '{self.name}': Value for period '{self.period2}' is non-numeric/non-finite ({val2}). Returning NaN."
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

    @staticmethod
    def from_dict_with_context(
        data: dict[str, Any], context: dict[str, Node]
    ) -> "TwoPeriodAverageNode":
        """Recreate a TwoPeriodAverageNode from serialized data.

        Args:
            data (dict[str, Any]): Serialized node data.
            context (dict[str, Node]): Existing nodes for dependencies.

        Returns:
            TwoPeriodAverageNode: Reconstructed node.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        if data.get("type") != "two_period_average":
            raise ValueError(
                f"Invalid type for TwoPeriodAverageNode: {data.get('type')}"
            )

        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in TwoPeriodAverageNode data")

        input_node_name = data.get("input_node_name")
        if not input_node_name:
            raise ValueError(
                "Missing 'input_node_name' field in TwoPeriodAverageNode data"
            )

        if input_node_name not in context:
            raise ValueError(f"Input node '{input_node_name}' not found in context")

        input_node = context[input_node_name]
        period1 = data.get("period1")
        period2 = data.get("period2")

        if not period1:
            raise ValueError("Missing 'period1' field in TwoPeriodAverageNode data")
        if not period2:
            raise ValueError("Missing 'period2' field in TwoPeriodAverageNode data")

        return TwoPeriodAverageNode(
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
