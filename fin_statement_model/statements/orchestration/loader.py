"""Statement loading and building functionality.

This module handles the loading of statement configurations from files or directories,
validates them, builds statement structures, and registers them with the registry.
"""

import logging
from pathlib import Path
from typing import Optional

from fin_statement_model.core.errors import ConfigurationError, StatementError
from fin_statement_model.io import (
    read_statement_config_from_path,
    read_statement_configs_from_directory,
)
from fin_statement_model.io.exceptions import ReadError

from fin_statement_model.statements.structure.builder import StatementStructureBuilder
from fin_statement_model.statements.configs.validator import StatementConfig
from fin_statement_model.statements.registry import StatementRegistry

# Import UnifiedNodeValidator for optional node validation
from fin_statement_model.io.validation import UnifiedNodeValidator

logger = logging.getLogger(__name__)

__all__ = ["load_build_register_statements"]


def load_build_register_statements(
    config_path_or_dir: str,
    registry: StatementRegistry,
    builder: Optional[StatementStructureBuilder] = None,
    enable_node_validation: bool = False,
    node_validation_strict: bool = False,
    node_validator: Optional[UnifiedNodeValidator] = None,
) -> list[str]:
    """Load, validate, build, and register statement structures from configs.

    This function orchestrates the first part of the statement processing pipeline.
    It reads configurations, validates them using StatementConfig, builds the
    structure using StatementStructureBuilder, and registers them with the
    provided StatementRegistry.

    Args:
        config_path_or_dir: Path to a single statement config file (e.g.,
            'income_statement.yaml') or a directory containing multiple
            config files.
        registry: The StatementRegistry instance to register loaded statements.
        builder: Optional StatementStructureBuilder instance. If None, creates
            a default builder with node validation settings.
        enable_node_validation: If True, validates node IDs during config and build.
        node_validation_strict: If True, treats node validation failures as errors.
        node_validator: Optional pre-configured UnifiedNodeValidator instance.

    Returns:
        A list of statement IDs that were successfully loaded and registered.

    Raises:
        ConfigurationError: If reading or validation of any configuration fails.
        FileNotFoundError: If the `config_path_or_dir` does not exist.
        StatementError: If registration fails (e.g., duplicate ID).
    """
    loaded_statement_ids = []
    errors = []

    # Create builder if not provided
    if builder is None:
        builder = StatementStructureBuilder(
            enable_node_validation=enable_node_validation,
            node_validation_strict=node_validation_strict,
            node_validator=node_validator,
        )

    try:
        if Path(config_path_or_dir).is_dir():
            raw_configs = read_statement_configs_from_directory(config_path_or_dir)
        elif Path(config_path_or_dir).is_file():
            stmt_id = Path(config_path_or_dir).stem
            raw_config = read_statement_config_from_path(config_path_or_dir)
            raw_configs = {stmt_id: raw_config}
        else:
            raise FileNotFoundError(
                f"Config path is not a valid file or directory: {config_path_or_dir}"
            )

    except (ReadError, FileNotFoundError) as e:
        logger.exception(f"Failed to read configuration from {config_path_or_dir}:")
        raise ConfigurationError(
            message=f"Failed to read config: {e}", config_path=config_path_or_dir
        ) from e

    if not raw_configs:
        logger.warning(f"No statement configurations found at {config_path_or_dir}")
        return []

    for stmt_id, raw_data in raw_configs.items():
        try:
            # Create config with node validation if enabled
            config = StatementConfig(
                config_data=raw_data,
                enable_node_validation=enable_node_validation,
                node_validation_strict=node_validation_strict,
                node_validator=node_validator,
            )

            validation_errors = config.validate_config()
            if validation_errors:
                raise ConfigurationError(
                    f"Invalid configuration for statement '{stmt_id}'",
                    config_path=f"{config_path_or_dir}/{stmt_id}.ext",  # Placeholder path
                    errors=validation_errors,
                )

            statement = builder.build(config)
            registry.register(statement)  # Raises StatementError on conflict
            loaded_statement_ids.append(statement.id)

        except (ConfigurationError, StatementError, ValueError) as e:
            logger.exception(f"Failed to process/register statement '{stmt_id}':")
            errors.append((stmt_id, str(e)))
        except Exception as e:
            logger.exception(
                f"Unexpected error processing statement '{stmt_id}' from {config_path_or_dir}"
            )
            errors.append((stmt_id, f"Unexpected error: {e!s}"))

    # Handle errors - maybe raise an aggregate error if any occurred?
    if errors:
        # For now, just log a warning, processing continues with successfully
        # loaded statements
        error_details = "; ".join([f"{sid}: {msg}" for sid, msg in errors])
        logger.warning(
            f"Encountered {len(errors)} errors during statement loading/building "
            f"from {config_path_or_dir}: {error_details}"
        )
        # Consider raising an aggregated error if needed for stricter handling

    return loaded_statement_ids
