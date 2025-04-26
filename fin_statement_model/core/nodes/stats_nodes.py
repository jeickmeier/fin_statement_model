"""Provide nodes for statistical calculations on financial data across periods.

This module provides nodes for common time-series statistical analyses:
- `YoYGrowthNode`: Calculates year-over-year percentage growth.
- `MultiPeriodStatNode`: Computes statistics (mean, stddev, etc.) over a range of periods.
- `TwoPeriodAverageNode`: Calculates the simple average over two specific periods.
"""

import logging
import math
import statistics

# Use lowercase built-in types for annotations
from typing import Optional, Callable, Union
from collections.abc import Sequence

# Use absolute imports
from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.errors import CalculationError

# Added logger instance
logger = logging.getLogger(__name__)

Numeric = Union[int, float]
StatFunc = Callable[[Sequence[Numeric]], Numeric]


class YoYGrowthNode(Node):
    """Calculate year-over-year (YoY) percentage growth.

    Compares the value of an input node between two specified periods
    (prior and current) and calculates the relative change.

    Growth = (Current Value - Prior Value) / Prior Value

    Attributes:
        name (str): The node's identifier.
        input_node (Node): The node providing the values for comparison.
        prior_period (str): Identifier for the earlier time period.
        current_period (str): Identifier for the later time period.

    Examples:
        >>> # Assume revenue_node holds {"2022": 100, "2023": 120}
        >>> revenue_node = FinancialStatementItemNode("revenue", {"2022": 100.0, "2023": 120.0})
        >>> yoy_growth = YoYGrowthNode(
        ...     "revenue_yoy",
        ...     input_node=revenue_node,
        ...     prior_period="2022",
        ...     current_period="2023"
        ... )
        >>> print(yoy_growth.calculate("any_period")) # Period arg is ignored
        0.2
    """

    def __init__(self, name: str, input_node: Node, prior_period: str, current_period: str):
        """Initialize the YoY Growth node.

        Args:
            name (str): The identifier for this growth node.
            input_node (Node): The node whose values will be compared.
            prior_period (str): The identifier for the earlier period.
            current_period (str): The identifier for the later period.

        Raises:
            TypeError: If `input_node` is not a Node instance or periods are not strings.
        """
        super().__init__(name)
        if not isinstance(input_node, Node):
            raise TypeError("YoYGrowthNode input_node must be a Node instance.")
        if not isinstance(prior_period, str) or not isinstance(current_period, str):
            raise TypeError("YoYGrowthNode prior_period and current_period must be strings.")

        self.input_node = input_node
        self.prior_period = prior_period
        self.current_period = current_period

    def calculate(self, period: Optional[str] = None) -> float:
        """Calculate the year-over-year growth rate.

        Retrieves values for the prior and current periods from the input node
        and computes the percentage growth. The `period` argument is ignored
        as the calculation periods are fixed during initialization.

        Args:
            period (Optional[str]): Ignored. The calculation uses the periods
                defined during initialization.

        Returns:
            float: The calculated growth rate (e.g., 0.2 for 20% growth).
                   Returns `float('nan')` if the prior period value is zero
                   or non-numeric.

        Raises:
            CalculationError: If the input node fails to provide numeric values
                for the required periods.
        """
        try:
            prior_value = self.input_node.calculate(self.prior_period)
            current_value = self.input_node.calculate(self.current_period)

            # Validate input types
            if not isinstance(prior_value, (int, float)):
                raise TypeError(f"Prior period ('{self.prior_period}') value is non-numeric.")
            if not isinstance(current_value, (int, float)):
                raise TypeError(f"Current period ('{self.current_period}') value is non-numeric.")

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
        """Return the names of nodes this node depends on."""
        return [self.input_node.name]

    def has_calculation(self) -> bool:
        """Indicate that this node performs a calculation."""
        return True


class MultiPeriodStatNode(Node):
    """Calculate a statistical measure across multiple periods.

    Applies a specified statistical function (e.g., mean, standard deviation)
    to the values of an input node over a list of periods.

    Attributes:
        name (str): The node's identifier.
        input_node (Node): The node providing the values for analysis.
        periods (List[str]): The list of period identifiers to include.
        stat_func (StatFunc): The statistical function to apply (e.g.,
            `statistics.mean`, `statistics.stdev`). Must accept a sequence
            of numbers and return a single number.

    Examples:
        >>> # Assume sales_node holds {"Q1": 10, "Q2": 12, "Q3": 11, "Q4": 13}
        >>> sales_node = FinancialStatementItemNode("sales", {"Q1": 10, "Q2": 12, "Q3": 11, "Q4": 13})
        >>> mean_sales = MultiPeriodStatNode(
        ...     "avg_quarterly_sales",
        ...     input_node=sales_node,
        ...     periods=["Q1", "Q2", "Q3", "Q4"],
        ...     stat_func=statistics.mean
        ... )
        >>> print(mean_sales.calculate()) # Period arg is ignored
        11.5
        >>> stddev_sales = MultiPeriodStatNode(
        ...     "sales_volatility",
        ...     input_node=sales_node,
        ...     periods=["Q1", "Q2", "Q3", "Q4"],
        ...     stat_func=statistics.stdev # Default
        ... )
        >>> print(round(stddev_sales.calculate(), 2))
        1.29
    """

    def __init__(
        self,
        name: str,
        input_node: Node,
        periods: list[str],
        stat_func: StatFunc = statistics.stdev,  # Default to standard deviation
    ):
        """Initialize the multi-period statistics node.

        Args:
            name (str): The identifier for this statistical node.
            input_node (Node): The node providing the source values.
            periods (List[str]): A list of period identifiers to analyze.
            stat_func (StatFunc): The statistical function to apply. Defaults to
                `statistics.stdev`. It must accept a sequence of numerics and
                return a numeric value.

        Raises:
            ValueError: If `periods` is not a list or is empty.
            TypeError: If `input_node` is not a Node, `periods` contains non-strings,
                or `stat_func` is not callable.
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

    def calculate(self, period: Optional[str] = None) -> float:
        """Calculate the statistical measure across the specified periods.

        Retrieves values from the input node for each period in the configured list,
        then applies the `stat_func`. The `period` argument is ignored.

        Args:
            period (Optional[str]): Ignored. Calculation uses the periods defined
                during initialization.

        Returns:
            float: The result of the statistical function. Returns `float('nan')`
                   if the statistical function requires more data points than
                   available (e.g., standard deviation with < 2 values) or if
                   no valid numeric data is found.

        Raises:
            CalculationError: If retrieving input node values fails or if the
                statistical function itself raises an unexpected error.
        """
        values: list[Numeric] = []
        retrieval_errors = []
        try:
            for p in self.periods:
                try:
                    value = self.input_node.calculate(p)
                    if isinstance(value, (int, float)) and math.isfinite(value):
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
        """Return the names of nodes this node depends on."""
        return [self.input_node.name]

    def has_calculation(self) -> bool:
        """Indicate that this node performs a calculation."""
        return True


class TwoPeriodAverageNode(Node):
    """Compute the simple average of an input node's value over two periods.

    Calculates (Value at Period 1 + Value at Period 2) / 2.

    Attributes:
        name (str): Identifier for this node.
        input_node (Node): Node providing the values to be averaged.
        period1 (str): Identifier for the first period.
        period2 (str): Identifier for the second period.

    Examples:
        >>> # Assume price_node holds {"Jan": 10.0, "Feb": 11.0}
        >>> price_node = FinancialStatementItemNode("price", {"Jan": 10.0, "Feb": 11.0})
        >>> avg_price = TwoPeriodAverageNode(
        ...     "jan_feb_avg_price",
        ...     input_node=price_node,
        ...     period1="Jan",
        ...     period2="Feb"
        ... )
        >>> print(avg_price.calculate()) # Period arg is ignored
        10.5
    """

    def __init__(self, name: str, input_node: Node, period1: str, period2: str):
        """Initialize the two-period average node.

        Args:
            name (str): The identifier for this node.
            input_node (Node): The node providing values.
            period1 (str): The identifier for the first period.
            period2 (str): The identifier for the second period.

        Raises:
            TypeError: If `input_node` is not a Node, or periods are not strings.
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
        """Calculate the average of the input node for the two fixed periods.

        Ignores the `period` argument, using `period1` and `period2` defined
        during initialization.

        Args:
            period (Optional[str]): Ignored.

        Returns:
            float: The average of the input node's values for `period1` and `period2`.
                   Returns `float('nan')` if either input value is non-numeric.

        Raises:
            CalculationError: If retrieving values from the input node fails.
        """
        try:
            val1 = self.input_node.calculate(self.period1)
            val2 = self.input_node.calculate(self.period2)

            # Ensure values are numeric and finite
            if not isinstance(val1, (int, float)) or not math.isfinite(val1):
                logger.warning(
                    f"TwoPeriodAverageNode '{self.name}': Value for period '{self.period1}' is non-numeric/non-finite ({val1}). Returning NaN."
                )
                return float("nan")
            if not isinstance(val2, (int, float)) or not math.isfinite(val2):
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
        """Return the names of nodes this node depends on."""
        return [self.input_node.name]

    def has_calculation(self) -> bool:
        """Indicate that this node performs a calculation."""
        return True


__all__ = [
    "MultiPeriodStatNode",
    "TwoPeriodAverageNode",
    "YoYGrowthNode",
]
