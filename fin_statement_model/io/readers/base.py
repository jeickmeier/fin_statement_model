"""Shared utilities for IO readers."""

from typing import Optional, Union

MappingConfig = Union[
    dict[str, str],
    dict[Optional[str], dict[str, str]]
]

def normalize_mapping(
    mapping_config: MappingConfig = None,
    context_key: Optional[str] = None
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
        raise TypeError("mapping_config must include a default mapping under None")
    default_map = mapping_config[None]

    if not isinstance(default_map, dict):
        raise TypeError(
            "Default mapping (None key) must be a dict[str, str] if present"
        )
    result: dict[str, str] = dict(default_map)
    if context_key and context_key in mapping_config:
        scoped = mapping_config[context_key]
        if not isinstance(scoped, dict):
            raise TypeError(
                f"Scoped mapping for key '{context_key}' must be a dict[str, str]"
            )
        result.update(scoped)
    return result
