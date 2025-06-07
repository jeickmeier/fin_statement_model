"""Parameter to configuration path mapping utilities.

This module provides utilities for mapping function/method parameter names
to configuration paths, supporting both explicit mappings and convention-based
automatic mapping.
"""

from typing import Optional, ClassVar
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ParamMapper:
    """Maps parameter names to configuration paths using conventions and explicit mappings."""

    # Base mappings for common parameters that don't follow conventions
    BASE_MAPPINGS: ClassVar[dict[str, str]] = {
        "delimiter": "io.default_csv_delimiter",
        "sheet_name": "io.default_excel_sheet",
        "periods": "forecasting.default_periods",
        "growth_rate": "forecasting.default_growth_rate",
        "method": "forecasting.default_method",
        "scale_factor": "display.scale_factor",
        "scale": "display.scale_factor",
        "retry_count": "api.api_retry_count",
        "max_retries": "api.api_retry_count",
        "timeout": "api.api_timeout",
        "validate_on_read": "io.validate_on_read",
        "auto_clean": "preprocessing.auto_clean_data",
        "auto_create_dirs": "io.auto_create_output_dirs",
        "strict_mode": "validation.strict_mode",
        "hide_zero_rows": "display.hide_zero_rows",
        "number_format": "display.default_number_format",
        "currency_format": "display.default_currency_format",
        "percentage_format": "display.default_percentage_format",
    }

    @classmethod
    def get_config_path(cls, param_name: str) -> Optional[str]:
        """Get configuration path for a parameter name.

        Uses explicit mappings first, then tries convention-based mapping.

        Args:
            param_name: The parameter name to map

        Returns:
            Configuration path string, or None if no mapping found

        Example:
            >>> ParamMapper.get_config_path("delimiter")
            'io.default_csv_delimiter'
            >>> ParamMapper.get_config_path("default_periods")
            'forecasting.default_periods'
        """
        # Check explicit mappings first
        if param_name in cls.BASE_MAPPINGS:
            return cls.BASE_MAPPINGS[param_name]

        # Try convention-based mapping
        return cls._try_convention_mapping(param_name)

    @classmethod
    def _try_convention_mapping(cls, param_name: str) -> Optional[str]:
        """Try to map parameter name using conventions.

        Conventions:
        1. "default_X" -> search for "default_X" in config
        2. "X_timeout" -> "api.X_timeout" or "api.api_timeout"
        3. "X_format" -> "display.X_format"
        4. "auto_X" -> search for "auto_X" in config

        Args:
            param_name: The parameter name

        Returns:
            Configuration path if found, None otherwise
        """
        from .models import Config

        # Convention 1: default_* parameters
        if param_name.startswith("default_"):
            path = cls._find_config_field(Config, param_name)
            if path:
                return path

        # Convention 2: *_timeout parameters -> api section
        if param_name.endswith("_timeout"):
            if param_name == "api_timeout":
                return "api.api_timeout"
            # Try with api prefix
            api_field = f"api_{param_name}"
            if cls._field_exists(Config, ["api", api_field]):
                return f"api.{api_field}"
            elif cls._field_exists(Config, ["api", param_name]):
                return f"api.{param_name}"

        # Convention 3: *_format parameters -> display section
        if param_name.endswith("_format"):
            if cls._field_exists(Config, ["display", param_name]):
                return f"display.{param_name}"
            # Try with default_ prefix
            default_field = f"default_{param_name}"
            if cls._field_exists(Config, ["display", default_field]):
                return f"display.{default_field}"

        # Convention 4: auto_* parameters
        if param_name.startswith("auto_"):
            path = cls._find_config_field(Config, param_name)
            if path:
                return path

        return None

    @classmethod
    def _find_config_field(cls, model: type[BaseModel], field_name: str) -> Optional[str]:
        """Find a field by name anywhere in the config model hierarchy.

        Args:
            model: The Pydantic model to search
            field_name: The field name to find

        Returns:
            Dot-separated path to the field, or None if not found
        """
        return cls._search_model_recursive(model, field_name, [])

    @classmethod
    def _search_model_recursive(
        cls,
        model: type[BaseModel],
        field_name: str,
        path: list[str]
    ) -> Optional[str]:
        """Recursively search for a field in a model hierarchy.

        Args:
            model: Current model to search
            field_name: Field name to find
            path: Current path in the hierarchy

        Returns:
            Dot-separated path if found, None otherwise
        """
        from typing import get_origin, get_args, Union

        for current_field, field_info in model.model_fields.items():
            current_path = [*path, current_field]

            # Check if this is the field we're looking for
            if current_field == field_name:
                return ".".join(current_path)

            # If it's a nested model, recurse
            field_type = field_info.annotation

            # Handle Union types (Optional)
            origin = get_origin(field_type)
            if origin is Union:
                args = get_args(field_type)
                non_none_args = [arg for arg in args if arg is not type(None)]
                if non_none_args:
                    field_type = non_none_args[0]

            if (isinstance(field_type, type) and
                issubclass(field_type, BaseModel)):
                result = cls._search_model_recursive(field_type, field_name, current_path)
                if result:
                    return result

        return None

    @classmethod
    def _field_exists(cls, model: type[BaseModel], path: list[str]) -> bool:
        """Check if a field path exists in the model.

        Args:
            model: The model to check
            path: List of field names representing the path

        Returns:
            True if the path exists, False otherwise
        """
        try:
            from .introspection import _validate_config_path
            _validate_config_path(model, path)
            return True
        except ValueError:
            return False

    @classmethod
    def register_mapping(cls, param_name: str, config_path: str) -> None:
        """Register a custom parameter mapping.

        Args:
            param_name: The parameter name
            config_path: The configuration path

        Example:
            >>> ParamMapper.register_mapping("custom_param", "custom.config.path")
        """
        cls.BASE_MAPPINGS[param_name] = config_path
        logger.debug(f"Registered parameter mapping: {param_name} -> {config_path}")

    @classmethod
    def get_all_mappings(cls) -> dict[str, str]:
        """Get all current parameter mappings.

        Returns:
            Dictionary of parameter name to config path mappings
        """
        return cls.BASE_MAPPINGS.copy()

    @classmethod
    def clear_custom_mappings(cls) -> None:
        """Clear all custom mappings, keeping only the base mappings."""
        # Store the original base mappings
        original_mappings = {
            "delimiter": "io.default_csv_delimiter",
            "sheet_name": "io.default_excel_sheet",
            "periods": "forecasting.default_periods",
            "growth_rate": "forecasting.default_growth_rate",
            "method": "forecasting.default_method",
            "scale_factor": "display.scale_factor",
            "scale": "display.scale_factor",
            "retry_count": "api.api_retry_count",
            "max_retries": "api.api_retry_count",
            "timeout": "api.api_timeout",
            "validate_on_read": "io.validate_on_read",
            "auto_clean": "preprocessing.auto_clean_data",
            "auto_create_dirs": "io.auto_create_output_dirs",
            "strict_mode": "validation.strict_mode",
            "hide_zero_rows": "display.hide_zero_rows",
            "number_format": "display.default_number_format",
            "currency_format": "display.default_currency_format",
            "percentage_format": "display.default_percentage_format",
        }
        cls.BASE_MAPPINGS = original_mappings
        logger.debug("Cleared custom parameter mappings")


def get_class_param_mappings(cls: type) -> dict[str, str]:
    """Get parameter mappings declared at the class level.

    Looks for a _config_mappings attribute on the class.

    Args:
        cls: The class to check

    Returns:
        Dictionary of parameter mappings, empty if none found
    """
    mappings = getattr(cls, "_config_mappings", {})
    return mappings if mappings is not None else {}


def merge_param_mappings(*mapping_dicts: dict[str, str]) -> dict[str, str]:
    """Merge multiple parameter mapping dictionaries.

    Later dictionaries override earlier ones for conflicting keys.

    Args:
        *mapping_dicts: Variable number of mapping dictionaries

    Returns:
        Merged mapping dictionary
    """
    result = {}
    for mapping_dict in mapping_dicts:
        result.update(mapping_dict)
    return result
