"""Custom exceptions for forecasting operations.

This module defines the exception hierarchy for the forecasting sub-module. All forecasting-related
errors inherit from ForecastingError, which itself extends FinancialModelError. These exceptions
cover invalid methods, configuration errors, node errors, and result validation issues.

Example:
    >>> from fin_statement_model.forecasting.errors import ForecastMethodError
    >>> raise ForecastMethodError("Unknown method", method="foo", supported_methods=["simple"])
    Traceback (most recent call last):
        ...
    fin_statement_model.forecasting.errors.ForecastMethodError: Unknown method: 'foo'. Supported methods: simple
"""

from typing import Any

from fin_statement_model.core.errors import FinancialModelError

__all__ = [
    "ForecastConfigurationError",
    "ForecastMethodError",
    "ForecastNodeError",
    "ForecastResultError",
    "ForecastingError",
]

# Maximum items to preview in error lists
MAX_PREVIEW_ITEMS: int = 10


class ForecastingError(FinancialModelError):
    """Base exception for all forecasting-related errors.

    All custom forecasting exceptions inherit from this class.
    """


class ForecastMethodError(ForecastingError):
    """Exception raised for invalid or unsupported forecast methods.

    This includes unknown method names, invalid method parameters,
    or methods incompatible with the data type.

    Example:
        >>> from fin_statement_model.forecasting.errors import ForecastMethodError
        >>> raise ForecastMethodError("Unknown method", method="foo", supported_methods=["simple"])
        Traceback (most recent call last):
            ...
        fin_statement_model.forecasting.errors.ForecastMethodError: Unknown method: 'foo'. Supported methods: simple
    """

    def __init__(
        self,
        message: str,
        method: str | None = None,
        supported_methods: list[str] | None = None,
        node_id: str | None = None,
    ):
        """Initialize a ForecastMethodError.

        Args:
            message: The primary error message.
            method: Optional name of the invalid method.
            supported_methods: Optional list of supported methods.
            node_id: Optional ID of the node being forecasted.
        """
        self.method = method
        self.supported_methods = supported_methods or []
        self.node_id = node_id

        full_message = message
        if method:
            full_message = f"{message}: '{method}'"
        if node_id:
            full_message = f"{full_message} for node '{node_id}'"
        if supported_methods:
            full_message = f"{full_message}. Supported methods: {', '.join(supported_methods)}"

        super().__init__(full_message)


class ForecastConfigurationError(ForecastingError):
    """Exception raised for invalid forecast configuration.

    This includes missing required parameters, invalid parameter values,
    or incompatible configuration combinations.

    Example:
        >>> from fin_statement_model.forecasting.errors import ForecastConfigurationError
        >>> raise ForecastConfigurationError("Missing config", missing_params=["growth_rate"])
        Traceback (most recent call last):
            ...
        fin_statement_model.forecasting.errors.ForecastConfigurationError: Missing config - Missing parameters: growth_rate
    """

    def __init__(
        self,
        message: str,
        config: dict[str, Any] | None = None,
        missing_params: list[str] | None = None,
        invalid_params: dict[str, str] | None = None,
    ):
        """Initialize a ForecastConfigurationError.

        Args:
            message: The primary error message.
            config: Optional configuration dictionary that caused the error.
            missing_params: Optional list of missing required parameters.
            invalid_params: Optional dict of parameter names to error descriptions.
        """
        self.config = config
        self.missing_params = missing_params or []
        self.invalid_params = invalid_params or {}

        details = []
        if missing_params:
            details.append(f"Missing parameters: {', '.join(missing_params)}")
        if invalid_params:
            param_errors = [f"{k}: {v}" for k, v in invalid_params.items()]
            details.append(f"Invalid parameters: {'; '.join(param_errors)}")

        full_message = message
        if details:
            full_message = f"{message} - {' | '.join(details)}"

        super().__init__(full_message)


class ForecastNodeError(ForecastingError):
    """Exception raised for node-related forecast errors.

    This includes nodes not found in the graph, nodes without historical data,
    or nodes that cannot be forecasted.

    Example:
        >>> from fin_statement_model.forecasting.errors import ForecastNodeError
        >>> raise ForecastNodeError("Node not found", node_id="revenue", available_nodes=["revenue", "costs"])
        Traceback (most recent call last):
            ...
        fin_statement_model.forecasting.errors.ForecastNodeError: Node not found for node 'revenue'. Available nodes: revenue, costs
    """

    def __init__(
        self,
        message: str,
        node_id: str | None,
        available_nodes: list[str] | None = None,
        reason: str | None = None,
    ):
        """Initialize a ForecastNodeError.

        Args:
            message: The primary error message.
            node_id: The ID of the problematic node.
            available_nodes: Optional list of available node IDs.
            reason: Optional specific reason why the node cannot be forecasted.
        """
        self.node_id = node_id
        self.available_nodes = available_nodes or []
        self.reason = reason

        full_message = f"{message} for node '{node_id}'"
        if reason:
            full_message = f"{full_message}: {reason}"
        if available_nodes and len(available_nodes) < MAX_PREVIEW_ITEMS:  # Only show if list is small
            full_message = f"{full_message}. Available nodes: {', '.join(available_nodes)}"

        super().__init__(full_message)


class ForecastResultError(ForecastingError):
    """Exception raised for forecast result access or manipulation errors.

    This includes accessing results for non-existent periods, invalid result
    formats, or result validation failures.

    Example:
        >>> from fin_statement_model.forecasting.errors import ForecastResultError
        >>> raise ForecastResultError("Period not found", period="2024", available_periods=["2023", "2024"])
        Traceback (most recent call last):
            ...
        fin_statement_model.forecasting.errors.ForecastResultError: Period not found for period '2024'. Available periods: 2023, 2024
    """

    def __init__(
        self,
        message: str,
        period: str | None = None,
        available_periods: list[str] | None = None,
        node_id: str | None = None,
    ):
        """Initialize a ForecastResultError.

        Args:
            message: The primary error message.
            period: Optional period that caused the error.
            available_periods: Optional list of available periods.
            node_id: Optional ID of the node whose results are being accessed.
        """
        self.period = period
        self.available_periods = available_periods or []
        self.node_id = node_id

        context = []
        if node_id:
            context.append(f"node '{node_id}'")
        if period:
            context.append(f"period '{period}'")

        full_message = message
        if context:
            full_message = f"{message} for {' and '.join(context)}"
        if available_periods and len(available_periods) < MAX_PREVIEW_ITEMS:
            full_message = f"{full_message}. Available periods: {', '.join(available_periods)}"

        super().__init__(full_message)
