from pathlib import Path
from typing import Dict, List, Union, Optional
import pandas as pd

from .graph import Graph
from .importers.excel_importer import ExcelImporter
from .importers.mapping_service import MappingService
from .nodes import FinancialStatementItemNode, Node, AdditionCalculationNode, \
    SubtractionCalculationNode, MultiplicationCalculationNode, DivisionCalculationNode, CalculationNode, \
    MetricCalculationNode
from .forecasts import ForecastNode, FixedGrowthForecastNode, CurveGrowthForecastNode, StatisticalGrowForecastNode, CustomGrowForecastNode
from .metrics import METRIC_DEFINITIONS

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

    def to_dataframe(self, recalculate: bool = True) -> pd.DataFrame:
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

        if recalculate:
            # Recalculate all nodes to ensure all values are up to date
            self.recalculate_all()

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

    def __str__(self) -> str:
        """
        Returns a string representation of the financial statement graph structure.

        The string includes:
        - All time periods in the graph
        - Financial statement items (raw data nodes)
        - Calculations between items, showing their input dependencies
        - Financial metrics that have been defined
        - Forecasted items with their forecast types

        Returns:
            str: A formatted string containing the graph summary
        """
        # Get all nodes from the graph
        nodes = list(self.graph.nodes.keys())
        
        # Categorize nodes
        financial_items = []
        calculations = []
        metrics = []
        forecasts = []
        
        for node_name in nodes:
            node = self.graph.nodes[node_name]
            if isinstance(node, FinancialStatementItemNode):
                financial_items.append(node_name)
            elif isinstance(node, CalculationNode):
                calculations.append(node_name)
            elif isinstance(node, MetricCalculationNode):
                metrics.append(node_name)
            elif isinstance(node, ForecastNode):
                forecasts.append(node_name)
        
        output = ["Financial Statement Graph Summary"]
        output.append("=" * 40)
        
        output.append(f"\nPeriods: {', '.join(self.graph.periods)}")
        
        output.append("\nFinancial Statement Items:")
        output.append("-" * 25)
        # Get items in topological order
        topo_order = list(reversed(self.graph.topological_sort()))
        
        # Filter and display items in topological order
        for item in topo_order:
            if item in financial_items + forecasts:
                if item in forecasts:
                    output.append(f"• {item} (w Forecasts)")
                else:
                    output.append(f"• {item}")
        
        output.append("\nCalculations:")
        output.append("-" * 25)
        for calc in sorted(calculations):
            node = self.graph.nodes[calc]
            if hasattr(node, 'input_names'):
                inputs = node.input_names
                output.append(f"• {calc} = f({', '.join(inputs)})")
        
        output.append("\nMetrics:")
        output.append("-" * 25)
        for metric in sorted(metrics):
            output.append(f"• {metric}")
        
        output.append("\nForecasted Items:")
        output.append("-" * 25)
        for forecast in sorted(forecasts):
            node = self.graph.nodes[forecast]
            if isinstance(node, ForecastNode):
                forecast_type = node.__class__.__name__.replace('ForecastNode', '')
                base_info = f"• {forecast} (type: {forecast_type})"
                
                # Add specific forecast parameters based on type
                if isinstance(node, FixedGrowthForecastNode):
                    output.append(f"{base_info}, growth rate: {node.growth_rate:.1%}")
                
                elif isinstance(node, CurveGrowthForecastNode):
                    growth_rates = [f"{rate:.1%}" for rate in node.growth_rates]
                    periods = node.forecast_periods
                    curve_info = [f"{p}: {r}" for p, r in zip(periods, growth_rates)]
                    output.append(f"{base_info}\n  Growth curve: {', '.join(curve_info)}")
                
                elif isinstance(node, StatisticalGrowForecastNode):
                    # Get the source code of the lambda function
                    import inspect
                    lambda_source = inspect.getsource(node.distribution_callable)
                    # Extract just the function call part (after the lambda:)
                    func_call = lambda_source.split('lambda:')[1].strip()
                    output.append(f"{base_info}\n  Distribution: {func_call}")
                
                elif isinstance(node, CustomGrowForecastNode):
                    output.append(f"{base_info}\n  Custom growth function: {node.growth_function.__name__}")
                
                else:
                    output.append(base_info)
        
        return "\n".join(output)

    def __add__(self, other: 'FinancialStatementGraph') -> 'FinancialStatementGraph':
        """
        Add (merge) two FinancialStatementGraphs into a single graph.
        
        Args:
            other: The FinancialStatementGraph to merge with this graph
            
        Returns:
            FinancialStatementGraph: A new graph containing all nodes from both graphs
            
        Raises:
            ValueError: If there are conflicting node names between graphs
            ValueError: If there are conflicting values for the same node and period
            
        Example:
            # Create separate graphs for income statement and balance sheet
            income_graph = FinancialStatementGraph()
            balance_graph = FinancialStatementGraph()
            
            # Add nodes to each graph...
            
            # Merge the graphs using + operator
            combined_graph = income_graph + balance_graph
        """
        # Create a new graph with combined periods
        all_periods = set(self.graph.periods) | set(other.graph.periods)
        merged = FinancialStatementGraph(list(sorted(all_periods)))
        
        # Helper function to copy a node to the merged graph
        def copy_node(node: Node, source_graph: Graph):
            if isinstance(node, FinancialStatementItemNode):
                merged.add_financial_statement_item(node.name, node.values)
            elif isinstance(node, CalculationNode):
                merged.add_calculation(node.name, node.input_names, 
                                    node.__class__.__name__.replace('CalculationNode', '').lower())
            elif isinstance(node, ForecastNode):
                # Copy forecast configuration
                base_node = source_graph.get_node(node.input_node.name)
                if isinstance(node, FixedGrowthForecastNode):
                    merged.create_forecast(base_node.name, 'fixed', 
                                        node.base_period, node.forecast_periods, 
                                        node.growth_rate)
                elif isinstance(node, CurveGrowthForecastNode):
                    merged.create_forecast(base_node.name, 'curve',
                                        node.base_period, node.forecast_periods,
                                        node.growth_rates)
                elif isinstance(node, StatisticalGrowForecastNode):
                    merged.create_forecast(base_node.name, 'statistical',
                                        node.base_period, node.forecast_periods,
                                        node.distribution_callable)
                elif isinstance(node, CustomGrowForecastNode):
                    merged.create_forecast(base_node.name, 'custom',
                                        node.base_period, node.forecast_periods,
                                        node.growth_function)
        
        # First, copy all nodes from the current graph
        for node in self.graph.nodes.values():
            if node.name in merged.graph.nodes:
                raise ValueError(f"Duplicate node name found: {node.name}")
            copy_node(node, self.graph)
        
        # Then copy nodes from the other graph
        for node in other.graph.nodes.values():
            if node.name in merged.graph.nodes:
                # Check if values match for overlapping periods
                existing_node = merged.graph.get_node(node.name)
                if isinstance(node, FinancialStatementItemNode):
                    for period, value in node.values.items():
                        if period in existing_node.values:
                            if abs(existing_node.values[period] - value) > 1e-10:
                                raise ValueError(
                                    f"Conflicting values for node {node.name} in period {period}: "
                                    f"{existing_node.values[period]} != {value}"
                                )
                continue
            copy_node(node, other.graph)
        
        # Recalculate all values in the merged graph
        merged.recalculate_all()
        
        return merged

    def import_from_excel(self, file_path: Union[str, Path], sheet_names: Optional[List[str]] = None,
                         date_format: str = "%Y-%m-%d", metric_definitions: Optional[Dict] = None,
                         similarity_threshold: float = 0.85) -> None:
        """
        Import financial data from an Excel file into the graph.

        This method uses ExcelImporter to parse the Excel file and MappingService to normalize
        metric names, then integrates the data into the graph structure.

        Args:
            file_path: Path to the Excel file containing financial data
            sheet_names: Optional list of specific sheets to process. If None, processes all sheets.
            date_format: Format string for parsing date columns (default: "%Y-%m-%d")
            metric_definitions: Optional custom metric definitions. If None, uses METRIC_DEFINITIONS.
            similarity_threshold: Threshold for metric name matching (default: 0.85)

        Raises:
            FileNotFoundError: If the Excel file doesn't exist
            ValueError: If the file format is invalid or if there are mapping errors
            MappingError: If metric mapping fails for any items

        Example:
            # Import from Excel with default settings
            fsg.import_from_excel("financial_data.xlsx")

            # Import specific sheets with custom date format
            fsg.import_from_excel(
                "financial_data.xlsx",
                sheet_names=["Income Statement", "Balance Sheet"],
                date_format="%m/%d/%Y"
            )
        """
        # Initialize importers
        excel_importer = ExcelImporter(file_path, sheet_names, date_format)
        mapping_service = MappingService(
            metric_definitions or METRIC_DEFINITIONS,
            similarity_threshold
        )

        try:
            # Read and process Excel data
            financial_data, periods = excel_importer.get_financial_data()

            # Update graph periods
            self.graph.periods = sorted(list(set(self.graph.periods) | set(periods)))

            # Map metric names and add to graph
            mappings = mapping_service.map_metric_names(list(financial_data.keys()))

            for original_name, (mapped_name, confidence) in mappings.items():
                if mapped_name in METRIC_DEFINITIONS:
                    # If it's a defined metric, add it through the metric system
                    self.add_metric(mapped_name)
                    continue

                # Add as financial statement item
                self.add_financial_statement_item(mapped_name, financial_data[original_name])

            # Recalculate all values to ensure consistency
            self.recalculate_all()

        except Exception as e:
            # Wrap any underlying errors with context
            raise ValueError(f"Error importing Excel data: {str(e)}") from e

    def add_metric(self, metric_name: str, node_name: str = None, _processing=None):
        """
        Add a metric calculation node to the graph based on predefined metric definitions.

        This method adds a new metric node to the financial statement graph, handling all dependencies
        and ensuring proper calculation order. It will recursively add any required metric nodes that
        don't yet exist in the graph.

        Args:
            metric_name: The name of the metric to add (must exist in METRIC_DEFINITIONS)
            node_name: Optional custom name for the node (defaults to metric_name)
            _processing: Internal set to detect cyclic dependencies (do not set manually)

        Raises:
            ValueError: If the metric is not found in METRIC_DEFINITIONS
            ValueError: If a required input node is missing from the graph
            ValueError: If a cyclic dependency is detected between metrics

        Example:
            # Add gross profit metric
            fsg.add_metric("gross_profit")

            # Add net profit margin (will automatically add gross_profit if needed)
            fsg.add_metric("net_profit_margin")

            # Add metric with custom node name
            fsg.add_metric("gross_profit", node_name="adjusted_gross_profit")
        """
        if metric_name not in METRIC_DEFINITIONS:
            raise ValueError(f"Metric '{metric_name}' not found in METRIC_DEFINITIONS.")

        if _processing is None:
            _processing = set()

        if metric_name in _processing:
            raise ValueError(f"Cyclic dependency detected for metric '{metric_name}'.")
        _processing.add(metric_name)

        definition = METRIC_DEFINITIONS[metric_name]
        required_inputs = definition['inputs']

        for inp in required_inputs:
            node = self.graph.get_node(inp)
            if node is None:
                if inp in METRIC_DEFINITIONS:
                    # It's another metric, add it first
                    self.add_metric(inp, inp, _processing=_processing)
                else:
                    # It's a raw data node - must be present before adding metric
                    if self.graph.get_node(inp) is None:
                        raise ValueError(
                            f"Required input '{inp}' for metric '{metric_name}' not found. "
                            f"Please ensure '{inp}' is added as a financial statement item node."
                        )

        metric_node_name = node_name or metric_name
        if self.graph.get_node(metric_node_name) is not None:
            _processing.remove(metric_name)
            return

        metric_node = MetricCalculationNode(metric_node_name, metric_name, self.graph)
        self.graph.add_node(metric_node)

        _processing.remove(metric_name)
