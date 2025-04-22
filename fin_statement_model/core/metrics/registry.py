"""Registry for loading and accessing metric definitions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Union, ClassVar, Callable, TYPE_CHECKING

# Use a try-except block for the YAML import
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from fin_statement_model.core.errors import ConfigurationError

if TYPE_CHECKING:
    from fin_statement_model.core.nodes.metric_node import MetricCalculation

logger = logging.getLogger(__name__)

# Registry mapping metric type strings to MetricCalculation classes
_registry: ClassVar[dict[str, type[MetricCalculation]]] = {}


class MetricRegistry:
    """Manages loading and accessing metric definitions from YAML files.

    Responsibilities:
    - Discovering and loading YAML metric definitions from specified directories.
    - Validating the structure of loaded metric definitions.
    - Providing access to metric definitions by ID.
    """

    _REQUIRED_FIELDS: ClassVar[list[str]] = ["inputs", "formula", "description", "name"]

    def __init__(self):
        """Initialize the registry with an empty store."""
        self._metrics: dict[str, dict[str, Any]] = {}
        logger.info("MetricRegistry initialized.")

    def load_metrics_from_directory(self, directory_path: Union[str, Path]) -> int:
        """Load all *.yaml metric definitions from a given directory.

        Args:
            directory_path: The path to the directory containing metric YAML files.

        Returns:
            int: The number of metrics successfully loaded.

        Raises:
            ImportError: If PyYAML is not installed.
            FileNotFoundError: If the directory_path does not exist.
            ConfigurationError: If a YAML file is invalid or missing required fields.
        """
        if not HAS_YAML:
            logger.error("PyYAML is required to load metrics from YAML files. Please install it.")
            raise ImportError("PyYAML is required to load metrics from YAML files.")

        dir_path = Path(directory_path)
        if not dir_path.is_dir():
            logger.error(f"Metric directory not found: {dir_path}")
            raise FileNotFoundError(f"Metric directory not found: {dir_path}")

        logger.info(f"Loading metrics from directory: {dir_path}")
        loaded_count = 0
        for filepath in dir_path.glob("*.yaml"):
            metric_id = filepath.stem  # Use filename without extension as ID (e.g., "gross_profit")
            logger.debug(f"Attempting to load metric '{metric_id}' from {filepath}")
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if not isinstance(data, dict):
                    raise TypeError("YAML content must be a dictionary.")

                # Validate required fields
                missing_fields = [field for field in self._REQUIRED_FIELDS if field not in data]
                if missing_fields:
                    raise ValueError(f"Missing required fields: {missing_fields}")

                # Basic type validation for key fields
                if not isinstance(data["name"], str):
                    raise TypeError("'name' field must be a string.")
                if not isinstance(data["description"], str):
                    raise TypeError("'description' field must be a string.")
                if not isinstance(data["inputs"], list):
                    raise TypeError("'inputs' field must be a list.")
                if not isinstance(data["formula"], str):
                    raise TypeError("'formula' field must be a string.")

                # Store the validated metric definition
                if metric_id in self._metrics:
                    logger.warning(
                        f"Overwriting existing metric definition for '{metric_id}' from {filepath}"
                    )
                self._metrics[metric_id] = data
                logger.debug(f"Successfully loaded and validated metric '{metric_id}'")
                loaded_count += 1

            except yaml.YAMLError as e:
                logger.exception(f"Error parsing YAML file {filepath}")
                raise ConfigurationError(
                    f"Invalid YAML syntax in {filepath}", config_path=str(filepath)
                ) from e
            except (TypeError, ValueError) as e:
                logger.exception(f"Invalid metric definition structure in {filepath}")
                raise ConfigurationError(
                    f"Invalid metric structure in {filepath}: {e}",
                    config_path=str(filepath),
                ) from e
            except Exception as e:
                logger.error(
                    f"Unexpected error loading metric from {filepath}",
                    exc_info=True,
                )
                raise ConfigurationError(
                    f"Failed to load metric from {filepath} due to: {e}",
                    config_path=str(filepath),
                ) from e

        logger.info(f"Successfully loaded {loaded_count} metrics from {dir_path}.")
        return loaded_count

    def get(self, metric_id: str) -> dict[str, Any]:
        """Retrieve a loaded metric definition by its ID.

        Args:
            metric_id: The identifier of the metric (usually the filename stem).

        Returns:
            Dict[str, Any]: The dictionary containing the metric definition.

        Raises:
            KeyError: If the metric_id is not found in the registry.
        """
        try:
            return self._metrics[metric_id]
        except KeyError:
            logger.warning(f"Metric ID '{metric_id}' not found in registry.")
            raise KeyError(f"Metric ID '{metric_id}' not found. Available: {self.list_metrics()}")

    def list_metrics(self) -> list[str]:
        """Get a sorted list of all loaded metric IDs.

        Returns:
            List[str]: Sorted list of available metric IDs.
        """
        return sorted(self._metrics.keys())

    def __len__(self) -> int:
        """Return the number of loaded metrics."""
        return len(self._metrics)

    def __contains__(self, metric_id: str) -> bool:
        """Check if a metric ID exists in the registry."""
        return metric_id in self._metrics

    @classmethod
    def register(cls, name: str) -> Callable[[type[MetricCalculation]], type[MetricCalculation]]:
        """Class method decorator to register a new metric calculation type.

        Args:
            name: The name of the metric calculation type.

        Returns:
            Callable[[Type["MetricCalculation"]], Type["MetricCalculation"]]: The decorator function.
        """

        def decorator(metric_class: type[MetricCalculation]) -> type[MetricCalculation]:
            _registry[name] = metric_class
            return metric_class

        return decorator
