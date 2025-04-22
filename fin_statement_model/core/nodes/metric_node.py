"""Defines a node that calculates a value based on a registered metric."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional
import ast

if TYPE_CHECKING:
    from fin_statement_model.core.nodes.base import Node
    from fin_statement_model.core.graph.graph import Graph

from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.metrics import metric_registry
from fin_statement_model.core.nodes.calculation_nodes import FormulaCalculationNode
from fin_statement_model.core.errors import (
    ConfigurationError,
    CalculationError,
    MetricError,
)

logger = logging.getLogger(__name__)


class MetricCalculationNode(Node):
    """Calculates a value based on a predefined metric definition.

    This node looks up a metric in the `metric_registry`, resolves its
    input nodes from the provided graph, and delegates the actual calculation
    to an underlying `FormulaCalculationNode` based on the metric's formula.

    Attributes:
        name (str): The unique identifier for this metric node.
        metric_name (str): The key of the metric in the `metric_registry`.
        graph (GraphType): The financial statement graph instance used to resolve
            input nodes.
        definition (Dict): The loaded definition dictionary for the metric.
        calc_node (FormulaCalculationNode): The internal node performing the
            calculation.

    Example:
        >>> # Assume 'gross_profit' metric is registered:
        >>> #   inputs: ["revenue", "cogs"]
        >>> #   formula: "revenue - cogs"
        >>> # Assume graph object exists and metric_registry is populated
        >>> # (Need imports: FinancialStatementItemNode, metric_registry)
        >>> class MockGraph:
        ...     def get_node(self, name):
        ...         nodes = {
        ...             "revenue_item": FinancialStatementItemNode("revenue_item", {"2023": 500}),
        ...             "cogs_item": FinancialStatementItemNode("cogs_item", {"2023": 200})
        ...         }
        ...         return nodes.get(name)
        >>> graph = MockGraph()
        >>> # We need to register the metric first (or assume it's done elsewhere)
        >>> try:
        ...     metric_registry.register({
        ...         "gross_profit": {
        ...             "inputs": ["revenue_item", "cogs_item"],
        ...             "formula": "revenue_item - cogs_item",
        ...             "description": "Revenue minus Cost of Goods Sold."
        ...         }
        ...     })
        ... except Exception as e: # Handle potential re-registration
        ...     if "already registered" not in str(e): raise e
        >>>
        >>> gp_node = MetricCalculationNode(
        ...     "calculated_gp",
        ...     metric_name="gross_profit",
        ...     graph=graph
        ... )
        >>> # print(gp_node.calculate("2023")) # Actual result depends on live registry/graph
        >>> # Expected: 300.0
    """

    def __init__(self, name: str, metric_name: str, graph: Optional[Graph]):
        """Initialize the metric calculation node.

        Retrieves the metric definition, resolves input nodes from the graph,
        and sets up the underlying formula calculation node.

        Args:
            name (str): The identifier for this node.
            metric_name (str): The key identifying the metric in the registry.
            graph (GraphType): The graph instance containing potential input nodes.

        Raises:
            ConfigurationError: If the `metric_name` is not found in the registry,
                or if an input node specified by the metric is not found in the graph.
            ValueError: If the metric definition is invalid (e.g., missing formula
                or inputs).
            TypeError: If input nodes resolved from the graph are not `Node` instances.
        """
        super().__init__(name)
        self.metric_name = metric_name
        self.graph = graph
        self._formula_string: Optional[str] = None
        self._parsed_expr: Optional[ast.Expression] = None
        self._load_metric_definition()

    def _load_metric_definition(self):
        """Load and validate the metric definition from the registry."""
        try:
            self.definition = metric_registry.get(self.metric_name)
        except KeyError:
            raise MetricError(f"Metric '{self.metric_name}' not found in registry.")

        # Validate required fields in definition
        required = ["description", "inputs", "formula"]
        if not all(k in self.definition for k in required):
            missing = [k for k in required if k not in self.definition]
            raise ValueError(
                f"Metric definition '{self.metric_name}' is invalid: missing required field(s): {missing}"
            )

        input_nodes: dict[str, Node] = {}
        missing_inputs = []
        for input_name in self.definition["inputs"]:
            node = self.graph.get_node(input_name)
            if node is None:
                missing_inputs.append(input_name)
            elif not isinstance(node, Node):
                raise TypeError(
                    f"Resolved input '{input_name}' for metric '{self.metric_name}' is not a Node instance."
                )
            else:
                input_nodes[input_name] = node

        if missing_inputs:
            raise ConfigurationError(
                f"Input node(s) required by metric '{self.metric_name}' not found in graph: {missing_inputs}"
            )

        calc_node_name = f"_{self.name}_formula_calc"
        try:
            self.calc_node = FormulaCalculationNode(
                calc_node_name, input_nodes, self.definition["formula"]
            )
        except ValueError as e:
            raise ValueError(
                f"Error creating formula node for metric '{self.metric_name}' (node '{self.name}'): {e}"
            ) from e

    def calculate(self, period: str, graph: Optional[Graph] = None) -> float:
        """Calculate the metric's value for the specified period.

        Delegates the calculation to the internal `FormulaCalculationNode`.

        Args:
            period (str): The time period for which to calculate the metric.
            graph (GraphType): The graph instance containing potential input nodes.

        Returns:
            float: The calculated metric value.

        Raises:
            CalculationError: If an error occurs during the underlying formula
                evaluation (e.g., missing input data for the period, type errors).
        """
        try:
            return self.calc_node.calculate(period)
        except Exception as e:
            raise CalculationError(
                message=f"Failed to calculate metric '{self.metric_name}' for node '{self.name}'",
                node_id=self.name,
                period=period,
                details={"original_error": str(e)},
            ) from e

    def get_dependencies(self) -> list[str]:
        """Return the names of the input nodes required by the metric definition."""
        return self.definition.get("inputs", [])

    def has_calculation(self) -> bool:
        """Indicate that this node performs a calculation."""
        return True
