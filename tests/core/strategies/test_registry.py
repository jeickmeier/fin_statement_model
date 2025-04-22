"""Tests for the registry module in the Financial Statement Model.

This module contains tests specifically for the Registry class functionality.
"""

import pytest
from unittest.mock import patch

from fin_statement_model.core.strategies.registry import Registry
from fin_statement_model.core.strategies.strategy import (
    Strategy,
    AdditionStrategy,
    SubtractionStrategy,
)


def test_registry_initialization():
    """Test that the registry is properly initialized."""
    Registry._strategies.clear()  # Clear existing strategies
    assert isinstance(Registry._strategies, dict)
    assert len(Registry._strategies) == 0


def test_registry_register_multiple_strategies():
    """Test registering multiple strategies with the registry."""
    Registry._strategies.clear()  # Clear existing strategies
    Registry.register(AdditionStrategy)
    Registry.register(SubtractionStrategy)

    assert len(Registry._strategies) == 2
    assert "AdditionStrategy" in Registry._strategies
    assert "SubtractionStrategy" in Registry._strategies


def test_registry_register_duplicate():
    """Test registering a duplicate strategy (should overwrite)."""
    Registry._strategies.clear()  # Clear existing strategies

    # Register first time
    Registry.register(AdditionStrategy)
    assert Registry._strategies["AdditionStrategy"] == AdditionStrategy

    # Register a different strategy with the same name
    class AdditionStrategy2(Strategy):
        def calculate(self, inputs, period):
            return 0.0

    # Force the class name to match
    AdditionStrategy2.__name__ = "AdditionStrategy"
    Registry.register(AdditionStrategy2)
    assert Registry._strategies["AdditionStrategy"] == AdditionStrategy2


def test_registry_get_all_strategies():
    """Test getting all registered strategies."""
    Registry._strategies.clear()  # Clear existing strategies
    Registry.register(AdditionStrategy)
    Registry.register(SubtractionStrategy)

    strategies = Registry.list()
    assert isinstance(strategies, dict)
    assert len(strategies) == 2
    assert strategies["AdditionStrategy"] == AdditionStrategy
    assert strategies["SubtractionStrategy"] == SubtractionStrategy


def test_registry_get_strategy_with_invalid_name():
    """Test getting a strategy with an invalid name type."""
    Registry._strategies.clear()  # Clear existing strategies
    with pytest.raises(KeyError):
        Registry.get(123)  # Invalid name type


def test_registry_clear():
    """Test clearing the registry."""
    Registry._strategies.clear()  # Clear existing strategies
    Registry.register(AdditionStrategy)
    Registry.register(SubtractionStrategy)

    Registry._strategies.clear()
    assert len(Registry._strategies) == 0
    assert Registry.list() == {}


def test_registry_with_mocked_logging():
    """Test registry operations with mocked logging."""
    Registry._strategies.clear()  # Clear existing strategies

    with patch("fin_statement_model.core.strategies.registry.logger") as mock_logger:
        # Test registration logging
        Registry.register(AdditionStrategy)
        mock_logger.debug.assert_called_with("Registered strategy: AdditionStrategy")

        # Test error logging for non-existent strategy
        with pytest.raises(KeyError):
            Registry.get("NonExistentStrategy")
        mock_logger.error.assert_called_with(
            "Attempted to access unregistered strategy: NonExistentStrategy"
        )
