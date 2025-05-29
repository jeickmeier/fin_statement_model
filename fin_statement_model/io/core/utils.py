"""Utility functions for IO operations."""

from typing import Optional, Union

# Type alias for mapping configurations
MappingConfig = Union[dict[str, str], dict[Optional[str], dict[str, str]]]


def normalize_mapping(
    mapping_config: MappingConfig = None, context_key: Optional[str] = None
) -> dict[str, str]:
    """Turn a scoped MappingConfig into a unified flat dict with a required default mapping under None.

    Args:
        mapping_config: MappingConfig object defining name mappings.
        context_key: Optional key (e.g., sheet name or statement type) to select
            a scoped mapping within a scoped config.

    Returns:
        A flat dict mapping original names to canonical names.

    Raises:
        TypeError: If the provided mapping_config is not of a supported structure.
    """
    if mapping_config is None:
        return {}
    if not isinstance(mapping_config, dict):
        raise TypeError(f"mapping_config must be a dict, got {type(mapping_config).__name__}")
    if None not in mapping_config:
        # Flat mapping
        return mapping_config
    else:
        # Scoped mapping
        default_mapping = mapping_config.get(None, {})
        if context_key and context_key in mapping_config:
            context_mapping = mapping_config[context_key]
            # Merge with context-specific overriding default
            return {**default_mapping, **context_mapping}
        else:
            return default_mapping


__all__ = ["MappingConfig", "normalize_mapping"]
