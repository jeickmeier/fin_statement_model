import statistics
from typing import List
from .nodes import Node

class YoYGrowthNode(Node):
    """
    A node that calculates year-over-year growth between two periods.

    This node takes an input node and calculates the percentage growth between a prior period
    and current period. The growth is calculated as: (current_value - prior_value) / prior_value.

    If the prior period value is zero, returns NaN to avoid division by zero.

    Args:
        name (str): The name/identifier for this growth calculation node
        input_node (Node): The node whose values will be used to calculate growth
        prior_period (str): The earlier time period (e.g. "2021")
        current_period (str): The later time period (e.g. "2022")

    Attributes:
        name (str): The node's name/identifier
        input_node (Node): Reference to the input node
        prior_period (str): The earlier period for growth calculation
        current_period (str): The later period for growth calculation

    Example:
        # Create growth node to calculate revenue growth
        revenue = FinancialStatementItemNode("revenue", {
            "2021": 1000.0,
            "2022": 1200.0
        })
        revenue_growth = YoYGrowthNode("revenue_growth", revenue, "2021", "2022")
        
        # Calculate growth
        growth = revenue_growth.calculate()  # Returns 0.2 (20% growth)

    Returns:
        float: The calculated growth rate as a decimal (e.g. 0.2 for 20% growth)
        float('nan'): If prior period value is zero
    """
    def __init__(self, name: str, input_node: Node, prior_period: str, current_period: str):
        self.name = name
        self.input_node = input_node
        self.prior_period = prior_period
        self.current_period = current_period

    def calculate(self, period: str = None) -> float:
        """
        Calculate the year-over-year growth rate.

        This method calculates the growth rate between the prior period and current period,
        ignoring the period parameter passed in since the periods are fixed at initialization.
        The growth rate is calculated as: (current_value - prior_value) / prior_value.

        Args:
            period (str, optional): Ignored parameter to match Node interface. The periods
                used for calculation are set during initialization.

        Returns:
            float: The calculated growth rate as a decimal (e.g. 0.2 for 20% growth)
            float('nan'): If the prior period value is zero to avoid division by zero

        Example:
            # Create growth node
            revenue = FinancialStatementItemNode("revenue", {
                "2021": 1000.0,
                "2022": 1200.0
            })
            growth = YoYGrowthNode("revenue_growth", revenue, "2021", "2022")
            
            # Calculate growth rate
            rate = growth.calculate()  # Returns 0.2 (20% growth)
            
            # Period parameter is ignored
            rate = growth.calculate("2022")  # Still returns 0.2
        """
        prior_value = self.input_node.calculate(self.prior_period)
        current_value = self.input_node.calculate(self.current_period)
        if prior_value == 0:
            return float('nan')
        return (current_value - prior_value) / prior_value

class MultiPeriodStatNode(Node):
    """
    A node that calculates statistical measures across multiple time periods.

    This node takes an input node and calculates statistical measures (like standard deviation,
    mean, etc.) across a list of time periods. The specific statistical function is configurable
    via the stat_func parameter, defaulting to standard deviation.

    The node is useful for analyzing the variability or central tendency of financial metrics
    across multiple periods, such as revenue volatility or average profit margins.

    Args:
        name (str): The name/identifier for this statistical node
        input_node (Node): The node whose values will be analyzed across periods
        periods (List[str]): List of time periods to include in the statistical calculation
        stat_func (callable, optional): Statistical function to apply. Defaults to statistics.stdev.
            Must accept a list of numbers and return a single number.

    Attributes:
        name (str): The node's name/identifier
        input_node (Node): The source node for values
        periods (List[str]): The time periods to analyze
        stat_func (callable): The statistical function to apply

    Returns:
        float: The calculated statistical measure
        float('nan'): If fewer than 2 periods are provided

    Example:
        # Create node to calculate revenue volatility
        revenue = FinancialStatementItemNode("revenue", {
            "2020": 1000.0,
            "2021": 1200.0,
            "2022": 1100.0
        })
        volatility = MultiPeriodStatNode(
            "revenue_volatility",
            revenue,
            ["2020", "2021", "2022"]
        )
        
        # Calculate standard deviation
        std_dev = volatility.calculate()  # Returns standard deviation of revenue
    """
    def __init__(self, name: str, input_node: Node, periods: List[str], stat_func=statistics.stdev):
        self.name = name
        self.input_node = input_node
        self.periods = periods
        self.stat_func = stat_func

    def calculate(self, period: str = None) -> float:
        """
        Calculate the statistical measure across the configured time periods.

        This method retrieves values from the input node for each configured period and applies
        the statistical function to analyze those values. The period parameter is ignored since
        this node operates across multiple periods rather than a single period.

        Args:
            period (str, optional): Ignored. This node operates across the periods configured at initialization.

        Returns:
            float: The calculated statistical measure (e.g. standard deviation) across periods
            float('nan'): If fewer than 2 periods are provided (insufficient for statistical calculation)

        Example:
            # Create revenue volatility node
            revenue = FinancialStatementItemNode("revenue", {
                "2020": 1000.0,
                "2021": 1200.0,
                "2022": 1100.0
            })
            volatility = MultiPeriodStatNode(
                "revenue_volatility", 
                revenue,
                ["2020", "2021", "2022"]
            )

            # Calculate standard deviation
            std_dev = volatility.calculate()  # Returns ~100.0
        """
        values = [self.input_node.calculate(p) for p in self.periods]
        if len(values) < 2:
            return float('nan')
        return self.stat_func(values)
