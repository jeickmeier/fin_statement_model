from typing import List, Callable
from .nodes import Node

class ForecastNode(Node):
    """
    Base class for forecast nodes that project future values based on historical data.

    A forecast node takes an input node (typically a financial statement item) and projects its
    future values using various growth methods. The node caches calculated values to avoid
    redundant computations.

    Attributes:
        name (str): Identifier for the forecast node
        input_node (Node): Source node containing historical values to forecast from
        base_period (str): Last historical period to use as basis for forecasting
        forecast_periods (List[str]): List of future periods to generate forecasts for
        _cache (dict): Internal cache of calculated values

    Methods:
        calculate(period): Get value for a specific period (historical or forecast)
        _calculate_value(period): Core calculation logic for a period
        _get_previous_period(period): Helper to get chronologically previous period
        _get_growth_factor_for_period(): Abstract method for growth rate calculation

    Example:
        # Create 5% fixed growth forecast for revenue
        base = "FY2022"
        forecasts = ["FY2023", "FY2024", "FY2025"]
        node = FixedGrowthForecastNode("revenue_forecast", revenue_node, base, forecasts, 0.05)
        
        # Get forecasted value
        fy2024_revenue = node.calculate("FY2024")
    """
    def __init__(self, input_node: Node, base_period: str, forecast_periods: List[str]):
        self.name = input_node.name
        self.input_node = input_node
        self.base_period = base_period
        self.forecast_periods = forecast_periods
        self._cache = {}

    def calculate(self, period: str) -> float:
        """
        Calculate the value for a specific period, using cached results if available.

        This method returns historical values for periods up to the base period, and
        calculates forecasted values for future periods. Results are cached to avoid
        redundant calculations.

        Args:
            period (str): The period to calculate the value for (e.g. "FY2023")

        Returns:
            float: The calculated value for the specified period

        Raises:
            ValueError: If the requested period is not in base_period or forecast_periods

        Example:
            # Get historical value
            base_value = node.calculate("FY2022")  # Returns actual historical value

            # Get forecasted value 
            forecast_value = node.calculate("FY2024")  # Returns projected value
        """
        if period not in self._cache:
            self._cache[period] = self._calculate_value(period)
        return self._cache[period]

    def clear_cache(self):
        """
        Clear the calculation cache.

        This method clears any cached calculation results, forcing future calls to
        calculate() to recompute values rather than using cached results.

        Example:
            # Clear cached calculations
            node.clear_cache()  # Future calculate() calls will recompute values
        """
        self._cache.clear()

    def _calculate_value(self, period: str) -> float:
        if period <= self.base_period:
            return self.input_node.calculate(period)
        if period not in self.forecast_periods:
            raise ValueError(f"Period '{period}' not in forecast periods for {self.name}")
        prev_period = self._get_previous_period(period)
        prev_value = self.calculate(prev_period)
        growth_factor = self._get_growth_factor_for_period(period, prev_period, prev_value)
        return prev_value * (1 + growth_factor)

    def _get_previous_period(self, current_period: str) -> str:
        all_periods = sorted([self.base_period] + self.forecast_periods)
        idx = all_periods.index(current_period)
        return all_periods[idx - 1]

    def _get_growth_factor_for_period(self, period: str, prev_period: str, prev_value: float) -> float:
        raise NotImplementedError("Implement in subclass.")

class FixedGrowthForecastNode(ForecastNode):
    """
    A forecast node that applies a fixed growth rate to project future values.

    This node takes a constant growth rate and applies it to each forecast period,
    compounding from the base period value. It's useful for simple forecasting scenarios
    where steady growth is expected.

    Args:
        name (str): Name identifier for the node
        input_node (Node): The node containing historical/base values
        base_period (str): The last historical period (e.g. "FY2022") 
        forecast_periods (List[str]): List of future periods to forecast
        growth_rate (float): The fixed growth rate to apply (e.g. 0.05 for 5% growth)

    Example:
        # Create node forecasting 5% annual revenue growth
        forecast = FixedGrowthForecastNode(
            "revenue_forecast",
            revenue_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            0.05
        )

        # Get forecasted value
        fy2024_revenue = forecast.calculate("FY2024")
        # Returns: base_value * (1.05)^2
    """
    def __init__(self, input_node: Node, base_period: str, forecast_periods: List[str], growth_rate: float):
        super().__init__(input_node, base_period, forecast_periods)
        self.growth_rate = growth_rate

    def _get_growth_factor_for_period(self, period: str, prev_period: str, prev_value: float) -> float:
        return self.growth_rate

class CurveGrowthForecastNode(ForecastNode):
    """
    A forecast node that applies different growth rates for each forecast period.

    This node takes a list of growth rates corresponding to each forecast period,
    allowing for varying growth assumptions over time. This is useful when you expect
    growth patterns to change, such as high initial growth followed by moderation.

    Args:
        name (str): Name identifier for the node
        input_node (Node): The node containing historical/base values
        base_period (str): The last historical period (e.g. "FY2022")
        forecast_periods (List[str]): List of future periods to forecast
        growth_rates (List[float]): List of growth rates for each period (e.g. [0.08, 0.06, 0.04])
                                   Must match length of forecast_periods.

    Raises:
        ValueError: If length of growth_rates doesn't match forecast_periods

    Example:
        # Create node with declining growth rates
        forecast = CurveGrowthForecastNode(
            "revenue_forecast", 
            revenue_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            [0.08, 0.06, 0.04]  # 8% then 6% then 4% growth
        )

        # Get forecasted value
        fy2024_revenue = forecast.calculate("FY2024")
        # Returns: base_value * (1.08) * (1.06)
    """
    def __init__(self, input_node: Node, base_period: str, forecast_periods: List[str], growth_rates: List[float]):
        super().__init__( input_node, base_period, forecast_periods)
        if len(growth_rates) != len(forecast_periods):
            raise ValueError("Number of growth rates must match forecast periods.")
        self.growth_rates = growth_rates

    def _get_growth_factor_for_period(self, period: str, prev_period: str, prev_value: float) -> float:
        idx = self.forecast_periods.index(period)
        return self.growth_rates[idx]

class StatisticalGrowForecastNode(ForecastNode):
    """
    A forecast node that generates growth rates from a statistical distribution.

    This node uses a provided statistical distribution function to randomly generate
    growth rates for each forecast period. This is useful for modeling uncertainty
    and running Monte Carlo simulations of different growth scenarios.

    Args:
        name (str): Name identifier for the node
        input_node (Node): The node containing historical/base values
        base_period (str): The last historical period (e.g. "FY2022")
        forecast_periods (List[str]): List of future periods to forecast
        distribution_callable (Callable[[], float]): Function that returns random growth rates
                                                   from a statistical distribution

    Example:
        # Create node with normally distributed growth rates
        from numpy.random import normal
        forecast = StatisticalGrowForecastNode(
            "revenue_forecast",
            revenue_node, 
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            lambda: normal(0.05, 0.02)  # Mean 5% growth, 2% std dev
        )

        # Get forecasted value (will vary due to randomness)
        fy2024_revenue = forecast.calculate("FY2024")
        # Returns: base_value * (1 + r1) * (1 + r2) where r1,r2 are random
    """
    def __init__(self, input_node: Node, base_period: str, forecast_periods: List[str], distribution_callable: Callable[[], float]):
        super().__init__(input_node, base_period, forecast_periods)
        self.distribution_callable = distribution_callable

    def _get_growth_factor_for_period(self, period: str, prev_period: str, prev_value: float) -> float:
        return self.distribution_callable()

class CustomGrowForecastNode(ForecastNode):
    """
    A forecast node that uses a custom function to determine growth rates.

    This node allows complete flexibility in how growth rates are calculated by accepting
    a custom function that can incorporate any logic or external data to determine the
    growth rate for each period.

    Args:
        name (str): Name identifier for the node
        input_node (Node): The node containing historical/base values
        base_period (str): The last historical period (e.g. "FY2022")
        forecast_periods (List[str]): List of future periods to forecast
        growth_function (Callable[[str, str, float], float]): Function that returns growth rate
            given current period, previous period, and previous value

    The growth_function should accept three parameters:
        - current_period (str): The period being forecasted
        - prev_period (str): The previous period
        - prev_value (float): The value from the previous period
    And return a float representing the growth rate for that period.

    Example:
        def custom_growth(period, prev_period, prev_value):
            # Growth rate increases by 1% each year, starting at 5%
            year_diff = int(period[-4:]) - int(prev_period[-4:])
            return 0.05 + (0.01 * year_diff)

        forecast = CustomGrowForecastNode(
            "revenue_forecast",
            revenue_node,
            "FY2022",
            ["FY2023", "FY2024", "FY2025"],
            custom_growth
        )

        # Get forecasted value using custom growth logic
        fy2024_revenue = forecast.calculate("FY2024")
        # Returns: base_value * (1 + 0.05) * (1 + 0.06)
    """
    def __init__(self, input_node: Node, base_period: str, forecast_periods: List[str], growth_function: Callable[[str, str, float], float]):
        super().__init__(input_node, base_period, forecast_periods)
        self.growth_function = growth_function

    def _get_growth_factor_for_period(self, period: str, prev_period: str, prev_value: float) -> float:
        return self.growth_function(period, prev_period, prev_value)
