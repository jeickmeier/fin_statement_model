"""Custom exception classes for the financial statement model.

This module defines exception classes for specific error cases,
allowing for more precise error handling and better error messages.
"""

from typing import Optional, Any


class FinancialModelError(Exception):
    """Base exception for all financial statement model errors.

    All custom exceptions raised within the library should inherit from this class.

    Examples:
        >>> raise FinancialModelError("An error occurred.")
    """

    def __init__(self, message: str):
        """Initialize the FinancialModelError.

        Args:
            message: A human-readable description of the error.
        """
        self.message = message
        super().__init__(self.message)


class ConfigurationError(FinancialModelError):
    """Error raised for invalid configuration files or objects.

    This typically occurs when parsing or validating configuration data,
    such as YAML files defining metrics or statement structures.

    Examples:
        >>> raise ConfigurationError("Invalid syntax", config_path="config.yaml")
        >>> raise ConfigurationError(
        ...     "Missing required fields",
        ...     config_path="metrics.yaml",
        ...     errors=["Missing 'formula' for 'revenue'"]
        ... )
    """

    def __init__(
        self,
        message: str,
        config_path: Optional[str] = None,
        errors: Optional[list[Any]] = None,
    ):
        """Initialize the ConfigurationError.

        Args:
            message: The base error message.
            config_path: Optional path to the configuration file where the error occurred.
            errors: Optional list of specific validation errors found.
        """
        self.config_path = config_path
        self.errors = errors or []

        if config_path and self.errors:
            full_message = (
                f"{message} in {config_path}: {' ; '.join(str(e) for e in self.errors)}"
            )
        elif config_path:
            full_message = f"{message} in {config_path}"
        elif self.errors:
            full_message = f"{message}: {' ; '.join(str(e) for e in self.errors)}"
        else:
            full_message = message

        super().__init__(full_message)


class CalculationError(FinancialModelError):
    """Error raised during calculation operations.

    Indicates a problem while computing the value of a node, often due
    to issues with the calculation logic, input data, or strategy used.

    Examples:
        >>> raise CalculationError("Division by zero", node_id="profit_margin", period="2023-Q1")
        >>> raise CalculationError(
        ...     "Incompatible input types",
        ...     node_id="total_assets",
        ...     details={"input_a_type": "str", "input_b_type": "int"}
        ... )
    """

    def __init__(
        self,
        message: str,
        node_id: Optional[str] = None,
        period: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize the CalculationError.

        Args:
            message: The base error message.
            node_id: Optional ID of the node where the calculation failed.
            period: Optional period for which the calculation failed.
            details: Optional dictionary containing additional context about the error.
        """
        self.node_id = node_id
        self.period = period
        self.details = details or {}

        context = []
        if node_id:
            context.append(f"node '{node_id}'")
        if period:
            context.append(f"period '{period}'")

        full_message = f"{message} for {' and '.join(context)}" if context else message

        # Append details to the message for better context
        if self.details:
            details_str = ", ".join(f'{k}="{v}"' for k, v in self.details.items())
            # Prioritize showing the original underlying error if captured
            original_error_str = self.details.get("original_error")
            if original_error_str:
                full_message = f"{full_message}: {original_error_str}"
            else:
                full_message = f"{full_message} (Details: {details_str})"

        super().__init__(full_message)


class NodeError(FinancialModelError):
    """Error raised for issues related to graph nodes.

    Covers issues like trying to access a non-existent node,
    invalid node configurations, or type mismatches related to nodes.

    Examples:
        >>> raise NodeError("Node not found", node_id="non_existent_node")
        >>> raise NodeError("Invalid node type for operation", node_id="revenue")
    """

    def __init__(self, message: str, node_id: Optional[str] = None):
        """Initialize the NodeError.

        Args:
            message: The base error message.
            node_id: Optional ID of the node related to the error.
        """
        self.node_id = node_id

        full_message = f"{message} for node '{node_id}'" if node_id else message

        super().__init__(full_message)


class MissingInputError(FinancialModelError):
    """Error raised when a required calculation input is missing.

    Occurs when a calculation node needs data from another node for a
    specific period, but that data is unavailable.

    Examples:
        >>> raise MissingInputError(
        ...     "Required input data unavailable",
        ...     node_id="cogs",
        ...     input_name="inventory",
        ...     period="2023-12-31"
        ... )
    """

    def __init__(
        self,
        message: str,
        node_id: Optional[str] = None,
        input_name: Optional[str] = None,
        period: Optional[str] = None,
    ):
        """Initialize the MissingInputError.

        Args:
            message: The base error message.
            node_id: Optional ID of the node requiring the input.
            input_name: Optional name or ID of the missing input node.
            period: Optional period for which the input was missing.
        """
        self.node_id = node_id
        self.input_name = input_name
        self.period = period

        context = []
        if node_id:
            context.append(f"node '{node_id}'")
        if input_name:
            context.append(f"input '{input_name}'")
        if period:
            context.append(f"period '{period}'")

        full_message = f"{message} for {' in '.join(context)}" if context else message

        super().__init__(full_message)


class GraphError(FinancialModelError):
    """Error raised for invalid graph structure or operations.

    Covers issues like inconsistencies in the graph (e.g., orphaned nodes),
    problems during graph traversal, or invalid modifications to the graph.

    Examples:
        >>> raise GraphError("Orphaned node detected", nodes=["unconnected_node"])
        >>> raise GraphError("Failed to add edge due to type mismatch")
    """

    def __init__(self, message: str, nodes: Optional[list[str]] = None):
        """Initialize the GraphError.

        Args:
            message: The base error message.
            nodes: Optional list of node IDs involved in the graph error.
        """
        self.nodes = nodes or []

        full_message = (
            f"{message} involving nodes: {', '.join(nodes)}" if nodes else message
        )

        super().__init__(full_message)


class DataValidationError(FinancialModelError):
    """Error raised for data validation failures.

    Typically occurs during data import or preprocessing when data
    does not conform to expected formats, types, or constraints.

    Examples:
        >>> raise DataValidationError(
        ...     "Input data failed validation",
        ...     validation_errors=[
        ...         "Column 'Date' has invalid format",
        ...         "Value '-100' is not allowed for 'Revenue'"
        ...     ]
        ... )
    """

    def __init__(self, message: str, validation_errors: Optional[list[str]] = None):
        """Initialize the DataValidationError.

        Args:
            message: The base error message.
            validation_errors: Optional list of specific validation failures.
        """
        self.validation_errors = validation_errors or []

        if validation_errors:
            full_message = f"{message}: {'; '.join(validation_errors)}"
        else:
            full_message = message

        super().__init__(full_message)


class CircularDependencyError(FinancialModelError):
    """Error raised when a circular dependency is detected in calculations.

    Occurs if the calculation graph contains cycles, meaning a node
    directly or indirectly depends on itself.

    Examples:
        >>> raise CircularDependencyError(cycle=["node_a", "node_b", "node_c", "node_a"])
    """

    def __init__(
        self,
        message: str = "Circular dependency detected",
        cycle: Optional[list[str]] = None,
    ):
        """Initialize the CircularDependencyError.

        Args:
            message: The base error message.
            cycle: Optional list of node IDs forming the detected cycle.
        """
        self.cycle = cycle or []

        if cycle:
            cycle_str = " -> ".join(cycle)
            full_message = f"{message}: {cycle_str}"
        else:
            full_message = message

        super().__init__(full_message)


class PeriodError(FinancialModelError):
    """Error raised for invalid or missing periods.

    Covers issues like requesting data for a non-existent period or
    using invalid period formats.

    Examples:
        >>> raise PeriodError("Invalid period format", period="2023Q5")
        >>> raise PeriodError("Period not found", period="2024-01-01", available_periods=["2023-12-31"])
    """

    def __init__(
        self,
        message: str,
        period: Optional[str] = None,
        available_periods: Optional[list[str]] = None,
    ):
        """Initialize the PeriodError.

        Args:
            message: The base error message.
            period: Optional specific period involved in the error.
            available_periods: Optional list of valid periods.
        """
        self.period = period
        self.available_periods = available_periods or []

        if period and available_periods:
            full_message = f"{message} for period '{period}'. Available periods: {', '.join(available_periods)}"
        elif period:
            full_message = f"{message} for period '{period}'"
        else:
            full_message = message

        super().__init__(full_message)


class StatementError(FinancialModelError):
    """Error raised for issues related to financial statements.

    Used for errors specific to the structure, definition, or
    processing of financial statements (e.g., Balance Sheet, P&L).

    Examples:
        >>> raise StatementError("Balance sheet does not balance", statement_id="BS_2023")
        >>> raise StatementError("Required account missing from P&L", statement_id="PnL_Q1")
    """

    def __init__(self, message: str, statement_id: Optional[str] = None):
        """Initialize the StatementError.

        Args:
            message: The base error message.
            statement_id: Optional ID or name of the statement involved.
        """
        self.statement_id = statement_id

        full_message = (
            f"{message} for statement '{statement_id}'" if statement_id else message
        )

        super().__init__(full_message)


class StrategyError(FinancialModelError):
    """Error raised for issues related to calculation strategies.

    Indicates a problem with the configuration or execution of a
    specific calculation strategy (e.g., Summation, GrowthRate).

    Examples:
        >>> raise StrategyError("Invalid parameter for GrowthRate strategy", strategy_type="GrowthRate", node_id="revenue_forecast")
        >>> raise StrategyError("Strategy not applicable to node type", strategy_type="Summation", node_id="text_description")
    """

    def __init__(
        self,
        message: str,
        strategy_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ):
        """Initialize the StrategyError.

        Args:
            message: The base error message.
            strategy_type: Optional name or type of the strategy involved.
            node_id: Optional ID of the node using the strategy.
        """
        self.strategy_type = strategy_type
        self.node_id = node_id

        context = []
        if strategy_type:
            context.append(f"strategy type '{strategy_type}'")
        if node_id:
            context.append(f"node '{node_id}'")

        full_message = f"{message} for {' in '.join(context)}" if context else message

        super().__init__(full_message)


class TransformationError(FinancialModelError):
    """Error raised during data transformation.

    Occurs during preprocessing steps when a specific transformation
    (e.g., normalization, scaling) fails.

    Examples:
        >>> raise TransformationError("Log transform requires positive values", transformer_type="LogTransformer")
        >>> raise TransformationError(
        ...     "Incompatible data type for scaling",
        ...     transformer_type="MinMaxScaler",
        ...     parameters={"feature_range": (0, 1)}
        ... )
    """

    def __init__(
        self,
        message: str,
        transformer_type: Optional[str] = None,
        parameters: Optional[dict[str, Any]] = None,
    ):
        """Initialize the TransformationError.

        Args:
            message: The base error message.
            transformer_type: Optional name or type of the transformer involved.
            parameters: Optional dictionary of parameters used by the transformer.
        """
        self.transformer_type = transformer_type
        self.parameters = parameters or {}

        if transformer_type:
            full_message = f"{message} in transformer '{transformer_type}'"
            if parameters:
                params_str = ", ".join(f"{k}={v}" for k, v in parameters.items())
                full_message = f"{full_message} with parameters: {params_str}"
        else:
            full_message = message

        super().__init__(full_message)


class MetricError(FinancialModelError):
    """Error raised for issues related to metric definitions or registry.

    Covers issues with loading, validating, or accessing financial metrics,
    whether defined in YAML or Python code.

    Examples:
        >>> raise MetricError("Metric definition not found", metric_name="unknown_ratio")
        >>> raise MetricError(
        ...     "Invalid formula syntax in metric definition",
        ...     metric_name="profitability_index",
        ...     details={"formula": "NPV / Initial Investment)"}  # Missing parenthesis
        ... )
    """

    def __init__(
        self,
        message: str,
        metric_name: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize the MetricError.

        Args:
            message: The base error message.
            metric_name: Optional name of the metric involved in the error.
            details: Optional dictionary containing additional context about the error.
        """
        self.metric_name = metric_name
        self.details = details or {}

        full_message = (
            f"{message} related to metric '{metric_name}'" if metric_name else message
        )

        super().__init__(full_message)


class AdjustmentError(FinancialModelError):
    """Error raised when an invalid adjustment is encountered.

    Used by :class:`fin_statement_model.core.adjustments.manager.AdjustmentManager` when
    ``strict=True`` and a mathematical domain error or overflow is detected while
    applying an adjustment.
    """

    pass
