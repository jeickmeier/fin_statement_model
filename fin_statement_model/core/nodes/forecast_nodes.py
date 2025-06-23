"""Provide forecast nodes to project future values from historical data.

This module defines the base `ForecastNode` class and its subclasses,
implementing various forecasting strategies (fixed, curve, statistical,
custom, average, and historical growth).

Features:
    - ForecastNode provides a base for projecting future values from historical data.
    - FixedGrowthForecastNode applies a constant growth rate to all forecast periods.
    - CurveGrowthForecastNode allows period-specific growth rates.
    - StatisticalGrowthForecastNode samples growth from a distribution.
    - CustomGrowthForecastNode uses a user-supplied function for growth.
    - AverageValueForecastNode projects the historical average forward.
    - AverageHistoricalGrowthForecastNode applies the average historical growth rate.
    - All nodes support serialization to and from dictionary representations (where possible).
    - All nodes provide dependency inspection and cache clearing.

Example:
    >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
    >>> from fin_statement_model.core.nodes.forecast_nodes import FixedGrowthForecastNode, AverageValueForecastNode
    >>> revenue = FinancialStatementItemNode("revenue", {"2022": 100, "2023": 110})
    >>> forecast = FixedGrowthForecastNode(revenue, "2023", ["2024", "2025"], 0.05)
    >>> round(forecast.calculate("2025"), 2)
    121.28
    >>> avg_forecast = AverageValueForecastNode(revenue, "2023", ["2024", "2025"])
    >>> avg_forecast.calculate("2024")
    105.0
"""

import logging
from collections.abc import Callable
from typing import Optional, Any
from abc import abstractmethod

# Use absolute imports
from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.node_factory.registries import forecast_type

logger = logging.getLogger(__name__)


class ForecastNode(Node):
    """Base class for projecting future values from historical data.

    ForecastNode uses a source node's historical data to generate projected values
    for specified future periods, caching results to avoid redundant computations.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary.
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> ForecastNode`:
            Classmethod to deserialize a node from a dictionary. Subclasses must override this method.

    Attributes:
        input_node (Node): Node providing historical data.
        base_period (str): Last historical period used as forecast base.
        forecast_periods (list[str]): Future periods to project.
        values (dict[str, float]): Historical and forecasted values.

    Example:
        >>> from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode
        >>> from fin_statement_model.core.nodes.forecast_nodes import FixedGrowthForecastNode
        >>> revenue = FinancialStatementItemNode("revenue", {"2022": 100, "2023": 110})
        >>> forecast = FixedGrowthForecastNode(revenue, "2023", ["2024", "2025"], 0.05)
        >>> d = forecast.to_dict()
        >>> forecast2 = FixedGrowthForecastNode.from_dict(d, {"revenue": revenue})
        >>> round(forecast2.calculate("2025"), 2)
        121.28
    """

    _cache: dict[str, float]

    def __init__(self, input_node: Node, base_period: str, forecast_periods: list[str]):
        """Initialize a ForecastNode.

        Args:
            input_node (Node): Source of historical data.
            base_period (str): Last historical period as forecast base.
            forecast_periods (list[str]): Future periods to generate forecasts for.
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
        """Calculate the node's value for a given period.

        Returns historical values for periods up to `base_period`; computes forecast for later periods.

        Args:
            period (str): Period identifier, historical or forecast.

        Returns:
            float: Value for the specified period.

        Raises:
            ValueError: If `period` is not a historical or forecast period.
        """
        if period not in self._cache:
            self._cache[period] = self._calculate_value(period)
        return self._cache[period]

    def clear_cache(self) -> None:
        """Clear cached forecast values.

        Use to force recomputation of all periods when input data changes.
        """
        self._cache.clear()

    def get_dependencies(self) -> list[str]:
        """Get names of nodes that this forecast depends on.

        Returns:
            list[str]: Single-element list of the input node's name.
        """
        return [self.input_node.name]

    def _calculate_value(self, period: str) -> float:
        """Compute the value for a given period without caching.

        Args:
            period (str): Period identifier to compute.

        Returns:
            float: Historical or forecasted value.

        Raises:
            ValueError: If `period` is not valid for this node.
        """
        # For historical periods, return the actual value
        if period <= self.base_period:
            # Return historical value, ensuring float type
            return float(self.values.get(period, 0.0))

        # For forecast periods, calculate using growth rate
        if period not in self.forecast_periods:
            raise ValueError(
                f"Period '{period}' not in forecast periods for {self.name}"
            )

        # Get the previous period's value
        prev_period = self._get_previous_period(period)
        prev_value = self.calculate(prev_period)

        # Get the growth rate for this period
        growth_factor = self._get_growth_factor_for_period(
            period, prev_period, prev_value
        )

        # Calculate the new value
        return prev_value * (1 + growth_factor)

    def _get_previous_period(self, current_period: str) -> str:
        all_periods = sorted([self.base_period, *self.forecast_periods])
        idx = all_periods.index(current_period)
        return all_periods[idx - 1]

    @abstractmethod
    def _get_growth_factor_for_period(
        self, period: str, prev_period: str, prev_value: float
    ) -> float:
        """Return the growth factor for *period*.

        Subclasses must implement this to provide their specific growth logic.
        """
        raise NotImplementedError(
            "Subclasses must implement _get_growth_factor_for_period."
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this node to a dictionary.

        Returns:
            dict[str, Any]: Serialized representation including base forecast parameters.

        Note:
            Subclasses should override to include specific forecast details.
        """
        return {
            "type": "forecast",
            "name": self.name,
            "base_node_name": self.input_node.name,
            "base_period": self.base_period,
            "forecast_periods": self.forecast_periods.copy(),
            "forecast_type": "base",  # Override in subclasses
        }

    @classmethod
    @abstractmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, Node] | None = None,
    ) -> "ForecastNode":
        """Recreate a ForecastNode from serialized data.

        Args:
            data: Dictionary containing the node's serialized data.
            context: Dictionary of existing nodes to resolve dependencies.

        Returns:
            A new ForecastNode instance.

        Raises:
            ValueError: If the data is invalid or missing required fields.
            NotImplementedError: This base method should be overridden by subclasses.
        """
        raise NotImplementedError("Subclasses must implement from_dict.")


@forecast_type("simple")
class FixedGrowthForecastNode(ForecastNode):
    """Forecast node that applies a single growth rate to every future period.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary.
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> FixedGrowthForecastNode`:
            Classmethod to deserialize a node from a dictionary. `context` is required to resolve the base node.

    Attributes:
        growth_rate (float): Constant growth factor expressed as a decimal (``0.05`` → 5 %).

    Example:
        >>> from fin_statement_model.core.nodes import FinancialStatementItemNode, FixedGrowthForecastNode
        >>> revenue = FinancialStatementItemNode("revenue", {"2022": 100})
        >>> forecast = FixedGrowthForecastNode(revenue, "2022", ["2023", "2024"], 0.05)
        >>> d = forecast.to_dict()
        >>> forecast2 = FixedGrowthForecastNode.from_dict(d, {"revenue": revenue})
        >>> round(forecast2.calculate("2024"), 2)
        110.25
    """

    def __init__(
        self,
        input_node: Node,
        base_period: str,
        forecast_periods: list[str],
        growth_rate: Optional[float] = None,
    ):
        """Create a FixedGrowthForecastNode.

        Args:
            input_node (Node): Source of historical data.
            base_period (str): Last historical period.
            forecast_periods (list[str]): Future periods to project.
            growth_rate (float | None): Constant growth rate (``0.05`` → 5 %).
                If ``None``, the default configured in ``cfg('forecasting.default_growth_rate')`` is used.
        """
        super().__init__(input_node, base_period, forecast_periods)

        # Use config default if not provided (import inside to avoid circular import)
        if growth_rate is None:
            from fin_statement_model.config.access import cfg

            growth_rate = cfg("forecasting.default_growth_rate")

        self.growth_rate = float(growth_rate)  # Ensure it's a float
        logger.debug(
            f"Created FixedGrowthForecastNode with growth rate: {self.growth_rate}"
        )

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

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, Node] | None = None,
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
        if context is None:
            raise ValueError(
                "'context' must be provided to deserialize FixedGrowthForecastNode"
            )

        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in FixedGrowthForecastNode data")

        base_node_name = data.get("base_node_name")
        if not base_node_name:
            raise ValueError(
                "Missing 'base_node_name' field in FixedGrowthForecastNode data"
            )

        if base_node_name not in context:
            raise ValueError(f"Base node '{base_node_name}' not found in context")

        base_node = context[base_node_name]
        base_period = data.get("base_period")
        forecast_periods = data.get("forecast_periods", [])
        growth_params = data.get("growth_params")

        if not base_period:
            raise ValueError(
                "Missing 'base_period' field in FixedGrowthForecastNode data"
            )

        node = cls(
            input_node=base_node,
            base_period=base_period,
            forecast_periods=forecast_periods,
            growth_rate=growth_params,
        )

        # Set the correct name from the serialized data
        node.name = name
        return node


@forecast_type("curve")
class CurveGrowthForecastNode(ForecastNode):
    """Forecast node with period-specific growth rates.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary.
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> CurveGrowthForecastNode`:
            Classmethod to deserialize a node from a dictionary. `context` is required to resolve the base node.

    Attributes:
        growth_rates (list[float]): Growth rate for each corresponding forecast period.

    Example:
        >>> from fin_statement_model.core.nodes import FinancialStatementItemNode, CurveGrowthForecastNode
        >>> revenue = FinancialStatementItemNode("revenue", {"2022": 100})
        >>> rates = [0.10, 0.08]
        >>> forecast = CurveGrowthForecastNode(revenue, "2022", ["2023", "2024"], rates)
        >>> d = forecast.to_dict()
        >>> forecast2 = CurveGrowthForecastNode.from_dict(d, {"revenue": revenue})
        >>> round(forecast2.calculate("2024"), 2)
        118.8
    """

    def __init__(
        self,
        input_node: Node,
        base_period: str,
        forecast_periods: list[str],
        growth_rates: list[float],
    ):
        """Create a CurveGrowthForecastNode.

        Args:
            input_node (Node): Source of historical data.
            base_period (str): Last historical period.
            forecast_periods (list[str]): Future periods to project.
            growth_rates (list[float]): Growth rate for each forecast period; length must equal *forecast_periods*.
        """
        super().__init__(input_node, base_period, forecast_periods)
        if len(growth_rates) != len(forecast_periods):
            raise ValueError("Number of growth rates must match forecast periods.")
        self.growth_rates = [
            float(rate) for rate in growth_rates
        ]  # Ensure all are floats
        logger.debug(
            f"Created CurveGrowthForecastNode with growth rates: {self.growth_rates}"
        )
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

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, Node] | None = None,
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
        if context is None:
            raise ValueError(
                "'context' must be provided to deserialize CurveGrowthForecastNode"
            )

        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in CurveGrowthForecastNode data")

        base_node_name = data.get("base_node_name")
        if not base_node_name:
            raise ValueError(
                "Missing 'base_node_name' field in CurveGrowthForecastNode data"
            )

        if base_node_name not in context:
            raise ValueError(f"Base node '{base_node_name}' not found in context")

        base_node = context[base_node_name]
        base_period = data.get("base_period")
        forecast_periods = data.get("forecast_periods", [])
        growth_params = data.get("growth_params", [])

        if not base_period:
            raise ValueError(
                "Missing 'base_period' field in CurveGrowthForecastNode data"
            )

        if not isinstance(growth_params, list):
            raise TypeError(
                "'growth_params' must be a list for CurveGrowthForecastNode"
            )

        node = cls(
            input_node=base_node,
            base_period=base_period,
            forecast_periods=forecast_periods,
            growth_rates=growth_params,
        )

        # Set the correct name from the serialized data
        node.name = name
        return node


@forecast_type("statistical")
class StatisticalGrowthForecastNode(ForecastNode):
    """Forecast node whose growth rates are drawn from a random distribution.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary (includes a warning).
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> StatisticalGrowthForecastNode`:
            Not supported; always raises NotImplementedError because the callable cannot be serialized.

    Attributes:
        distribution_callable (Callable[[], float]): Function returning a pseudo-random growth rate.

    Example:
        >>> # Not supported:
        >>> from fin_statement_model.core.nodes import FinancialStatementItemNode, StatisticalGrowthForecastNode
        >>> import random
        >>> revenue = FinancialStatementItemNode("revenue", {"2022": 100})
        >>> node = StatisticalGrowthForecastNode(revenue, "2022", ["2023"], lambda: random.gauss(0.05, 0.01))
        >>> d = node.to_dict()
        >>> StatisticalGrowthForecastNode.from_dict(d, {"revenue": revenue})  # doctest: +SKIP
        Traceback (most recent call last):
        ...
        NotImplementedError: StatisticalGrowthForecastNode cannot be fully deserialized because the distribution_callable cannot be serialized. Manual reconstruction required.
    """

    def __init__(
        self,
        input_node: Node,
        base_period: str,
        forecast_periods: list[str],
        distribution_callable: Callable[[], float],
    ):
        """Create a StatisticalGrowthForecastNode.

        Args:
            input_node (Node): Source of historical data.
            base_period (str): Last historical period.
            forecast_periods (list[str]): Future periods to project.
            distribution_callable (Callable[[], float]): Zero-argument function returning random growth rates.
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

    # Deserialization intentionally unsupported – distribution_callable is not serializable.

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, Node] | None = None,
    ) -> "StatisticalGrowthForecastNode":  # pragma: no cover
        """Deserialization is not supported for StatisticalGrowthForecastNode."""
        raise NotImplementedError(
            "StatisticalGrowthForecastNode cannot be deserialized; "
            "distribution_callable is not serializable."
        )


@forecast_type("custom")
class CustomGrowthForecastNode(ForecastNode):
    """Forecast node that computes growth via a user-supplied function.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary (includes a warning).
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> CustomGrowthForecastNode`:
            Not supported; always raises NotImplementedError because the function cannot be serialized.

    Attributes:
        growth_function (Callable[[str, str, float], float]): Function returning growth factor.

    Example:
        >>> # Not supported:
        >>> from fin_statement_model.core.nodes import FinancialStatementItemNode, CustomGrowthForecastNode
        >>> revenue = FinancialStatementItemNode("revenue", {"2022": 100})
        >>> node = CustomGrowthForecastNode(revenue, "2022", ["2023"], lambda p, pp, v: 0.05)
        >>> d = node.to_dict()
        >>> CustomGrowthForecastNode.from_dict(d, {"revenue": revenue})  # doctest: +SKIP
        Traceback (most recent call last):
        ...
        NotImplementedError: CustomGrowthForecastNode cannot be fully deserialized because the growth_function cannot be serialized. Manual reconstruction required.
    """

    def __init__(
        self,
        input_node: Node,
        base_period: str,
        forecast_periods: list[str],
        growth_function: Callable[[str, str, float], float],
    ):
        """Create a CustomGrowthForecastNode.

        Args:
            input_node (Node): Source of historical data.
            base_period (str): Last historical period.
            forecast_periods (list[str]): Future periods to project.
            growth_function (Callable[[str, str, float], float]): Function returning growth factor.
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

    # Deserialization intentionally unsupported – growth_function is not serializable.

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, Node] | None = None,
    ) -> "CustomGrowthForecastNode":  # pragma: no cover
        """Deserialization is not supported for CustomGrowthForecastNode."""
        raise NotImplementedError(
            "CustomGrowthForecastNode cannot be deserialized; "
            "growth_function is not serializable."
        )


@forecast_type("average")
class AverageValueForecastNode(ForecastNode):
    """Forecast node that projects the historical average forward.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary.
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> AverageValueForecastNode`:
            Classmethod to deserialize a node from a dictionary. `context` is required to resolve the base node.

    Example:
        >>> from fin_statement_model.core.nodes import FinancialStatementItemNode, AverageValueForecastNode
        >>> revenue = FinancialStatementItemNode("revenue", {"2022": 100, "2023": 110})
        >>> forecast = AverageValueForecastNode(revenue, "2023", ["2024", "2025"])
        >>> d = forecast.to_dict()
        >>> forecast2 = AverageValueForecastNode.from_dict(d, {"revenue": revenue})
        >>> forecast2.calculate("2024")
        105.0
    """

    def __init__(
        self,
        input_node: Node,
        base_period: str,
        forecast_periods: list[str],
    ):
        """Create an AverageValueForecastNode.

        Args:
            input_node (Node): Source of historical data.
            base_period (str): Last historical period.
            forecast_periods (list[str]): Future periods to project.
        """
        super().__init__(input_node, base_period, forecast_periods)
        self.average_value = self._calculate_average_value()
        logger.debug(
            f"Created AverageValueForecastNode with average value: {self.average_value}"
        )

    def _calculate_average_value(self) -> float:
        """Calculate the average historical value up to the base period.

        Returns:
            float: The average of historical values or 0.0 if none.
        """
        values = [
            value for period, value in self.values.items() if period <= self.base_period
        ]
        if not values:
            logger.warning(
                f"No historical values found for {self.name}, using 0.0 as average"
            )
            return 0.0
        # Compute average and ensure float type
        return float(sum(values)) / len(values)

    def _calculate_value(self, period: str) -> float:
        """Calculate the value for a specific period using the computed average value."""
        # For historical periods, return the actual value
        if period <= self.base_period:
            # Return historical value, ensuring float type
            return float(self.values.get(period, 0.0))

        # For forecast periods, return the constant average value
        if period not in self.forecast_periods:
            raise ValueError(
                f"Period '{period}' not in forecast periods for {self.name}"
            )

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

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, Node] | None = None,
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
        if context is None:
            raise ValueError(
                "'context' must be provided to deserialize AverageValueForecastNode"
            )

        name = data.get("name")
        if not name:
            raise ValueError("Missing 'name' field in AverageValueForecastNode data")

        base_node_name = data.get("base_node_name")
        if not base_node_name:
            raise ValueError(
                "Missing 'base_node_name' field in AverageValueForecastNode data"
            )

        if base_node_name not in context:
            raise ValueError(f"Base node '{base_node_name}' not found in context")

        base_node = context[base_node_name]
        base_period = data.get("base_period")
        forecast_periods = data.get("forecast_periods", [])

        if not base_period:
            raise ValueError(
                "Missing 'base_period' field in AverageValueForecastNode data"
            )

        node = cls(
            input_node=base_node,
            base_period=base_period,
            forecast_periods=forecast_periods,
        )

        # Set the correct name from the serialized data
        node.name = name
        return node


@forecast_type("average_growth")
class AverageHistoricalGrowthForecastNode(ForecastNode):
    """Forecast node that applies the average historical growth rate to all future periods.

    Serialization contract:
        - `to_dict(self) -> dict`: Serialize the node to a dictionary.
        - `from_dict(cls, data: dict, context: dict[str, Node] | None = None) -> AverageHistoricalGrowthForecastNode`:
            Classmethod to deserialize a node from a dictionary. `context` is required to resolve the base node.

    Example:
        >>> from fin_statement_model.core.nodes import FinancialStatementItemNode, AverageHistoricalGrowthForecastNode
        >>> revenue = FinancialStatementItemNode("revenue", {"2022": 100, "2023": 110})
        >>> forecast = AverageHistoricalGrowthForecastNode(revenue, "2023", ["2024", "2025"])
        >>> d = forecast.to_dict()
        >>> forecast2 = AverageHistoricalGrowthForecastNode.from_dict(d, {"revenue": revenue})
        >>> round(forecast2.calculate("2025"), 2)
        121.0
    """

    def __init__(
        self,
        input_node: Node,
        base_period: str,
        forecast_periods: list[str],
    ):
        """Create an AverageHistoricalGrowthForecastNode.

        Args:
            input_node (Node): Source of historical data.
            base_period (str): Last historical period.
            forecast_periods (list[str]): Future periods to project.
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
            logger.warning(
                f"No valid growth rates calculated for {self.name}, using 0.0"
            )
            return 0.0

        # Compute average growth rate and ensure float type
        return float(sum(growth_rates)) / len(growth_rates)

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

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        context: dict[str, Node] | None = None,
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
        if context is None:
            raise ValueError(
                "'context' must be provided to deserialize AverageHistoricalGrowthForecastNode"
            )

        name = data.get("name")
        if not name:
            raise ValueError(
                "Missing 'name' field in AverageHistoricalGrowthForecastNode data"
            )

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

        node = cls(
            input_node=base_node,
            base_period=base_period,
            forecast_periods=forecast_periods,
        )

        # Set the correct name from the serialized data
        node.name = name
        return node
