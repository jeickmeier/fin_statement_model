"""Input validation and error checking for forecasting operations.

This module provides validation utilities to ensure forecast inputs
are valid before processing.
"""

import logging
from typing import Any, Optional

from fin_statement_model.core.nodes import Node
from .types import ForecastMethodType, ForecastConfig

logger = logging.getLogger(__name__)


class ForecastValidator:
    """Validates inputs for forecasting operations.

    This class provides methods to validate various aspects of forecast
    inputs including periods, node configurations, and method parameters.
    """

    @staticmethod
    def validate_forecast_inputs(
        historical_periods: list[str],
        forecast_periods: list[str],
        node_configs: Optional[dict[str, dict[str, Any]]] = None,
    ) -> None:
        """Validate basic forecast inputs.

        Args:
            historical_periods: List of historical periods.
            forecast_periods: List of periods to forecast.
            node_configs: Optional node configuration mapping.

        Raises:
            ValueError: If inputs are logically invalid.
            TypeError: If inputs are of wrong type.
        """
        # Validate historical periods
        if not historical_periods:
            raise ValueError("No historical periods provided for forecasting")

        if not isinstance(historical_periods, list):
            raise TypeError(
                f"Historical periods must be a list, got {type(historical_periods)}"
            )

        # Validate forecast periods
        if not forecast_periods:
            raise ValueError("No forecast periods provided")

        if not isinstance(forecast_periods, list):
            raise TypeError(
                f"Forecast periods must be a list, got {type(forecast_periods)}"
            )

        # Check for overlapping periods
        historical_set = set(historical_periods)
        forecast_set = set(forecast_periods)
        overlap = historical_set & forecast_set
        if overlap:
            logger.warning(
                f"Forecast periods overlap with historical periods: {overlap}. "
                f"This may overwrite historical data."
            )

        # Validate node configs if provided
        if node_configs is not None:
            if not isinstance(node_configs, dict):
                raise TypeError(
                    f"Node configs must be a dict, got {type(node_configs)}"
                )

            for node_name, config in node_configs.items():
                ForecastValidator.validate_node_config(node_name, config)

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
        """Validate that a node can be forecasted with the given method.

        Args:
            node: The node to validate.
            method: The forecast method to use.

        Raises:
            ValueError: If node cannot be forecasted.
        """
        # Check if node has values dictionary
        if not hasattr(node, "values") or not isinstance(node.values, dict):
            raise ValueError(
                f"Node '{node.name}' cannot be forecasted: missing or invalid "
                f"'values' attribute. Only nodes with values dictionaries can "
                f"be forecasted."
            )

        # Check if node has calculate method for certain forecast types
        if method in ["average", "historical_growth"] and (
            not hasattr(node, "calculate") or not callable(node.calculate)
        ):
            raise ValueError(
                f"Node '{node.name}' cannot use '{method}' forecast method: "
                f"missing calculate() method"
            )

    @staticmethod
    def validate_forecast_config(config: dict[str, Any]) -> ForecastConfig:
        """Validate and convert a forecast configuration dictionary.

        Args:
            config: Raw configuration dictionary.

        Returns:
            Validated ForecastConfig instance.

        Raises:
            ValueError: If configuration is logically invalid.
            TypeError: If configuration is of wrong type.
        """
        if not isinstance(config, dict):
            raise TypeError(f"Forecast config must be a dict, got {type(config)}")

        if "method" not in config:
            raise ValueError("Forecast config missing required 'method' key")

        if "config" not in config:
            raise ValueError("Forecast config missing required 'config' key")

        # Create and validate using dataclass
        return ForecastConfig(method=config["method"], config=config["config"])

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
        result: dict[str, float], expected_periods: list[str], node_name: str
    ) -> None:
        """Validate forecast results.

        Args:
            result: Dictionary of period -> value mappings.
            expected_periods: List of expected forecast periods.
            node_name: Name of the node (for error messages).

        Raises:
            ValueError: If results are logically invalid or incomplete.
            TypeError: If results are of wrong type.
        """
        if not isinstance(result, dict):
            raise TypeError(
                f"Forecast result for node '{node_name}' must be a dict, got {type(result)}"
            )

        # Check all expected periods are present
        missing_periods = set(expected_periods) - set(result.keys())
        if missing_periods:
            raise ValueError(
                f"Forecast result for node '{node_name}' missing periods: {missing_periods}"
            )

        # Validate all values are numeric
        for period, value in result.items():
            if not isinstance(value, int | float):
                raise TypeError(
                    f"Forecast value for node '{node_name}' period '{period}' "
                    f"must be numeric, got {type(value)}"
                )
