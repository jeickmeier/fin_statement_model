"""Custom exceptions for the Financial Statement Model.

This module defines exception classes for specific error cases in the
Financial Statement Model, allowing for more precise error handling
and better error messages.
"""

from typing import Optional, Any


class FinancialModelError(Exception):
    """Base exception class for all Financial Statement Model errors.

    All custom exceptions raised within the library should inherit from this class.

    Args:
        message: A human-readable description of the error.
    """

    def __init__(self, message: str):
        """Initializes the FinancialModelError."""
        self.message = message
        super().__init__(self.message)


class ConfigurationError(FinancialModelError):
    """Exception raised for errors in configuration files or objects.

    This typically occurs when parsing or validating configuration data,
    such as YAML files defining metrics or statement structures.

    Args:
        message: The base error message.
        config_path: Optional path to the configuration file where the error occurred.
        errors: Optional list of specific validation errors found.

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
        errors: Optional[list[str]] = None,
    ):
        """Initializes the ConfigurationError."""
        self.config_path = config_path
        self.errors = errors or []

        if config_path and errors:
            full_message = f"{message} in {config_path}: {'; '.join(errors)}"
        elif config_path:
            full_message = f"{message} in {config_path}"
        elif errors:
            full_message = f"{message}: {'; '.join(errors)}"
        else:
            full_message = message

        super().__init__(full_message)


class CalculationError(FinancialModelError):
    """Exception raised for errors during calculation operations.

    This indicates a problem while computing the value of a node, often due
    to issues with the calculation logic, input data, or strategy used.

    Args:
        message: The base error message.
        node_id: Optional ID of the node where the calculation failed.
        period: Optional period for which the calculation failed.
        details: Optional dictionary containing additional context about the error.

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
        """Initializes the CalculationError."""
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
    """Exception raised for errors related to graph nodes.

    This covers issues like trying to access a non-existent node,
    invalid node configurations, or type mismatches related to nodes.

    Args:
        message: The base error message.
        node_id: Optional ID of the node related to the error.

    Examples:
        >>> raise NodeError("Node not found", node_id="non_existent_node")
        >>> raise NodeError("Invalid node type for operation", node_id="revenue")
    """

    def __init__(self, message: str, node_id: Optional[str] = None):
        """Initializes the NodeError."""
        self.node_id = node_id

        full_message = f"{message} for node '{node_id}'" if node_id else message

        super().__init__(full_message)


class MissingInputError(FinancialModelError):
    """Exception raised when a required input for a calculation is missing.

    This occurs when a calculation node needs data from another node for a
    specific period, but that data is unavailable.

    Args:
        message: The base error message.
        node_id: Optional ID of the node requiring the input.
        input_name: Optional name or ID of the missing input node.
        period: Optional period for which the input was missing.

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
        """Initializes the MissingInputError."""
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
    """Exception raised for errors in the graph structure or operations.

    This covers issues like inconsistencies in the graph (e.g., orphaned nodes),
    problems during graph traversal, or invalid modifications to the graph.

    Args:
        message: The base error message.
        nodes: Optional list of node IDs involved in the graph error.

    Examples:
        >>> raise GraphError("Orphaned node detected", nodes=["unconnected_node"])
        >>> raise GraphError("Failed to add edge due to type mismatch")
    """

    def __init__(self, message: str, nodes: Optional[list[str]] = None):
        """Initializes the GraphError."""
        self.nodes = nodes or []

        full_message = f"{message} involving nodes: {', '.join(nodes)}" if nodes else message

        super().__init__(full_message)


class DataValidationError(FinancialModelError):
    """Exception raised for data validation errors.

    This typically occurs during data import or preprocessing when data
    does not conform to expected formats, types, or constraints.

    Args:
        message: The base error message.
        validation_errors: Optional list of specific validation failures.

    Examples:
        >>> raise DataValidationError(
        ...     "Input data failed validation",
        ...     validation_errors=["Column 'Date' has invalid format", "Value '-100' is not allowed for 'Revenue'"]
        ... )
    """

    def __init__(self, message: str, validation_errors: Optional[list[str]] = None):
        """Initializes the DataValidationError."""
        self.validation_errors = validation_errors or []

        if validation_errors:
            full_message = f"{message}: {'; '.join(validation_errors)}"
        else:
            full_message = message

        super().__init__(full_message)


class ImportError(FinancialModelError):
    """Exception raised for errors during data import operations.

    This signals a problem while reading data from an external source,
    such as a file or an API.

    Args:
        message: The base error message.
        source: Optional identifier for the data source (e.g., file path, URL).
        adapter: Optional name of the adapter or reader used for importing.
        original_error: Optional underlying exception that caused the import failure.

    Examples:
        >>> raise ImportError("File not found", source="data.csv", adapter="csv_reader")
        >>> try:
        ...     # some_api_call()
        ...     pass
        ... except requests.exceptions.RequestException as e:
        ...     raise ImportError("API request failed", source="api.example.com/data", original_error=e)
    """

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        adapter: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initializes the ImportError."""
        self.source = source
        self.adapter = adapter
        self.original_error = original_error

        context = []
        if source:
            context.append(f"source '{source}'")
        if adapter:
            context.append(f"adapter '{adapter}'")

        if context:
            if adapter:
                full_message = f"{message} using {' '.join(context)}"
            else:
                full_message = f"{message} from {' '.join(context)}"
        else:
            full_message = message

        if original_error:
            full_message = f"{full_message}: {original_error!s}"

        super().__init__(full_message)


class ExportError(FinancialModelError):
    """Exception raised for errors during data export operations.

    This signals a problem while writing data to an external target,
    such as a file or database.

    Args:
        message: The base error message.
        target: Optional identifier for the export destination (e.g., file path).
        format_type: Optional name of the format being exported to (e.g., 'json', 'xlsx').
        original_error: Optional underlying exception that caused the export failure.

    Examples:
        >>> raise ExportError("Permission denied", target="/path/to/output.xlsx", format_type="excel")
        >>> try:
        ...     # write_to_database()
        ...     pass
        ... except DatabaseError as e:
        ...     raise ExportError("Database write failed", target="db://...", original_error=e)

    """

    def __init__(
        self,
        message: str,
        target: Optional[str] = None,
        format_type: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initializes the ExportError."""
        self.target = target
        self.format_type = format_type
        self.original_error = original_error

        context = []
        if target:
            context.append(f"target '{target}'")
        if format_type:
            context.append(f"format '{format_type}'")

        if context:
            if format_type:
                full_message = f"{message} in {' '.join(context)}"
            else:
                full_message = f"{message} to {' '.join(context)}"
        else:
            full_message = message

        if original_error:
            full_message = f"{full_message}: {original_error!s}"

        super().__init__(full_message)


class CircularDependencyError(FinancialModelError):
    """Exception raised when a circular dependency is detected in calculations.

    This occurs if the calculation graph contains cycles, meaning a node
    directly or indirectly depends on itself.

    Args:
        message: The base error message. Defaults to "Circular dependency detected".
        cycle: Optional list of node IDs forming the detected cycle.

    Examples:
        >>> raise CircularDependencyError(cycle=["node_a", "node_b", "node_c", "node_a"])
    """

    def __init__(
        self,
        message: str = "Circular dependency detected",
        cycle: Optional[list[str]] = None,
    ):
        """Initializes the CircularDependencyError."""
        self.cycle = cycle or []

        if cycle:
            cycle_str = " -> ".join(cycle)
            full_message = f"{message}: {cycle_str}"
        else:
            full_message = message

        super().__init__(full_message)


class PeriodError(FinancialModelError):
    """Exception raised for errors related to periods.

    This covers issues like requesting data for a non-existent period or
    using invalid period formats.

    Args:
        message: The base error message.
        period: Optional specific period involved in the error.
        available_periods: Optional list of valid periods.

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
        """Initializes the PeriodError."""
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
    """Exception raised for errors related to financial statements.

    This is used for errors specific to the structure, definition, or
    processing of financial statements (e.g., Balance Sheet, P&L).

    Args:
        message: The base error message.
        statement_id: Optional ID or name of the statement involved.

    Examples:
        >>> raise StatementError("Balance sheet does not balance", statement_id="BS_2023")
        >>> raise StatementError("Required account missing from P&L", statement_id="PnL_Q1")
    """

    def __init__(self, message: str, statement_id: Optional[str] = None):
        """Initializes the StatementError."""
        self.statement_id = statement_id

        full_message = f"{message} for statement '{statement_id}'" if statement_id else message

        super().__init__(full_message)


class StrategyError(FinancialModelError):
    """Exception raised for errors related to calculation strategies.

    This indicates a problem with the configuration or execution of a
    specific calculation strategy (e.g., Summation, GrowthRate).

    Args:
        message: The base error message.
        strategy_type: Optional name or type of the strategy involved.
        node_id: Optional ID of the node using the strategy.

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
        """Initializes the StrategyError."""
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
    """Exception raised for errors during data transformation.

    This occurs during preprocessing steps when a specific transformation
    (e.g., normalization, scaling) fails.

    Args:
        message: The base error message.
        transformer_type: Optional name or type of the transformer involved.
        parameters: Optional dictionary of parameters used by the transformer.

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
        """Initializes the TransformationError."""
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
    """Exception raised for errors related to metric definitions or registry.

    This covers issues with loading, validating, or accessing financial metrics,
    whether defined in YAML or Python code.

    Args:
        message: The base error message.
        metric_name: Optional name of the metric involved in the error.
        details: Optional dictionary containing additional context about the error.

    Examples:
        >>> raise MetricError("Metric definition not found", metric_name="unknown_ratio")
        >>> raise MetricError(
        ...     "Invalid formula syntax in metric definition",
        ...     metric_name="profitability_index",
        ...     details={"formula": "NPV / Initial Investment)"} # Missing parenthesis
        ... )
    """

    def __init__(
        self,
        message: str,
        metric_name: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initializes the MetricError."""
        self.metric_name = metric_name
        self.details = details or {}

        full_message = f"{message} related to metric '{metric_name}'" if metric_name else message

        super().__init__(full_message)
