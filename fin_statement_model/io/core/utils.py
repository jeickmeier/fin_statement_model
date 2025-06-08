"""Utility functions for IO operations."""

from typing import Optional, Union, cast

# Type alias for mapping configurations
MappingConfig = Union[dict[str, str], dict[Optional[str], dict[str, str]]]


def normalize_mapping(
    mapping_config: Optional[MappingConfig] = None, context_key: Optional[str] = None
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
        raise TypeError(
            f"mapping_config must be a dict, got {type(mapping_config).__name__}"
        )
    if None not in mapping_config:
        # Flat mapping: keys are source names
        return cast(dict[str, str], mapping_config)
    # Scoped mapping: mapping_config keys include Optional[str]
    scoped = cast(dict[Optional[str], dict[str, str]], mapping_config)
    # Default scope under None
    default_mapping = scoped[None]
    # Overlay context-specific mappings if provided
    if context_key and context_key in scoped:
        context_mapping = scoped[context_key]
        merged: dict[str, str] = {**default_mapping, **context_mapping}
        return merged
    return default_mapping


__all__ = ["MappingConfig", "normalize_mapping"]
