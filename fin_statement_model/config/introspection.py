"""Configuration introspection utilities.

This module provides utilities for dynamically generating configuration mappings
by introspecting Pydantic models, eliminating the need for hardcoded mappings.
"""

from typing import Any, get_origin, get_args, Union
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


def generate_env_mappings(
    model: type[BaseModel],
    prefix: str = "FSM",
    path: list[str] | None = None
) -> dict[str, list[str]]:
    """Generate environment variable mappings from a Pydantic model.

    Recursively walks through a Pydantic model and generates environment variable
    names that map to configuration paths. This eliminates the need for hardcoded
    environment variable mappings.

    Args:
        model: The Pydantic model to introspect
        prefix: The environment variable prefix (default: "FSM")
        path: Current path in the model hierarchy (used for recursion)

    Returns:
        Dictionary mapping environment variable names to config path lists

    Example:
        >>> from fin_statement_model.config.models import Config
        >>> mappings = generate_env_mappings(Config)
        >>> mappings["FSM_LOGGING_LEVEL"]
        ['logging', 'level']
        >>> mappings["FSM_IO_DEFAULT_EXCEL_SHEET"]
        ['io', 'default_excel_sheet']
    """
    if path is None:
        path = []

    mappings = {}

    for field_name, field_info in model.model_fields.items():
        current_path = [*path, field_name]
        field_type = field_info.annotation

        # Handle Union types (including Optional which is Union[T, None])
        origin = get_origin(field_type)
        if origin is Union:
            args = get_args(field_type)
            # For Optional[T], get the non-None type
            non_none_args = [arg for arg in args if arg is not type(None)]
            if non_none_args:
                field_type = non_none_args[0]

        # If it's another BaseModel, recurse
        if (isinstance(field_type, type) and
            issubclass(field_type, BaseModel)):
            sub_mappings = generate_env_mappings(field_type, prefix, current_path)
            mappings.update(sub_mappings)
        else:
            # Generate env var name: FSM_SECTION_FIELD_NAME
            env_name = prefix + "_" + "_".join(p.upper() for p in current_path)
            mappings[env_name] = current_path

    logger.debug(f"Generated {len(mappings)} environment variable mappings")
    return mappings


def validate_env_mappings(
    model: type[BaseModel],
    mappings: dict[str, list[str]]
) -> list[str]:
    """Validate that environment variable mappings are correct.

    Checks that all paths in the mappings actually exist in the model structure.

    Args:
        model: The Pydantic model to validate against
        mappings: Dictionary of env var name to config path mappings

    Returns:
        List of validation errors (empty if all mappings are valid)
    """
    errors = []

    for env_var, config_path in mappings.items():
        try:
            _validate_config_path(model, config_path)
        except ValueError as e:
            errors.append(f"Invalid mapping {env_var} -> {'.'.join(config_path)}: {e}")

    return errors


def _validate_config_path(model: type[BaseModel], path: list[str]) -> None:
    """Validate that a config path exists in the model.

    Args:
        model: The Pydantic model to check
        path: List of field names representing the path

    Raises:
        ValueError: If the path doesn't exist in the model
    """
    current_model = model

    for i, field_name in enumerate(path):
        if field_name not in current_model.model_fields:
            raise ValueError(f"Field '{field_name}' not found in {current_model.__name__}")

        field_info = current_model.model_fields[field_name]
        field_type = field_info.annotation

        # Handle Union types
        origin = get_origin(field_type)
        if origin is Union:
            args = get_args(field_type)
            non_none_args = [arg for arg in args if arg is not type(None)]
            if non_none_args:
                field_type = non_none_args[0]

        # If this is not the last field in the path, it should be a BaseModel
        if i < len(path) - 1:
            if not (isinstance(field_type, type) and issubclass(field_type, BaseModel)):
                raise ValueError(
                    f"Field '{field_name}' is not a nested model but path continues"
                )
            current_model = field_type


def get_field_type_info(model: type[BaseModel], path: list[str]) -> dict[str, Any]:
    """Get type information for a field at the given path.

    Args:
        model: The Pydantic model
        path: List of field names representing the path

    Returns:
        Dictionary with type information including:
        - type: The field type
        - is_optional: Whether the field is optional
        - default: The default value if any

    Raises:
        ValueError: If the path doesn't exist in the model
    """
    current_model = model

    for field_name in path[:-1]:
        if field_name not in current_model.model_fields:
            raise ValueError(f"Field '{field_name}' not found in {current_model.__name__}")

        field_info = current_model.model_fields[field_name]
        field_type = field_info.annotation

        # Handle Union types
        origin = get_origin(field_type)
        if origin is Union:
            args = get_args(field_type)
            non_none_args = [arg for arg in args if arg is not type(None)]
            if non_none_args:
                field_type = non_none_args[0]

        if not (isinstance(field_type, type) and issubclass(field_type, BaseModel)):
            raise ValueError(f"Field '{field_name}' is not a nested model")
        current_model = field_type

    # Get the final field
    final_field = path[-1]
    if final_field not in current_model.model_fields:
        raise ValueError(f"Field '{final_field}' not found in {current_model.__name__}")

    field_info = current_model.model_fields[final_field]
    field_type = field_info.annotation

    # Check if optional
    is_optional = False
    origin = get_origin(field_type)
    if origin is Union:
        args = get_args(field_type)
        if type(None) in args:
            is_optional = True
            non_none_args = [arg for arg in args if arg is not type(None)]
            if non_none_args:
                field_type = non_none_args[0]

    return {
        "type": field_type,
        "is_optional": is_optional,
        "default": field_info.default if hasattr(field_info, "default") else None,
        "field_info": field_info
    }
