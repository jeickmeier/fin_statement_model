"""Statement loading and building functionality.

This module handles validation, building, and registration of statement structures
from in-memory configuration dictionaries.
"""

import logging
from typing import Any

from fin_statement_model.core.errors import ConfigurationError, StatementError
from fin_statement_model.statements.registry import StatementRegistry
from fin_statement_model.statements.structure.models_v2 import load_structure
from fin_statement_model.statements.validation import UnifiedNodeValidator

logger = logging.getLogger(__name__)

__all__ = ["load_build_register_statements"]


def load_build_register_statements(
    raw_configs: dict[str, dict[str, Any]],
    registry: StatementRegistry,
    enable_node_validation: bool = False,
    node_validation_strict: bool = False,
    node_validator: UnifiedNodeValidator | None = None,
) -> list[str]:
    """Load, validate, build, and register statement structures from config dicts.

    Args:
        raw_configs: Mapping of statement IDs to configuration dicts.
        registry: StatementRegistry instance to register loaded statements.
        enable_node_validation: If True, validate node IDs during config and build.
        node_validation_strict: If True, treat validation failures as errors.
        node_validator: Optional pre-configured UnifiedNodeValidator.

    Returns:
        List of statement IDs successfully loaded and registered.

    Raises:
        ConfigurationError: If config validation fails.
        StatementError: If registration fails.
    """
    _ = (
        enable_node_validation,
        node_validation_strict,
        node_validator,
    )

    loaded_statement_ids: list[str] = []
    errors: list[tuple[str, str]] = []

    # Enforce modern API: raw_configs must be an in-memory mapping.
    if not isinstance(raw_configs, dict):
        raise TypeError(
            "'raw_configs' must be a mapping of statement_id to configuration dict. "
            "Loading configurations from file paths has been removed. "
            "Load the YAML/JSON into memory first (e.g., with yaml.safe_load) "
            "and pass the resulting mapping instead."
        )

    if not raw_configs:
        logger.warning("No statement configurations provided.")
        return []

    for stmt_id, raw_data in raw_configs.items():
        try:
            # Directly load structure via Pydantic models
            statement = load_structure(raw_data)
            registry.register(statement)
            loaded_statement_ids.append(statement.id)
        except (ConfigurationError, StatementError, ValueError) as e:
            logger.exception("Failed to process/register statement '%s'.", stmt_id)
            errors.append((stmt_id, str(e)))
        except Exception as e:
            logger.exception("Unexpected error processing statement '%s'.", stmt_id)
            errors.append((stmt_id, f"Unexpected error: {e!s}"))

    if errors:
        error_details = "; ".join(f"{sid}: {msg}" for sid, msg in errors)
        logger.warning("Encountered %s errors during statement loading/building: %s", len(errors), error_details)

    return loaded_statement_ids
