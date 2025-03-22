from abc import ABC, abstractmethod
from typing import Dict, List
from .metrics import METRIC_DEFINITIONS
import ast
import operator

class Node(ABC):
    name: str

    @abstractmethod
    def calculate(self, period: str) -> float:
        pass

    def clear_cache(self):
        # Default: no cache
        pass

class FinancialStatementItemNode(Node):
    """
    Represents a financial statement item with values for multiple periods.

    This node type stores raw financial statement data like revenue, expenses, assets, etc.
    Each node contains a mapping of time periods to their corresponding numerical values.

    Attributes:
        name (str): The identifier for this financial statement item (e.g. "revenue", "expenses")
        values (Dict[str, float]): Dictionary mapping time periods to values (e.g. {"2022": 1000.0})

    Example:
        # Create revenue node with historical values
        revenue = FinancialStatementItemNode("revenue", {
            "2022": 1000.0,
            "2021": 900.0,
            "2020": 800.0
        })

        # Calculate revenue for 2022
        revenue_2022 = revenue.calculate("2022")  # Returns 1000.0
    """
    def __init__(self, name: str, values: Dict[str, float]):
        self.name = name
        self.values = values

    def calculate(self, period: str) -> float:
        return self.values.get(period, 0.0)

class CalculationNode(Node):
    """
    Base class for calculation nodes that perform arithmetic operations on input nodes.

    This abstract class defines the interface and common functionality for nodes that
    perform calculations between other nodes in the financial statement graph.
    Specific calculation types (addition, subtraction, etc.) inherit from this class
    and implement their own calculation logic.

    Attributes:
        name (str): The identifier for this calculation node (e.g. "gross_profit")
        inputs (List[Node]): List of input nodes used in the calculation

    Example:
        # Create an addition calculation node
        revenue = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        other_income = FinancialStatementItemNode("other_income", {"2022": 100.0})
        total_income = AdditionCalculationNode("total_income", [revenue, other_income])

        # Calculate total income for 2022
        total_2022 = total_income.calculate("2022")  # Returns 1100.0
    """
    def __init__(self, name: str, inputs: List[Node]):
        self.name = name
        self.inputs = inputs
        self.input_names = []  # Will be set by FinancialStatementGraph.add_calculation

    @abstractmethod
    def calculate(self, period: str) -> float:
        pass

class AdditionCalculationNode(CalculationNode):
    """
    A calculation node that adds together values from multiple input nodes.

    This node performs addition of values from all input nodes for a given time period.
    It inherits from CalculationNode and implements the calculate() method to sum values.

    Example:
        # Create nodes with historical values
        revenue = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        other_income = FinancialStatementItemNode("other_income", {"2022": 100.0})
        
        # Create addition node to sum revenue and other income
        total_income = AdditionCalculationNode("total_income", [revenue, other_income])
        
        # Calculate total income for 2022
        total_2022 = total_income.calculate("2022")  # Returns 1100.0
    """
    def calculate(self, period: str) -> float:
        return sum(i.calculate(period) for i in self.inputs)

class SubtractionCalculationNode(CalculationNode):
    """
    A calculation node that subtracts subsequent input values from the first input.

    This node performs subtraction between input nodes for a given time period.
    It takes the first input node's value and subtracts all subsequent input node values from it.
    It inherits from CalculationNode and implements the calculate() method for subtraction.

    Example:
        # Create nodes with historical values
        revenue = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        expenses = FinancialStatementItemNode("expenses", {"2022": 600.0})
        
        # Create subtraction node to calculate profit
        profit = SubtractionCalculationNode("profit", [revenue, expenses])
        
        # Calculate profit for 2022
        profit_2022 = profit.calculate("2022")  # Returns 400.0
    """
    def calculate(self, period: str) -> float:
        result = self.inputs[0].calculate(period)
        for inp in self.inputs[1:]:
            result -= inp.calculate(period)
        return result

class MultiplicationCalculationNode(CalculationNode):
    """
    A calculation node that multiplies values from multiple input nodes.

    This node performs multiplication of values from all input nodes for a given time period.
    It inherits from CalculationNode and implements the calculate() method to multiply values.

    Example:
        # Create nodes with historical values
        revenue = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        margin = FinancialStatementItemNode("margin", {"2022": 0.4})
        
        # Create multiplication node to calculate profit
        profit = MultiplicationCalculationNode("profit", [revenue, margin])
        
        # Calculate profit for 2022
        profit_2022 = profit.calculate("2022")  # Returns 400.0
    """
    def calculate(self, period: str) -> float:
        result = 1
        for inp in self.inputs:
            result *= inp.calculate(period)
        return result

class DivisionCalculationNode(CalculationNode):
    """
    A calculation node that divides values from input nodes sequentially.

    This node performs division between input nodes for a given time period.
    It takes the first input node's value and divides it by each subsequent input node value in sequence.
    It inherits from CalculationNode and implements the calculate() method for division.
    
    The node will raise a ZeroDivisionError if any divisor (input after the first) equals zero.

    Example:
        # Create nodes with historical values
        net_income = FinancialStatementItemNode("net_income", {"2022": 400.0})
        revenue = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        
        # Create division node to calculate profit margin
        margin = DivisionCalculationNode("profit_margin", [net_income, revenue])
        
        # Calculate margin for 2022
        margin_2022 = margin.calculate("2022")  # Returns 0.4 (40%)

    Raises:
        ZeroDivisionError: If any divisor (input after the first) equals zero
    """
    def calculate(self, period: str) -> float:
        result = self.inputs[0].calculate(period)
        for inp in self.inputs[1:]:
            divisor = inp.calculate(period)
            if divisor == 0:
                raise ZeroDivisionError("Division by zero in division node.")
            result /= divisor
        return result

class MetricCalculationNode(Node):
    """
    A node that calculates a metric defined in METRIC_DEFINITIONS.

    This node represents a financial metric calculation that is defined in the METRIC_DEFINITIONS dictionary.
    It creates an appropriate calculation node (Addition, Subtraction, Multiplication, or Division) based on
    the metric definition and handles retrieving the required input nodes from the graph.

    The node acts as a wrapper around the underlying calculation node, delegating the actual calculation
    while handling the metric-specific setup and validation.

    Args:
        name (str): The name/identifier for this metric node
        metric_name (str): The name of the metric as defined in METRIC_DEFINITIONS
        graph: The financial statement graph containing the input nodes

    Attributes:
        name (str): The node's name/identifier
        metric_name (str): The name of the metric being calculated
        graph: Reference to the containing graph
        definition (dict): The metric's definition from METRIC_DEFINITIONS
        calc_node (CalculationNode): The underlying calculation node that performs the actual computation

    Raises:
        ValueError: If the metric_name is not found in METRIC_DEFINITIONS
        ValueError: If any required input nodes are not found in the graph
        ValueError: If the calculation type in the metric definition is invalid

    Example:
        # Create metric node for net profit margin
        npm_node = MetricCalculationNode("npm", "net_profit_margin", graph)
        
        # Calculate net profit margin for 2022
        npm_2022 = npm_node.calculate("2022")
    """
    def __init__(self, name: str, metric_name: str, graph):
        self.name = name
        self.metric_name = metric_name
        self.graph = graph
        self.definition = METRIC_DEFINITIONS[metric_name]

        # Create dictionary of input nodes
        input_nodes = {}
        for inp in self.definition["inputs"]:
            node = self.graph.get_node(inp)
            if node is None:
                raise ValueError(f"Input node '{inp}' for metric '{metric_name}' not found.")
            input_nodes[inp] = node

        self.calc_node = FormulaCalculationNode(
            name + "_calc",
            input_nodes,
            self.definition["formula"]
        )

    def calculate(self, period: str) -> float:
        return self.calc_node.calculate(period)

class TwoPeriodAverageNode(Node):
    """
    A node that calculates the average of a given metric's values over the current and previous period.

    This node takes an input node and calculates the average value between the current period and
    the immediately preceding period based on the graph's defined period ordering. The node requires
    that the graph has an ordered list of periods to determine the previous period.

    Args:
        name (str): The name/identifier for this average calculation node
        input_node (Node): The node whose values will be averaged
        graph: The financial statement graph containing the period definitions

    Attributes:
        name (str): The node's name/identifier
        input_node (Node): Reference to the input node being averaged
        graph: Reference to the containing graph

    Raises:
        ValueError: If the graph does not have defined periods
        ValueError: If the requested period is not found in the graph's periods
        ValueError: If there is no previous period available (e.g. first period)

    Example:
        # Create average total assets node
        total_assets = FinancialStatementItemNode("total_assets", {
            "2021": 1000.0,
            "2022": 1200.0
        })
        graph.periods = ["2021", "2022"]
        avg_assets = TwoPeriodAverageNode("avg_total_assets", total_assets, graph)
        
        # Calculate average for 2022
        avg_2022 = avg_assets.calculate("2022")  # Returns 1100.0
    """
    def __init__(self, name: str, input_node: Node, graph):
        self.name = name
        self.input_node = input_node
        self.graph = graph

    def calculate(self, period: str) -> float:
        """
        Calculate the average value between the current period and previous period.

        This method retrieves values from the input node for both the specified period and
        the immediately preceding period based on the graph's period ordering. It then
        calculates the arithmetic mean of these two values.

        Args:
            period (str): The current period for which to calculate the average (e.g. "2022")

        Returns:
            float: The arithmetic mean of the current and previous period values

        Raises:
            ValueError: If the graph does not have defined periods
            ValueError: If the requested period is not found in the graph's periods
            ValueError: If there is no previous period available (e.g. first period)

        Example:
            # Create average total assets node
            total_assets = FinancialStatementItemNode("total_assets", {
                "2021": 1000.0,
                "2022": 1200.0
            })
            graph.periods = ["2021", "2022"]
            avg_assets = TwoPeriodAverageNode("avg_total_assets", total_assets, graph)
            
            # Calculate average for 2022
            avg_2022 = avg_assets.calculate("2022")  # Returns 1100.0
            
            # Will raise ValueError since 2021 has no previous period
            avg_2021 = avg_assets.calculate("2021")  # Raises ValueError
        """
        # Ensure graph.periods is available and sorted
        if not hasattr(self.graph, 'periods') or not self.graph.periods:
            raise ValueError("Graph does not have a defined list of periods.")

        periods_list = self.graph.periods
        if period not in periods_list:
            raise ValueError(f"Period '{period}' not found in graph.periods.")

        idx = periods_list.index(period)
        if idx == 0:
            # If there's no previous period, we can't calculate an average
            # Decide how to handle this. Perhaps return just current value or raise an error.
            raise ValueError(f"No previous period available before '{period}' to calculate average.")

        previous_period = periods_list[idx - 1]

        current_value = self.input_node.calculate(period)
        previous_value = self.input_node.calculate(previous_period)

        return (current_value + previous_value) / 2.0

class FormulaCalculationNode(Node):
    """
    A node that calculates values based on a mathematical formula string.
    
    Attributes:
        name (str): The identifier for this calculation node
        inputs (Dict[str, Node]): Dictionary mapping input names to their nodes
        formula (str): The formula string to evaluate (e.g. "revenue - cost_of_goods_sold")
        _ast: The parsed abstract syntax tree of the formula
    """
    
    # Supported operators
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
    }
    
    def __init__(self, name: str, inputs: Dict[str, Node], formula: str):
        self.name = name
        self.inputs = inputs
        self.formula = formula
        self._ast = ast.parse(formula, mode='eval').body
        
    def calculate(self, period: str) -> float:
        return self._evaluate(self._ast, period)
    
    def _evaluate(self, node, period: str) -> float:
        """Recursively evaluates the AST of the formula."""
        
        # Handle numbers
        if isinstance(node, ast.Num):
            return float(node.n)
            
        # Handle variables (input nodes)
        if isinstance(node, ast.Name):
            if node.id not in self.inputs:
                raise ValueError(f"Unknown variable '{node.id}' in formula")
            return self.inputs[node.id].calculate(period)
            
        # Handle binary operations
        if isinstance(node, ast.BinOp):
            left = self._evaluate(node.left, period)
            right = self._evaluate(node.right, period)
            op = type(node.op)
            if op not in self.OPERATORS:
                raise ValueError(f"Unsupported operator {op.__name__}")
            return self.OPERATORS[op](left, right)
            
        # Handle unary operations (like negative numbers)
        if isinstance(node, ast.UnaryOp):
            operand = self._evaluate(node.operand, period)
            op = type(node.op)
            if op not in self.OPERATORS:
                raise ValueError(f"Unsupported unary operator {op.__name__}")
            return self.OPERATORS[op](operand)
            
        raise ValueError(f"Unsupported syntax in formula: {ast.dump(node)}")