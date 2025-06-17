"""Validation utilities for the forecasting module.

This module provides functions and classes to validate forecast inputs,
configurations, and results. It ensures that forecast operations are
performed with correct parameters, valid periods, and supported methods.

Features:
    - Input validation for forecast periods and node configs
    - Configuration validation for forecast methods and statistical parameters
    - Result validation for forecast output
    - Error reporting for invalid or missing data

Example:
    >>> from fin_statement_model.forecasting.validators import ForecastValidator
    >>> ForecastValidator.validate_forecast_inputs(["2022"], ["2023"], {"revenue": {"method": "simple", "config": 0.05}})
    # No exception means validation passed
"""

import logging
from typing import Any, Optional

from fin_statement_model.core.nodes import Node
from .types import ForecastMethodType, ForecastConfig
from fin_statement_model.forecasting.errors import (
    ForecastConfigurationError,
    ForecastMethodError,
    ForecastNodeError,
    ForecastResultError,
)

logger = logging.getLogger(__name__)


class ForecastValidator:
    """Validator for forecast inputs, configurations, and results.

    Provides static methods to check the validity of forecast periods,
    node configurations, and forecast results. Raises descriptive errors
    for invalid input or output.
    """

    @staticmethod
    def validate_forecast_inputs(
        historical_periods: list[str],
        forecast_periods: list[str],
        node_configs: Optional[dict[str, dict[str, Any]]] = None,
    ) -> None:
        """Validate forecast input periods and node configurations.

        Args:
            historical_periods: List of historical periods to use as base.
            forecast_periods: List of periods to forecast.
            node_configs: Optional mapping of node names to forecast configs.

        Raises:
            ForecastNodeError: If no historical or forecast periods are provided.
            ForecastConfigurationError: If node_configs is not a dict.

        Example:
            >>> ForecastValidator.validate_forecast_inputs(["2022"], ["2023"])
            # No exception means validation passed
        """
        if not historical_periods:
            raise ForecastNodeError(
                "No historical periods provided for forecasting",
                node_id=None,
            )
        if not forecast_periods:
            raise ForecastNodeError(
                "No forecast periods provided",
                node_id=None,
            )
        if node_configs is not None and not isinstance(node_configs, dict):
            raise ForecastConfigurationError(
                "node_configs must be a dictionary",
                config=node_configs,
            )

    @staticmethod
    def validate_node_config(node_name: str, config: dict[str, Any]) -> None:
        """Validate configuration for a single node.

        Args:
            node_name: Name of the node being configured.
            config: Configuration dictionary for the node.

        Raises:
            ValueError: If configuration is logically invalid.
            TypeError: If configuration is of wrong type.
        """
        if not isinstance(config, dict):
            raise TypeError(
                f"Configuration for node '{node_name}' must be a dict, got {type(config)}"
            )

        # Validate method
        if "method" not in config:
            raise ValueError(
                f"Configuration for node '{node_name}' missing required 'method' key"
            )

        method = config["method"]
        valid_methods: list[ForecastMethodType] = [
            "simple",
            "curve",
            "statistical",
            "average",
            "historical_growth",
        ]
        if method not in valid_methods:
            raise ValueError(
                f"Invalid forecast method '{method}' for node '{node_name}'. "
                f"Valid methods: {valid_methods}"
            )

        # Validate config exists (can be None for some methods)
        if "config" not in config:
            raise ValueError(
                f"Configuration for node '{node_name}' missing required 'config' key"
            )

    @staticmethod
    def validate_node_for_forecast(node: Node, method: str) -> None:
        """Validate that a node is forecastable with the given method.

        Args:
            node: The node object to check.
            method: The forecast method to use.

        Raises:
            ForecastNodeError: If the node is not forecastable.

        Example:
            >>> class DummyNode:
            ...     values = {"2022": 100.0}
            >>> ForecastValidator.validate_node_for_forecast(DummyNode(), "simple")
            # No exception means validation passed
        """
        if not hasattr(node, "values") or not isinstance(node.values, dict):
            raise ForecastNodeError(
                f"Node {node.name} is not forecastable (missing 'values' dict)",
                node_id=node.name,
            )

    @staticmethod
    def validate_forecast_config(config: dict[str, Any]) -> ForecastConfig:
        """Validate and parse a forecast configuration dictionary.

        Args:
            config: Dictionary with 'method' and method-specific 'config'.

        Returns:
            ForecastConfig: Validated and parsed configuration object.

        Raises:
            ForecastMethodError: If method is missing or invalid.
            ForecastConfigurationError: If config is missing or invalid.

        Example:
            >>> ForecastValidator.validate_forecast_config({"method": "simple", "config": 0.05})
            ForecastConfig(method='simple', config=0.05)
        """
        if not isinstance(config, dict):
            raise ForecastConfigurationError(
                "Forecast config must be a dictionary",
                config=config,
            )
        if "method" not in config:
            raise ForecastMethodError(
                "Forecast config missing 'method' key",
                method=None,
            )
        return ForecastConfig(**config)

    @staticmethod
    def validate_base_period(
        base_period: str, available_periods: list[str], node_name: str
    ) -> None:
        """Validate that a base period is valid for forecasting.

        Args:
            base_period: The proposed base period.
            available_periods: List of available periods.
            node_name: Name of the node (for error messages).

        Raises:
            ValueError: If base period is invalid.
        """
        if not base_period:
            raise ValueError(f"No base period determined for node '{node_name}'")

        if base_period not in available_periods:
            raise ValueError(
                f"Base period '{base_period}' for node '{node_name}' not found in available periods"
            )

    @staticmethod
    def validate_forecast_result(
        results: dict[str, float],
        forecast_periods: list[str],
        node_name: Optional[str] = None,
    ) -> None:
        """Validate forecast result values for completeness and type.

        Args:
            results: Dictionary mapping periods to forecast values.
            forecast_periods: List of periods that should be present in results.
            node_name: Optional name of the node for error context.

        Raises:
            ForecastResultError: If any forecast period is missing or value is not a float.

        Example:
            >>> ForecastValidator.validate_forecast_result({"2023": 1050.0}, ["2023"])
            # No exception means validation passed
        """
        missing = [p for p in forecast_periods if p not in results]
        if missing:
            raise ForecastResultError(
                f"Missing forecast results for periods: {', '.join(missing)}",
                period=missing[0],
                available_periods=list(results.keys()),
                node_id=node_name,
            )
        for period, value in results.items():
            if not isinstance(value, (int, float)):
                raise ForecastResultError(
                    f"Forecast value for period {period} is not a number",
                    period=period,
                    node_id=node_name,
                )
