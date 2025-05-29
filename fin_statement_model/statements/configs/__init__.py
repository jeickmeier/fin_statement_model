"""Configuration handling for financial statements.

This package provides:
- Pydantic models for configuration validation
- Configuration file loading utilities
- StatementConfig class for managing configurations
"""

from .loader import load_config_file, load_config_directory
from .models import (
    AdjustmentFilterSpec,
    BaseItemModel,
    CalculatedItemModel,
    CalculationSpec,
    LineItemModel,
    MetricItemModel,
    SectionModel,
    StatementModel,
    SubtotalModel,
)
from .validator import StatementConfig

__all__ = [
    # Models
    "AdjustmentFilterSpec",
    "BaseItemModel",
    "CalculatedItemModel",
    "CalculationSpec",
    "LineItemModel",
    "MetricItemModel",
    "SectionModel",
    # Validator
    "StatementConfig",
    "StatementModel",
    "SubtotalModel",
    "load_config_directory",
    # Loader functions
    "load_config_file",
]
