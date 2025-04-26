"""Define the MetricCalculation class for financial metrics.

This module provides the base class for all metric calculations in the financial statement model.
"""

from typing import Optional

from fin_statement_model.core.nodes.base import Node


class MetricCalculation(Node):
    """Base class for all metric calculations in the financial statement model.

    This class provides the foundation for implementing specific financial metrics.
    Subclasses should implement the calculate method to provide the specific
    calculation logic for the metric.

    Attributes:
        name (str): The name of the metric.
        inputs (Dict[str, Node]): Mapping of input names to their corresponding nodes.
        description (Optional[str]): Optional description of the metric.
    """

    def __init__(
        self,
        name: str,
        inputs: dict[str, Node],
        description: Optional[str] = None,
    ):
        """Initialize a new metric calculation.

        Args:
            name: The name of the metric.
            inputs: Mapping of input names to their corresponding nodes.
            description: Optional description of the metric.
        """
        super().__init__(name)
        self.inputs = inputs
        self.description = description

    def calculate(self, period: str) -> float:
        """Calculate the metric value for the given period.

        This method must be implemented by subclasses to provide the specific
        calculation logic for the metric.

        Args:
            period: The period for which to calculate the metric.

        Returns:
            The calculated metric value.

        Raises:
            MetricError: If the calculation fails.
        """
        raise NotImplementedError("Subclasses must implement calculate()")

    def get_dependencies(self) -> list[str]:
        """Get the names of all input nodes this metric depends on.

        Returns:
            A list of input node names.
        """
        return list(self.inputs.keys())

    def has_calculation(self) -> bool:
        """Check if this node has a calculation defined.

        Returns:
            True, as metric nodes always have calculations.
        """
        return True
