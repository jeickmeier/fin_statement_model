from typing import Dict, List, Union
import pandas as pd
from .graph import Graph
from .nodes import FinancialStatementItemNode, Node, AdditionCalculationNode,SubtractionCalculationNode, MultiplicationCalculationNode, DivisionCalculationNode
from .forecasts import ForecastNode, FixedGrowthForecastNode, CurveGrowthForecastNode, StatisticalGrowForecastNode, CustomGrowForecastNode

class FinancialStatementGraph:
    """
    A graph specialized for financial statements.
    A graph-based representation of financial statements and calculations.

    This class provides functionality to:
    - Add raw financial statement items (like revenue, expenses, etc.) with their values
    - Define calculations between financial items (addition, subtraction, multiplication, division)
    - Calculate derived metrics for specific time periods
    
    The graph structure ensures proper dependency management and calculation order.
    Each node in the graph represents either a raw financial statement item or a calculation.

    Example:
        fsg = FinancialStatementGraph()
        fsg.add_financial_statement_item("revenue", {"2022": 1000.0})
        fsg.add_financial_statement_item("expenses", {"2022": 600.0})
        fsg.add_calculation("profit", ["revenue", "expenses"], "subtraction")
        profit_2022 = fsg.calculate_financial_statement("profit", "2022")  # Returns 400.0
    """
    def __init__(self, periods: list = None):
        self.graph = Graph()
        if periods is None:
            periods = []
        self.graph.periods = periods

    def add_financial_statement_item(self, name: str, values: Dict[str, float]):
        """
        Add a financial statement item node to the graph with historical values.

        Args:
            name: The name/identifier of the financial statement item (e.g. "revenue", "expenses")
            values: Dictionary mapping time periods to numerical values (e.g. {"2022": 1000.0})

        Raises:
            ValueError: If a node with the given name already exists in the graph

        Example:
            fsg.add_financial_statement_item("revenue", {"2022": 1000.0, "2023": 1200.0})
        """
        node = FinancialStatementItemNode(name, values)
        self.graph.add_node(node)

    def add_calculation(self, name: str, inputs: List[str], calculation_type: str):
        """
        Add a calculation node to the graph that performs arithmetic operations between input nodes.

        Args:
            name: The name/identifier for the calculation node (e.g. "gross_profit", "operating_margin")
            inputs: List of input node names that will be used in the calculation. Must be existing nodes.
            calculation_type: Type of arithmetic operation to perform. Valid values are:
                - 'addition': Adds all input values together
                - 'subtraction': Subtracts subsequent values from the first input
                - 'multiplication': Multiplies all input values together  
                - 'division': Divides first input by second input

        Raises:
            ValueError: If any input nodes don't exist in the graph
            ValueError: If an invalid calculation_type is provided

        Example:
            # Calculate gross profit as revenue - cost_of_goods_sold
            fsg.add_calculation("gross_profit", ["revenue", "cost_of_goods_sold"], "subtraction")

            # Calculate profit margin as net_income / revenue
            fsg.add_calculation("profit_margin", ["net_income", "revenue"], "division")
        """
        input_nodes = [self.graph.get_node(inp) for inp in inputs]
        if None in input_nodes:
            raise ValueError("One of the input nodes for calculation is missing.")
        if calculation_type == 'addition':
            node = AdditionCalculationNode(name, input_nodes)
        elif calculation_type == 'subtraction':
            node = SubtractionCalculationNode(name, input_nodes)
        elif calculation_type == 'multiplication':
            node = MultiplicationCalculationNode(name, input_nodes)
        elif calculation_type == 'division':
            node = DivisionCalculationNode(name, input_nodes)
        else:
            raise ValueError(f"Invalid calculation type '{calculation_type}'.")
        node.input_names = inputs
        self.graph.add_node(node)

    def calculate_financial_statement(self, node_name: str, period: str) -> float:
        """
        Calculate the value of a node for a specific time period.

        Args:
            node_name: The name/identifier of the node to calculate (e.g. "revenue", "gross_profit")
            period: The time period to calculate the value for (e.g. "FY2022")

        Returns:
            float: The calculated value for the specified node and period

        Raises:
            ValueError: If the node does not exist in the graph
            ValueError: If the period is not found in the node's data
            ValueError: If there is an error performing the calculation (e.g. division by zero)

        Example:
            # Calculate gross profit for FY2022
            gross_profit = fsg.calculate_financial_statement("gross_profit", "FY2022")
            
            # Calculate net profit margin for FY2021 
            npm = fsg.calculate_financial_statement("net_profit_margin", "FY2021")
        """
        return self.graph.calculate(node_name, period)
    
    def recalculate_all(self, copy_forward=True):
        """
        Recalculate all nodes in the graph for all periods.

        This method clears all node caches and recalculates values for every node in the graph
        in topologically sorted order to ensure dependencies are handled correctly.

        Args:
            copy_forward (bool): If True, copy forward the last historical value for any
                               FinancialStatementItemNode that doesn't have forecast periods
                               defined. Defaults to False.
        """
        # Clear all caches first
        self.graph.clear_all_caches()
        
        if copy_forward:
            # First, handle copying forward values for FinancialStatementItemNodes
            for node_name, node in self.graph.nodes.items():
                if isinstance(node, FinancialStatementItemNode):
                    # Skip nodes that already have forecasts
                    if any(isinstance(node, ForecastNode) for node in self.graph.nodes.values() 
                          if node.name == node_name):
                        continue
                    
                    # Find the last historical value
                    last_value = None
                    last_period = None
                    for period in sorted(node.values.keys()):
                        if period in self.graph.periods:
                            last_value = node.values[period]
                            last_period = period
                    
                    # Copy forward the last value to all subsequent periods
                    if last_value is not None and last_period is not None:
                        start_idx = self.graph.periods.index(last_period) + 1
                        for period in self.graph.periods[start_idx:]:
                            node.values[period] = last_value
        
        # Get topologically sorted order to ensure proper calculation order
        order = self.graph.topological_sort()
        
        # Recalculate each node for all periods
        for period in self.graph.periods:
            for node_name in order:
                node = self.graph.get_node(node_name)
                try:
                    node.calculate(period)
                except ValueError:
                    # Skip if period not valid for this node
                    continue

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert the financial statement graph into a pandas DataFrame.
        
        The DataFrame will have financial statement items as indices and periods as columns.
        Both raw financial statement items and calculated values will be included.

        Returns:
            pd.DataFrame: A DataFrame containing all financial statement values
                        with items as indices and periods as columns.

        Example:
            fsg = FinancialStatementGraph()
            fsg.add_financial_statement_item("revenue", {"2022": 1000.0, "2023": 1200.0})
            fsg.add_financial_statement_item("expenses", {"2022": 600.0, "2023": 700.0})
            fsg.add_calculation("profit", ["revenue", "expenses"], "subtraction")
            
            df = fsg.to_dataframe()
            # Results in:
            #           2022    2023
            # revenue  1000.0  1200.0
            # expenses  600.0   700.0
            # profit    400.0   500.0
        """
        # Get all periods from the graph
        periods = sorted(self.graph.periods)
        
        # Initialize data dictionary
        data = {}
        
        # Iterate through all nodes in the graph
        for node_name in self.graph.nodes:
            values = []
            for period in periods:
                try:
                    value = self.calculate_financial_statement(node_name, period)
                    values.append(value)
                except (ValueError, KeyError):
                    values.append(None)
            data[node_name] = values
            
        # Create DataFrame
        df = pd.DataFrame(data).T
        df.columns = periods
        
        return df

    def create_forecast(self, node_name: str, forecast_type: str, base_period: str, 
                       forecast_periods: List[str], growth_params: Union[float, List[float]]) -> None:
        """
        Create a forecast node and replace the existing node in the graph.

        Args:
            node_name (str): Name of the node to forecast (must exist in graph)
            forecast_type (str): Type of forecast ('fixed', 'curve', 'statistical', or 'custom')
            base_period (str): Last historical period to use as basis for forecasting
            forecast_periods (List[str]): List of future periods to generate forecasts for
            growth_params: Growth parameters for the forecast:
                - For 'fixed': float representing constant growth rate
                - For 'curve': List[float] representing growth rates for each period
                - For 'statistical': Callable that returns random growth rates
                - For 'custom': Callable that takes (period, prev_period, prev_value)

        Raises:
            ValueError: If node_name doesn't exist in graph
            ValueError: If invalid forecast_type is provided
            ValueError: If growth_params don't match forecast_type requirements

        Example:
            # Create fixed 5% growth forecast
            fsg.create_forecast("revenue", "fixed", "FY2022", ["FY2023", "FY2024"], 0.05)
            
            # Create curved growth forecast
            fsg.create_forecast("revenue", "curve", "FY2022", ["FY2023", "FY2024"], [0.05, 0.06])
        """
        # Validate node exists
        input_node = self.graph.get_node(node_name)
        if input_node is None:
            raise ValueError(f"Node '{node_name}' not found in graph.")

        # Create appropriate forecast node based on type
        if forecast_type == 'fixed':
            if not isinstance(growth_params, (int, float)):
                raise ValueError("Fixed growth forecast requires a single growth rate.")
            forecast_node = FixedGrowthForecastNode(
                input_node, base_period, forecast_periods, growth_params
            )
        elif forecast_type == 'curve':
            if not isinstance(growth_params, list) or len(growth_params) != len(forecast_periods):
                raise ValueError("Curve growth forecast requires list of growth rates matching forecast periods.")
            forecast_node = CurveGrowthForecastNode(
                input_node, base_period, forecast_periods, growth_params
            )
        elif forecast_type == 'statistical':
            if not callable(growth_params):
                raise ValueError("Statistical growth forecast requires a callable distribution function.")
            forecast_node = StatisticalGrowForecastNode(
                input_node, base_period, forecast_periods, growth_params
            )
        elif forecast_type == 'custom':
            if not callable(growth_params):
                raise ValueError("Custom growth forecast requires a callable growth function.")
            forecast_node = CustomGrowForecastNode(
                input_node, base_period, forecast_periods, growth_params
            )
        else:
            raise ValueError(f"Invalid forecast type '{forecast_type}'.")

        # Replace existing node with forecast node
        self.graph.replace_node(node_name, forecast_node)
