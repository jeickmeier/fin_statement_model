"""
Custom exceptions for the Financial Statement Model.

This module defines exception classes for specific error cases in the
Financial Statement Model, allowing for more precise error handling
and better error messages.
"""

from typing import Optional, List, Dict, Any


class FinancialModelError(Exception):
    """Base exception class for all Financial Statement Model errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ConfigurationError(FinancialModelError):
    """Exception raised for errors in configuration files or objects."""

    def __init__(
        self,
        message: str,
        config_path: Optional[str] = None,
        errors: Optional[List[str]] = None,
    ):
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
    """Exception raised for errors during calculation operations."""

    def __init__(
        self,
        message: str,
        node_id: Optional[str] = None,
        period: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.node_id = node_id
        self.period = period
        self.details = details or {}

        context = []
        if node_id:
            context.append(f"node '{node_id}'")
        if period:
            context.append(f"period '{period}'")

        if context:
            full_message = f"{message} for {' and '.join(context)}"
        else:
            full_message = message

        super().__init__(full_message)


class NodeError(FinancialModelError):
    """Exception raised for errors related to graph nodes."""

    def __init__(self, message: str, node_id: Optional[str] = None):
        self.node_id = node_id

        if node_id:
            full_message = f"{message} for node '{node_id}'"
        else:
            full_message = message

        super().__init__(full_message)


class GraphError(FinancialModelError):
    """Exception raised for errors in the graph structure or operations."""

    def __init__(self, message: str, nodes: Optional[List[str]] = None):
        self.nodes = nodes or []

        if nodes:
            full_message = f"{message} involving nodes: {', '.join(nodes)}"
        else:
            full_message = message

        super().__init__(full_message)


class DataValidationError(FinancialModelError):
    """Exception raised for data validation errors."""

    def __init__(self, message: str, validation_errors: Optional[List[str]] = None):
        self.validation_errors = validation_errors or []

        if validation_errors:
            full_message = f"{message}: {'; '.join(validation_errors)}"
        else:
            full_message = message

        super().__init__(full_message)


class ImportError(FinancialModelError):
    """Exception raised for errors during data import operations."""

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        adapter: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
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
            full_message = f"{full_message}: {str(original_error)}"

        super().__init__(full_message)


class ExportError(FinancialModelError):
    """Exception raised for errors during data export operations."""

    def __init__(
        self,
        message: str,
        target: Optional[str] = None,
        format_type: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
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
            full_message = f"{full_message}: {str(original_error)}"

        super().__init__(full_message)


class CircularDependencyError(FinancialModelError):
    """Exception raised when a circular dependency is detected in calculations."""

    def __init__(
        self,
        message: str = "Circular dependency detected",
        cycle: Optional[List[str]] = None,
    ):
        self.cycle = cycle or []

        if cycle:
            cycle_str = " -> ".join(cycle)
            full_message = f"{message}: {cycle_str}"
        else:
            full_message = message

        super().__init__(full_message)


class PeriodError(FinancialModelError):
    """Exception raised for errors related to periods."""

    def __init__(
        self,
        message: str,
        period: Optional[str] = None,
        available_periods: Optional[List[str]] = None,
    ):
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
    """Exception raised for errors related to financial statements."""

    def __init__(self, message: str, statement_id: Optional[str] = None):
        self.statement_id = statement_id

        if statement_id:
            full_message = f"{message} for statement '{statement_id}'"
        else:
            full_message = message

        super().__init__(full_message)


class StrategyError(FinancialModelError):
    """Exception raised for errors related to calculation strategies."""

    def __init__(
        self,
        message: str,
        strategy_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ):
        self.strategy_type = strategy_type
        self.node_id = node_id

        context = []
        if strategy_type:
            context.append(f"strategy type '{strategy_type}'")
        if node_id:
            context.append(f"node '{node_id}'")

        if context:
            full_message = f"{message} for {' in '.join(context)}"
        else:
            full_message = message

        super().__init__(full_message)


class TransformationError(FinancialModelError):
    """Exception raised for errors during data transformation."""

    def __init__(
        self,
        message: str,
        transformer_type: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
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
