"""Statement loading and building functionality.

This module handles validation, building, and registration of statement structures
from in-memory configuration dictionaries.
"""

import logging
from typing import Any, Optional
from pathlib import Path

from fin_statement_model.core.errors import ConfigurationError, StatementError
from fin_statement_model.statements.structure.builder import StatementStructureBuilder
from fin_statement_model.statements.configs.validator import StatementConfig
from fin_statement_model.statements.registry import StatementRegistry
from fin_statement_model.io.validation import UnifiedNodeValidator

logger = logging.getLogger(__name__)

__all__ = ["load_build_register_statements"]


def load_build_register_statements(
    raw_configs: dict[str, dict[str, Any]] | str | Path,
    registry: StatementRegistry,
    builder: Optional[StatementStructureBuilder] = None,
    enable_node_validation: bool = False,
    node_validation_strict: bool = False,
    node_validator: Optional[UnifiedNodeValidator] = None,
) -> list[str]:
    """Load, validate, build, and register statement structures from config dicts.

    Args:
        raw_configs: Mapping of statement IDs to configuration dicts, or a file path or directory path.
        registry: StatementRegistry instance to register loaded statements.
        builder: Optional StatementStructureBuilder instance.
        enable_node_validation: If True, validate node IDs during config and build.
        node_validation_strict: If True, treat validation failures as errors.
        node_validator: Optional pre-configured UnifiedNodeValidator.

    Returns:
        List of statement IDs successfully loaded and registered.

    Raises:
        ConfigurationError: If config validation fails.
        StatementError: If registration fails.
    """
    loaded_statement_ids: list[str] = []
    errors: list[tuple[str, str]] = []

    # NEW: Allow `raw_configs` to be a file path or directory path for backward compatibility
    #       Convert such inputs into the expected {statement_id: config_dict} mapping.
    if isinstance(raw_configs, (str, Path)):
        def _parse_cfg_file(path: Path) -> dict[str, Any] | None:
            """Parse a YAML or JSON configuration file into a dict mapping."""
            try:
                if path.suffix.lower() == ".json":
                    import json

                    data = json.loads(path.read_text(encoding="utf-8"))
                else:
                    import yaml

                    data = yaml.safe_load(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    logger.warning(
                        "Skipping config '%s' – root element is not a mapping.", path
                    )
                    return None
                return data
            except Exception as exc:  # pragma: no cover
                logger.exception("Failed to parse statement config '%s': %s", path, exc)
                return None

        path_obj = Path(raw_configs)
        if not path_obj.exists():
            raise FileNotFoundError(f"Statement config path '{path_obj}' does not exist.")

        configs_dict: dict[str, dict[str, Any]] = {}
        if path_obj.is_dir():
            for file in path_obj.iterdir():
                if file.is_file() and file.suffix.lower() in {".yaml", ".yml", ".json"}:
                    parsed = _parse_cfg_file(file)
                    if parsed:
                        stmt_id = str(parsed.get("id", file.stem))
                        configs_dict[stmt_id] = parsed
        else:
            parsed = _parse_cfg_file(path_obj)
            if parsed:
                stmt_id = str(parsed.get("id", path_obj.stem))
                configs_dict[stmt_id] = parsed

        raw_configs = configs_dict  # type: ignore[assignment]

    if builder is None:
        builder = StatementStructureBuilder(
            enable_node_validation=enable_node_validation,
            node_validation_strict=node_validation_strict,
            node_validator=node_validator,
        )

    if not raw_configs:
        logger.warning("No statement configurations provided.")
        return []

    for stmt_id, raw_data in raw_configs.items():
        try:
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
                    errors=validation_errors,
                )
            statement = builder.build(config)
            registry.register(statement)
            loaded_statement_ids.append(statement.id)
        except (ConfigurationError, StatementError, ValueError) as e:
            logger.exception(f"Failed to process/register statement '{stmt_id}'.")
            errors.append((stmt_id, str(e)))
        except Exception as e:
            logger.exception(f"Unexpected error processing statement '{stmt_id}'.")
            errors.append((stmt_id, f"Unexpected error: {e!s}"))

    if errors:
        error_details = "; ".join(f"{sid}: {msg}" for sid, msg in errors)
        logger.warning(
            f"Encountered {len(errors)} errors during statement loading/building: {error_details}"
        )

    return loaded_statement_ids
