"""Provide forecast nodes to project future values from historical data.

This module defines the base `ForecastNode` class and its subclasses,
implementing various forecasting strategies (fixed, curve, statistical,
custom, average, and historical growth).
"""

import logging
from collections.abc import Callable
from typing import Optional, Any
from fin_statement_model.config import cfg

# Use absolute imports
from fin_statement_model.core.nodes.base import Node

logger = logging.getLogger(__name__)


class ForecastNode(Node):
    """Define base class for forecast nodes to project future values from historical data.

    A forecast node takes an input node (typically a financial statement item) and projects its
    future values using various growth methods. The node caches calculated values to avoid
    redundant computations.

    Attributes:
        name (str): Identifier for the forecast node (derived from input_node.name)
        input_node (Node): Source node containing historical values to forecast from
        base_period (str): Last historical period to use as basis for forecasting
        forecast_periods (List[str]): List of future periods to generate forecasts for
        _cache (dict): Internal cache of calculated values
        values (dict): Dictionary mapping periods to values (including historical)

    Methods:
        calculate(period): Get value for a specific period (historical or forecast)
        _calculate_value(period): Core calculation logic for a period
        _get_previous_period(period): Helper to get chronologically previous period
        _get_growth_factor_for_period(): Abstract method for growth rate calculation

    Examples:
        # Create 5% fixed growth forecast for revenue
        base = "FY2022"
        forecasts = ["FY2023", "FY2024", "FY2025"]
        node = FixedGrowthForecastNode(revenue_node, base, forecasts, 0.05)

        # Get forecasted value
        fy2024_revenue = node.calculate("FY2024")
    """

    def __init__(self, input_node: Node, base_period: str, forecast_periods: list[str]):
        """Initialize ForecastNode with input node and forecast periods.

        Args:
            input_node: Source node containing historical values.
            base_period: The last historical period serving as the forecast base.
            forecast_periods: List of future periods for which forecasts will be generated.
        """
        # Initialize with a default name based on input node, but allow it to be overridden
        super().__init__(input_node.name)
        self.input_node = input_node
        self.base_period = base_period
        self.forecast_periods = forecast_periods
        self._cache = {}

        # Copy historical values from input node
        if hasattr(input_node, "values"):
            self.values = input_node.values.copy()
        else:
            self.values = {}

    def calculate(self, period: str) -> float:
        """Calculate the value for a specific period, using cached results if available.

        This method returns historical values for periods up to the base period, and
        calculates forecasted values for future periods. Results are cached to avoid
        redundant calculations.

        Args:
            period (str): The period to calculate the value for (e.g. "FY2023")

        Returns:
            float: The calculated value for the specified period

        Raises:
            ValueError: If the requested period is not in base_period or forecast_periods

        Examples:
            # Get historical value
            base_value = node.calculate("FY2022")  # Returns actual historical value

            # Get forecasted value
            forecast_value = node.calculate("FY2024")  # Returns projected value
        """
        if period not in self._cache:
            self._cache[period] = self._calculate_value(period)
        return self._cache[period]

    def clear_cache(self):
        """Clear the calculation cache.

        This method clears any cached calculation results, forcing future calls to
        calculate() to recompute values rather than using cached results.

        Examples:
            # Clear cached calculations
            node.clear_cache()  # Future calculate() calls will recompute values
        """
        self._cache.clear()

    def has_calculation(self) -> bool:
        """Indicate that this node performs a calculation."""
        return True

    def get_dependencies(self) -> list[str]:
        """Return the names of nodes this forecast node depends on.

        Returns:
            List containing the base node name.
        """
        return [self.input_node.name]

    def _calculate_value(self, period: str) -> float:
        """Calculate the value for a specific period.

        For historical periods (up to base_period), returns the actual value.
        For forecast periods, calculates the value using the growth rate.

        Args:
            period: The period to calculate the value for

        Returns:
            float: The calculated value for the period

        Raises:
            ValueError: If the period is not in base_period or forecast_periods
        """
        # For historical periods, return the actual value
        if period <= self.base_period:
            return self.values.get(period, 0.0)  # 0.0 is appropriate here - not a growth rate

        # For forecast periods, calculate using growth rate
        if period not in self.forecast_periods:
            raise ValueError(f"Period '{period}' not in forecast periods for {self.name}")

        # Get the previous period's value
        prev_period = self._get_previous_period(period)
        prev_value = self.calculate(prev_period)

        # Get the growth rate for this period
        growth_factor = self._get_growth_factor_for_period(period, prev_period, prev_value)

        # Calculate the new value
        return prev_value * (1 + growth_factor)

    def _get_previous_period(self, current_period: str) -> str:
        all_periods = sorted([self.base_period, *self.forecast_periods])
        idx = all_periods.index(current_period)
        return all_periods[idx - 1]

    def _get_growth_factor_for_period(
        self, period: str, prev_period: str, prev_value: float
    ) -> float:
        raise NotImplementedError("Implement in subclass.")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a dictionary representation.

        Returns:
            Dictionary containing the node's type, name, and forecast configuration.

        Note:
            This base implementation should be overridden by subclasses to include
            specific forecast parameters.
        """
        return {
            "type": "forecast",
            "name": self.name,
            "base_node_name": self.input_node.name,
            "base_period": self.base_period,
            "forecast_periods": self.forecast_periods.copy(),
            "forecast_type": "base",  # Override in subclasses
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ForecastNode":
        """Create a ForecastNode from a dictionary representation.

        Args:
            data: Dictionary containing the node's serialized data.

        Returns:
            A new ForecastNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.
            NotImplementedError: This method requires context (existing nodes) to resolve
                the base node dependency. Use from_dict_with_context instead.
        """
        raise NotImplementedError(
            "ForecastNode.from_dict() requires context to resolve base node dependency. "
            "Use NodeFactory.create_from_dict() or from_dict_with_context() instead."
        )

    @staticmethod
    def from_dict_with_context(data: dict[str, Any], context: dict[str, Node]) -> "ForecastNode":
        """Create a ForecastNode from a dictionary with node context.

        Args:
            data: Dictionary containing the node's serialized data.
            context: Dictionary of existing nodes to resolve dependencies.

        Returns:
            A new ForecastNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.
            NotImplementedError: This base method should be overridden by subclasses.
        """
        raise NotImplementedError("Subclasses must implement from_dict_with_context")


class FixedGrowthForecastNode(ForecastNode):
    """A forecast node that applies a constant growth rate to all forecast periods.

    This node projects future values by applying the same growth rate to each period.
    It's the simplest forecasting method and is useful when you expect consistent
    growth patterns.

    Args:
        input_node (Node): The node containing historical/base values
        base_period (str): The last historical period (e.g. "FY2022")
        forecast_periods (List[str]): List of future periods to forecast
        growth_rate (float): The constant growth rate to apply (e.g. 0.05 for 5% growth)

    Examples:
        # Create 5% growth forecast for revenue
        forecast = FixedGrowthForecastNode(
            revenue_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            0.05
        )

        # Get forecasted value
        fy2024_revenue = forecast.calculate("FY2024")
        # Returns: base_value * (1.05)^2
    """

    def __init__(
        self,
        input_node: Node,
        base_period: str,
        forecast_periods: list[str],
        growth_rate: Optional[float] = None,
    ):
        """Initialize FixedGrowthForecastNode with a constant growth rate.

        Args:
            input_node: Node containing historical values to base the forecast on.
            base_period: The last historical period.
            forecast_periods: List of future periods to forecast.
            growth_rate: Fixed growth rate (e.g., 0.05 for 5% growth).
                        If None, uses config.forecasting.default_growth_rate.
        """
        super().__init__(input_node, base_period, forecast_periods)

        # Use config default if not provided
        if growth_rate is None:
            growth_rate = cfg("forecasting.default_growth_rate")

        self.growth_rate = float(growth_rate)  # Ensure it's a float
        logger.debug(f"Created FixedGrowthForecastNode with growth rate: {self.growth_rate}")

    def _get_growth_factor_for_period(
        self, period: str, prev_period: str, prev_value: float
    ) -> float:
        logger.debug(
            f"FixedGrowthForecastNode: Using growth rate {self.growth_rate} for period {period}"
        )
        return self.growth_rate

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a dictionary representation.

        Returns:
            Dictionary containing the node's forecast configuration.
        """
        base_dict = super().to_dict()
        base_dict.update(
            {
                "forecast_type": "simple",
                "growth_params": self.growth_rate,
            }
        )
        return base_dict

    @staticmethod
    def from_dict_with_context(
        data: dict[str, Any], context: dict[str, Node]
    ) -> "FixedGrowthForecastNode":
        """Create a FixedGrowthForecastNode from a dictionary with node context.

        Args:
            data: Dictionary containing the node's serialized data.
            context: Dictionary of existing nodes to resolve dependencies.

        Returns:
            A new FixedGrowthForecastNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.
        """
        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in FixedGrowthForecastNode data")

        base_node_name = data.get("base_node_name")
        if not base_node_name:
            raise ValueError("Missing 'base_node_name' field in FixedGrowthForecastNode data")

        if base_node_name not in context:
            raise ValueError(f"Base node '{base_node_name}' not found in context")

        base_node = context[base_node_name]
        base_period = data.get("base_period")
        forecast_periods = data.get("forecast_periods", [])
        growth_params = data.get("growth_params")

        if not base_period:
            raise ValueError("Missing 'base_period' field in FixedGrowthForecastNode data")

        node = FixedGrowthForecastNode(
            input_node=base_node,
            base_period=base_period,
            forecast_periods=forecast_periods,
            growth_rate=growth_params,
        )

        # Set the correct name from the serialized data
        node.name = name
        return node


class CurveGrowthForecastNode(ForecastNode):
    """A forecast node that applies different growth rates to different forecast periods.

    This node allows for more sophisticated forecasting by specifying different growth
    rates for each forecast period. This is useful when you expect growth to change
    over time (e.g., declining growth rates as a company matures).

    Args:
        input_node (Node): The node containing historical/base values
        base_period (str): The last historical period (e.g. "FY2022")
        forecast_periods (List[str]): List of future periods to forecast
        growth_rates (List[float]): List of growth rates, one for each forecast period

    Examples:
        # Create declining growth forecast for revenue
        forecast = CurveGrowthForecastNode(
            revenue_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            [0.10, 0.08, 0.05]  # 10%, 8%, 5% growth
        )

        # Get forecasted value
        fy2025_revenue = forecast.calculate("FY2025")
        # Returns: base_value * 1.10 * 1.08 * 1.05
    """

    def __init__(
        self,
        input_node: Node,
        base_period: str,
        forecast_periods: list[str],
        growth_rates: list[float],
    ):
        """Initialize CurveGrowthForecastNode with variable growth rates per period.

        Args:
            input_node: Node containing historical data.
            base_period: The last historical period.
            forecast_periods: List of future periods to forecast.
            growth_rates: List of growth rates matching each forecast period.
        """
        super().__init__(input_node, base_period, forecast_periods)
        if len(growth_rates) != len(forecast_periods):
            raise ValueError("Number of growth rates must match forecast periods.")
        self.growth_rates = [float(rate) for rate in growth_rates]  # Ensure all are floats
        logger.debug(f"Created CurveGrowthForecastNode with growth rates: {self.growth_rates}")
        logger.debug(f"  Base period: {base_period}")
        logger.debug(f"  Forecast periods: {forecast_periods}")
        logger.debug(f"  Base value: {input_node.calculate(base_period)}")

    def _get_growth_factor_for_period(
        self, period: str, prev_period: str, prev_value: float
    ) -> float:
        """Get the growth factor for a specific period."""
        idx = self.forecast_periods.index(period)
        growth_rate = self.growth_rates[idx]
        logger.debug(
            f"CurveGrowthForecastNode: Using growth rate {growth_rate} for period {period}"
        )
        logger.debug(f"  Previous period: {prev_period}")
        logger.debug(f"  Previous value: {prev_value}")
        return growth_rate

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a dictionary representation.

        Returns:
            Dictionary containing the node's forecast configuration.
        """
        base_dict = super().to_dict()
        base_dict.update(
            {
                "forecast_type": "curve",
                "growth_params": self.growth_rates.copy(),
            }
        )
        return base_dict

    @staticmethod
    def from_dict_with_context(
        data: dict[str, Any], context: dict[str, Node]
    ) -> "CurveGrowthForecastNode":
        """Create a CurveGrowthForecastNode from a dictionary with node context.

        Args:
            data: Dictionary containing the node's serialized data.
            context: Dictionary of existing nodes to resolve dependencies.

        Returns:
            A new CurveGrowthForecastNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.
        """
        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in CurveGrowthForecastNode data")

        base_node_name = data.get("base_node_name")
        if not base_node_name:
            raise ValueError("Missing 'base_node_name' field in CurveGrowthForecastNode data")

        if base_node_name not in context:
            raise ValueError(f"Base node '{base_node_name}' not found in context")

        base_node = context[base_node_name]
        base_period = data.get("base_period")
        forecast_periods = data.get("forecast_periods", [])
        growth_params = data.get("growth_params", [])

        if not base_period:
            raise ValueError("Missing 'base_period' field in CurveGrowthForecastNode data")

        if not isinstance(growth_params, list):
            raise TypeError("'growth_params' must be a list for CurveGrowthForecastNode")

        node = CurveGrowthForecastNode(
            input_node=base_node,
            base_period=base_period,
            forecast_periods=forecast_periods,
            growth_rates=growth_params,
        )

        # Set the correct name from the serialized data
        node.name = name
        return node


class StatisticalGrowthForecastNode(ForecastNode):
    """A forecast node that generates growth rates from a statistical distribution.

    This node uses a provided statistical distribution function to randomly generate
    growth rates for each forecast period. This is useful for modeling uncertainty
    and running Monte Carlo simulations of different growth scenarios.

    Args:
        input_node (Node): The node containing historical/base values
        base_period (str): The last historical period (e.g. "FY2022")
        forecast_periods (List[str]): List of future periods to forecast
        distribution_callable (Callable[[], float]): Function that returns random growth rates
                                                   from a statistical distribution

    Examples:
        # Create node with normally distributed growth rates
        from numpy.random import normal
        forecast = StatisticalGrowthForecastNode(
            revenue_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            lambda: normal(0.05, 0.02)  # Mean 5% growth, 2% std dev
        )

        # Get forecasted value (will vary due to randomness)
        fy2024_revenue = forecast.calculate("FY2024")
        # Returns: base_value * (1 + r1) * (1 + r2) where r1,r2 are random
    """

    def __init__(
        self,
        input_node: Node,
        base_period: str,
        forecast_periods: list[str],
        distribution_callable: Callable[[], float],
    ):
        """Initialize StatisticalGrowthForecastNode with a distribution function.

        Args:
            input_node: Node containing historical data.
            base_period: The last historical period.
            forecast_periods: List of future periods to forecast.
            distribution_callable: Function that returns a random growth rate.
        """
        super().__init__(input_node, base_period, forecast_periods)
        self.distribution_callable = distribution_callable

    def _get_growth_factor_for_period(
        self, period: str, prev_period: str, prev_value: float
    ) -> float:
        return self.distribution_callable()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a dictionary representation.

        Returns:
            Dictionary containing the node's forecast configuration.

        Note:
            The distribution_callable cannot be serialized, so a warning is included.
        """
        base_dict = super().to_dict()
        base_dict.update(
            {
                "forecast_type": "statistical",
                "serialization_warning": (
                    "StatisticalGrowthForecastNode uses a distribution callable which cannot be serialized. "
                    "Manual reconstruction required."
                ),
            }
        )
        return base_dict

    @staticmethod
    def from_dict_with_context(
        data: dict[str, Any], context: dict[str, Node]
    ) -> "StatisticalGrowthForecastNode":
        """Create a StatisticalGrowthForecastNode from a dictionary with node context.

        Args:
            data: Dictionary containing the node's serialized data.
            context: Dictionary of existing nodes to resolve dependencies.

        Returns:
            A new StatisticalGrowthForecastNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.
            NotImplementedError: StatisticalGrowthForecastNode cannot be fully deserialized
                because the distribution_callable cannot be serialized.
        """
        raise NotImplementedError(
            "StatisticalGrowthForecastNode cannot be fully deserialized because the "
            "distribution_callable cannot be serialized. Manual reconstruction required."
        )


class CustomGrowthForecastNode(ForecastNode):
    """A forecast node that uses a custom function to calculate growth rates.

    This node allows for completely custom growth logic by providing a function that
    calculates the growth rate based on the current period, previous period, and
    previous value. This is the most flexible forecasting option.

    Args:
        input_node (Node): The node containing historical/base values
        base_period (str): The last historical period (e.g. "FY2022")
        forecast_periods (List[str]): List of future periods to forecast
        growth_function (Callable): Function that calculates growth rate given
                                  (period, prev_period, prev_value) -> growth_rate

    Examples:
        # Create custom growth logic
        def custom_growth(period, prev_period, prev_value):
            # Declining growth based on company size
            if prev_value < 1000:
                return 0.15  # 15% for small companies
            elif prev_value < 5000:
                return 0.10  # 10% for medium companies
            else:
                return 0.05  # 5% for large companies

        forecast = CustomGrowthForecastNode(
            revenue_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            custom_growth
        )
    """

    def __init__(
        self,
        input_node: Node,
        base_period: str,
        forecast_periods: list[str],
        growth_function: Callable[[str, str, float], float],
    ):
        """Initialize CustomGrowthForecastNode with a custom growth function.

        Args:
            input_node: Node containing historical data.
            base_period: The last historical period.
            forecast_periods: List of future periods to forecast.
            growth_function: Callable(period, prev_period, prev_value) -> growth rate.
        """
        super().__init__(input_node, base_period, forecast_periods)
        self.growth_function = growth_function

    def _get_growth_factor_for_period(
        self, period: str, prev_period: str, prev_value: float
    ) -> float:
        return self.growth_function(period, prev_period, prev_value)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a dictionary representation.

        Returns:
            Dictionary containing the node's forecast configuration.

        Note:
            The growth_function cannot be serialized, so a warning is included.
        """
        base_dict = super().to_dict()
        base_dict.update(
            {
                "forecast_type": "custom",
                "serialization_warning": (
                    "CustomGrowthForecastNode uses a growth function which cannot be serialized. "
                    "Manual reconstruction required."
                ),
            }
        )
        return base_dict

    @staticmethod
    def from_dict_with_context(
        data: dict[str, Any], context: dict[str, Node]
    ) -> "CustomGrowthForecastNode":
        """Create a CustomGrowthForecastNode from a dictionary with node context.

        Args:
            data: Dictionary containing the node's serialized data.
            context: Dictionary of existing nodes to resolve dependencies.

        Returns:
            A new CustomGrowthForecastNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.
            NotImplementedError: CustomGrowthForecastNode cannot be fully deserialized
                because the growth_function cannot be serialized.
        """
        raise NotImplementedError(
            "CustomGrowthForecastNode cannot be fully deserialized because the "
            "growth_function cannot be serialized. Manual reconstruction required."
        )


class AverageValueForecastNode(ForecastNode):
    """A forecast node that uses the average of historical values for all forecast periods.

    This node calculates the average of historical values and returns that constant value
    for all forecast periods. It's useful when you want to project future values based
    on the historical average, without any growth.
    """

    def __init__(
        self,
        input_node: Node,
        base_period: str,
        forecast_periods: list[str],
    ):
        """Initialize AverageValueForecastNode by computing historical average.

        Args:
            input_node: Node containing historical data.
            base_period: The last historical period.
            forecast_periods: List of future periods to forecast.

        """
        super().__init__(input_node, base_period, forecast_periods)
        self.average_value = self._calculate_average_value()
        logger.debug(f"Created AverageValueForecastNode with average value: {self.average_value}")

    def _calculate_average_value(self) -> float:
        """Calculate the average historical value up to the base period.

        Returns:
            float: The average of historical values or 0.0 if none.
        """
        values = [value for period, value in self.values.items() if period <= self.base_period]
        if not values:
            logger.warning(f"No historical values found for {self.name}, using 0.0 as average")
            return 0.0
        return sum(values) / len(values)

    def _calculate_value(self, period: str) -> float:
        """Calculate the value for a specific period using the computed average value."""
        # For historical periods, return the actual value
        if period <= self.base_period:
            return self.values.get(period, 0.0)

        # For forecast periods, return the constant average value
        if period not in self.forecast_periods:
            raise ValueError(f"Period '{period}' not in forecast periods for {self.name}")

        return self.average_value

    def _get_growth_factor_for_period(
        self, period: str, prev_period: str, prev_value: float
    ) -> float:
        """Not used for average value forecasts."""
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a dictionary representation.

        Returns:
            Dictionary containing the node's forecast configuration.
        """
        base_dict = super().to_dict()
        base_dict.update(
            {
                "forecast_type": "average",
                "average_value": self.average_value,
            }
        )
        return base_dict

    @staticmethod
    def from_dict_with_context(
        data: dict[str, Any], context: dict[str, Node]
    ) -> "AverageValueForecastNode":
        """Create an AverageValueForecastNode from a dictionary with node context.

        Args:
            data: Dictionary containing the node's serialized data.
            context: Dictionary of existing nodes to resolve dependencies.

        Returns:
            A new AverageValueForecastNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.
        """
        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in AverageValueForecastNode data")

        base_node_name = data.get("base_node_name")
        if not base_node_name:
            raise ValueError("Missing 'base_node_name' field in AverageValueForecastNode data")

        if base_node_name not in context:
            raise ValueError(f"Base node '{base_node_name}' not found in context")

        base_node = context[base_node_name]
        base_period = data.get("base_period")
        forecast_periods = data.get("forecast_periods", [])

        if not base_period:
            raise ValueError("Missing 'base_period' field in AverageValueForecastNode data")

        node = AverageValueForecastNode(
            input_node=base_node,
            base_period=base_period,
            forecast_periods=forecast_periods,
        )

        # Set the correct name from the serialized data
        node.name = name
        return node


class AverageHistoricalGrowthForecastNode(ForecastNode):
    """A forecast node that uses the average historical growth rate for forecasting.

    This node calculates the average growth rate from historical values and applies
    that same growth rate consistently to all forecast periods. It's useful when you
    want to project future values based on the historical growth pattern.

    Args:
        input_node (Node): The node containing historical/base values
        base_period (str): The last historical period (e.g. "FY2022")
        forecast_periods (List[str]): List of future periods to forecast
    """

    def __init__(
        self,
        input_node: Node,
        base_period: str,
        forecast_periods: list[str],
    ):
        """Initialize AverageHistoricalGrowthForecastNode by computing average growth.

        Args:
            input_node: Node containing historical data.
            base_period: The last historical period.
            forecast_periods: List of future periods to forecast.
        """
        super().__init__(input_node, base_period, forecast_periods)
        self.avg_growth_rate = self._calculate_average_growth_rate()
        logger.debug(
            f"Created AverageHistoricalGrowthForecastNode with growth rate: {self.avg_growth_rate}"
        )

    def _calculate_average_growth_rate(self) -> float:
        """Calculate the average growth rate from historical values.

        Returns:
            float: The average growth rate or 0.0 if insufficient data.
        """
        # Get historical periods up to base_period, sorted
        historical_periods = sorted([p for p in self.values if p <= self.base_period])

        if len(historical_periods) < 2:
            logger.warning(
                f"Insufficient historical data for {self.name}, using 0.0 as growth rate"
            )
            return 0.0

        # Calculate growth rates between consecutive periods
        growth_rates = []
        for i in range(1, len(historical_periods)):
            prev_period = historical_periods[i - 1]
            curr_period = historical_periods[i]
            prev_value = self.values.get(prev_period, 0.0)
            curr_value = self.values.get(curr_period, 0.0)

            if prev_value != 0:
                growth_rate = (curr_value - prev_value) / prev_value
                growth_rates.append(growth_rate)

        if not growth_rates:
            logger.warning(f"No valid growth rates calculated for {self.name}, using 0.0")
            return 0.0

        return sum(growth_rates) / len(growth_rates)

    def _get_growth_factor_for_period(
        self, period: str, prev_period: str, prev_value: float
    ) -> float:
        return self.avg_growth_rate

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a dictionary representation.

        Returns:
            Dictionary containing the node's forecast configuration.
        """
        base_dict = super().to_dict()
        base_dict.update(
            {
                "forecast_type": "historical_growth",
                "avg_growth_rate": self.avg_growth_rate,
            }
        )
        return base_dict

    @staticmethod
    def from_dict_with_context(
        data: dict[str, Any], context: dict[str, Node]
    ) -> "AverageHistoricalGrowthForecastNode":
        """Create an AverageHistoricalGrowthForecastNode from a dictionary with node context.

        Args:
            data: Dictionary containing the node's serialized data.
            context: Dictionary of existing nodes to resolve dependencies.

        Returns:
            A new AverageHistoricalGrowthForecastNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.
        """
        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in AverageHistoricalGrowthForecastNode data")

        base_node_name = data.get("base_node_name")
        if not base_node_name:
            raise ValueError(
                "Missing 'base_node_name' field in AverageHistoricalGrowthForecastNode data"
            )

        if base_node_name not in context:
            raise ValueError(f"Base node '{base_node_name}' not found in context")

        base_node = context[base_node_name]
        base_period = data.get("base_period")
        forecast_periods = data.get("forecast_periods", [])

        if not base_period:
            raise ValueError(
                "Missing 'base_period' field in AverageHistoricalGrowthForecastNode data"
            )

        node = AverageHistoricalGrowthForecastNode(
            input_node=base_node,
            base_period=base_period,
            forecast_periods=forecast_periods,
        )

        # Set the correct name from the serialized data
        node.name = name
        return node
