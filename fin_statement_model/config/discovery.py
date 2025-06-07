"""Configuration discovery and documentation utilities.

This module provides tools to help developers understand and work with
the configuration system, including listing available paths and generating
documentation.
"""

from typing import Any, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


def list_all_config_paths(model: Optional[type[BaseModel]] = None) -> list[str]:
    """List all available configuration paths.

    Args:
        model: The model to introspect (defaults to Config)

    Returns:
        List of dot-separated configuration paths

    Example:
        >>> paths = list_all_config_paths()
        >>> 'logging.level' in paths
        True
        >>> 'io.default_excel_sheet' in paths
        True
    """
    if model is None:
        from .models import Config
        model = Config

    paths = []

    def _walk_model(m: type[BaseModel], prefix: str = ""):
        """Recursively walk through model fields."""
        from typing import get_origin, get_args, Union

        for field_name, field_info in m.model_fields.items():
            current_path = f"{prefix}.{field_name}" if prefix else field_name
            field_type = field_info.annotation

            # Handle Union types (Optional)
            origin = get_origin(field_type)
            if origin is Union:
                args = get_args(field_type)
                non_none_args = [arg for arg in args if arg is not type(None)]
                if non_none_args:
                    field_type = non_none_args[0]

            # If it's another BaseModel, recurse
            if (isinstance(field_type, type) and
                issubclass(field_type, BaseModel)):
                _walk_model(field_type, current_path)
            else:
                paths.append(current_path)

    _walk_model(model)
    return sorted(paths)


def generate_env_var_documentation(model: Optional[type[BaseModel]] = None) -> str:
    """Generate documentation for all available environment variables.

    Args:
        model: The model to document (defaults to Config)

    Returns:
        Markdown-formatted documentation string

    Example:
        >>> doc = generate_env_var_documentation()
        >>> 'FSM_LOGGING_LEVEL' in doc
        True
    """
    if model is None:
        from .models import Config
        model = Config

    from .introspection import generate_env_mappings

    mappings = generate_env_mappings(model)

    doc = "# Environment Variables\n\n"
    doc += "The following environment variables can be used to configure fin_statement_model:\n\n"

    # Group by section for better organization
    sections = {}
    for env_var, config_path in sorted(mappings.items()):
        section = config_path[0] if config_path else "global"
        if section not in sections:
            sections[section] = []
        sections[section].append((env_var, config_path))

    for section, vars_list in sorted(sections.items()):
        doc += f"## {section.title()} Configuration\n\n"
        for env_var, config_path in vars_list:
            config_str = ".".join(config_path)
            doc += f"- `{env_var}`: Maps to `{config_str}`\n"
        doc += "\n"

    return doc


def generate_param_mapping_documentation() -> str:
    """Generate documentation for parameter mappings.

    Returns:
        Markdown-formatted documentation string
    """
    from .param_mapping import ParamMapper

    mappings = ParamMapper.get_all_mappings()

    doc = "# Parameter Mappings\n\n"
    doc += "The following parameter names are automatically mapped to configuration values:\n\n"

    for param_name, config_path in sorted(mappings.items()):
        doc += f"- `{param_name}`: Maps to `{config_path}`\n"

    doc += "\n## Convention-Based Mappings\n\n"
    doc += "Parameters following these patterns are automatically mapped:\n\n"
    doc += "- `default_*`: Searches for matching field in configuration\n"
    doc += "- `*_timeout`: Maps to API timeout configurations\n"
    doc += "- `*_format`: Maps to display format configurations\n"
    doc += "- `auto_*`: Searches for matching auto-configuration fields\n"

    return doc


def get_config_field_info(config_path: str, model: Optional[type[BaseModel]] = None) -> dict[str, Any]:
    """Get detailed information about a configuration field.

    Args:
        config_path: Dot-separated path to the configuration field
        model: The model to inspect (defaults to Config)

    Returns:
        Dictionary with field information including type, default, description

    Raises:
        ValueError: If the config path doesn't exist

    Example:
        >>> info = get_config_field_info("logging.level")
        >>> info["type"].__name__
        'str'
    """
    if model is None:
        from .models import Config
        model = Config

    from .introspection import get_field_type_info

    path_parts = config_path.split(".")

    try:
        type_info = get_field_type_info(model, path_parts)

        # Extract description from field info if available
        description = None
        if hasattr(type_info["field_info"], "description"):
            description = type_info["field_info"].description

        return {
            "path": config_path,
            "type": type_info["type"],
            "is_optional": type_info["is_optional"],
            "default": type_info["default"],
            "description": description,
        }
    except ValueError as e:
        raise ValueError(f"Configuration path '{config_path}' not found: {e}")


def find_config_paths_by_type(target_type: type, model: type[BaseModel] | None = None) -> list[str]:
    """Find all configuration paths that have a specific type.

    Args:
        target_type: The type to search for (e.g., bool, int, str)
        model: The model to search (defaults to Config)

    Returns:
        List of configuration paths with the specified type

    Example:
        >>> bool_configs = find_config_paths_by_type(bool)
        >>> 'logging.detailed' in bool_configs
        True
    """
    if model is None:
        from .models import Config
        model = Config

    matching_paths = []
    all_paths = list_all_config_paths(model)

    for path in all_paths:
        try:
            field_info = get_config_field_info(path, model)
            if field_info["type"] == target_type:
                matching_paths.append(path)
        except ValueError:
            # Skip invalid paths
            continue

    return sorted(matching_paths)


def validate_config_completeness(model: type[BaseModel] | None = None) -> dict[str, list[str]]:
    """Validate that all configuration fields have proper environment variable mappings.

    Args:
        model: The model to validate (defaults to Config)

    Returns:
        Dictionary with validation results:
        - "missing_env_vars": Config paths without env var mappings
        - "missing_param_mappings": Common parameters without mappings

    Example:
        >>> results = validate_config_completeness()
        >>> len(results["missing_env_vars"])
        0
    """
    if model is None:
        from .models import Config
        model = Config

    from .introspection import generate_env_mappings
    from .param_mapping import ParamMapper

    # Get all config paths and env mappings
    all_paths = set(list_all_config_paths(model))
    env_mappings = generate_env_mappings(model)
    mapped_paths = set(".".join(path) for path in env_mappings.values())

    # Find config paths without env var mappings
    missing_env_vars = sorted(all_paths - mapped_paths)

    # Check for common parameter patterns that might need mappings
    param_mappings = ParamMapper.get_all_mappings()
    common_patterns = ["default_", "auto_", "_timeout", "_format", "_count", "_size"]

    missing_param_mappings = []
    for path in all_paths:
        field_name = path.split(".")[-1]
        # Check if this looks like a parameter that should have a mapping
        if any(pattern in field_name for pattern in common_patterns):
            # Check if there's already a mapping for this or similar parameter
            potential_param_names = [
                field_name,
                field_name.replace("default_", ""),
                field_name.replace("auto_", ""),
            ]
            if not any(param in param_mappings for param in potential_param_names):
                missing_param_mappings.append(path)

    return {
        "missing_env_vars": missing_env_vars,
        "missing_param_mappings": sorted(missing_param_mappings),
    }


def generate_config_summary(model: type[BaseModel] | None = None) -> str:
    """Generate a comprehensive summary of the configuration system.

    Args:
        model: The model to summarize (defaults to Config)

    Returns:
        Markdown-formatted summary
    """
    if model is None:
        from .models import Config
        model = Config

    from .introspection import generate_env_mappings
    from .param_mapping import ParamMapper

    all_paths = list_all_config_paths(model)
    env_mappings = generate_env_mappings(model)
    param_mappings = ParamMapper.get_all_mappings()
    validation_results = validate_config_completeness(model)

    summary = "# Configuration System Summary\n\n"
    summary += f"**Model**: {model.__name__}\n"
    summary += f"**Total Configuration Fields**: {len(all_paths)}\n"
    summary += f"**Environment Variables**: {len(env_mappings)}\n"
    summary += f"**Parameter Mappings**: {len(param_mappings)}\n\n"

    # Type breakdown
    type_counts = {}
    for path in all_paths:
        try:
            field_info = get_config_field_info(path, model)
            type_name = field_info["type"].__name__
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        except ValueError:
            continue

    summary += "## Field Types\n\n"
    for type_name, count in sorted(type_counts.items()):
        summary += f"- {type_name}: {count} fields\n"

    # Validation results
    summary += "\n## Validation Results\n\n"
    if validation_results["missing_env_vars"]:
        summary += f"**Missing Environment Variables**: {len(validation_results['missing_env_vars'])}\n"
        for path in validation_results["missing_env_vars"][:5]:  # Show first 5
            summary += f"- {path}\n"
        if len(validation_results["missing_env_vars"]) > 5:
            summary += f"- ... and {len(validation_results['missing_env_vars']) - 5} more\n"
    else:
        summary += "✅ All configuration fields have environment variable mappings\n"

    if validation_results["missing_param_mappings"]:
        summary += f"\n**Potential Missing Parameter Mappings**: {len(validation_results['missing_param_mappings'])}\n"
        for path in validation_results["missing_param_mappings"][:5]:  # Show first 5
            summary += f"- {path}\n"
        if len(validation_results["missing_param_mappings"]) > 5:
            summary += f"- ... and {len(validation_results['missing_param_mappings']) - 5} more\n"
    else:
        summary += "✅ All common parameter patterns have mappings\n"

    return summary
