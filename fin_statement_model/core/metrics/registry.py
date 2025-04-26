"""Manage loading and accessing metric definitions from YAML files.

This module provides a registry to discover, validate, and retrieve
metric definitions from YAML files and associate them with calculation classes.
"""


import logging
from pathlib import Path
from typing import Any, ClassVar, Union, Callable

# Use a try-except block for the YAML import
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from pydantic import ValidationError

from fin_statement_model.core.errors import ConfigurationError
from fin_statement_model.core.metrics.models import MetricDefinition
from fin_statement_model.core.nodes.metric_node import MetricCalculation

logger = logging.getLogger(__name__)

# Registry mapping metric type strings to MetricCalculation classes
_registry: dict[str, type[MetricCalculation]] = {}


class MetricRegistry:
    """Manage loading and accessing metric definitions from YAML files.

    This includes discovering YAML definitions, validating their structure,
    and providing retrieval methods by metric ID.
    """

    _REQUIRED_FIELDS: ClassVar[list[str]] = ["inputs", "formula", "description", "name"]

    def __init__(self):
        """Initialize the MetricRegistry with an empty metrics store.

        Examples:
            >>> registry = MetricRegistry()
            >>> len(registry)
            0
        """
        self._metrics: dict[str, MetricDefinition] = {}
        logger.info("MetricRegistry initialized.")

    def load_metrics_from_directory(self, directory_path: Union[str, Path]) -> int:
        """Load all metric definitions from a directory.

        This method searches for '*.yaml' files, validates their content,
        and stores them in the registry.

        Args:
            directory_path: Path to the directory containing metric YAML files.

        Returns:
            The number of metrics successfully loaded.

        Raises:
            ImportError: If PyYAML is not installed.
            FileNotFoundError: If the directory_path does not exist.
            ConfigurationError: If a YAML file is invalid or missing required fields.

        Examples:
            >>> registry = MetricRegistry()
            >>> count = registry.load_metrics_from_directory("./metrics")
            >>> print(f"Loaded {count} metrics.")
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

                try:
                    model = MetricDefinition.parse_obj(data)
                except ValidationError as e:
                    raise ConfigurationError(
                        f"Invalid metric '{filepath.name}': {e}",
                        config_path=str(filepath),
                    ) from e

                if metric_id in self._metrics:
                    logger.warning(
                        f"Overwriting existing metric definition for '{metric_id}' from {filepath}"
                    )
                self._metrics[metric_id] = model
                logger.debug(f"Successfully loaded and validated metric '{metric_id}'")
                loaded_count += 1

            except yaml.YAMLError as e:
                logger.exception(f"Error parsing YAML file {filepath}")
                raise ConfigurationError(
                    f"Invalid YAML syntax in {filepath}", config_path=str(filepath)
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

    def get(self, metric_id: str) -> MetricDefinition:
        """Retrieve a loaded metric definition by its ID.

        Args:
            metric_id: Identifier of the metric (filename stem).

        Returns:
            A MetricDefinition object containing the metric definition.

        Raises:
            KeyError: If the metric_id is not found in the registry.

        Examples:
            >>> definition = registry.get("gross_profit")
            >>> print(definition["formula"])
        """
        try:
            return self._metrics[metric_id]
        except KeyError:
            logger.warning(f"Metric ID '{metric_id}' not found in registry.")
            raise KeyError(f"Metric ID '{metric_id}' not found. Available: {self.list_metrics()}")

    def list_metrics(self) -> list[str]:
        """Get a sorted list of all loaded metric IDs.

        Returns:
            A sorted list of available metric IDs.

        Examples:
            >>> registry.list_metrics()
            ['current_ratio', 'debt_equity_ratio']
        """
        return sorted(self._metrics.keys())

    def __len__(self) -> int:
        """Return the number of loaded metrics.

        Returns:
            The count of metrics loaded into the registry.

        Examples:
            >>> len(registry)
            5
        """
        return len(self._metrics)

    def __contains__(self, metric_id: str) -> bool:
        """Check if a metric ID exists in the registry.

        Args:
            metric_id: The metric identifier to check.

        Returns:
            True if the metric is present, False otherwise.

        Examples:
            >>> 'current_ratio' in registry
        """
        return metric_id in self._metrics

    @classmethod
    def register(cls, name: str) -> Callable[[type[MetricCalculation]], type[MetricCalculation]]:
        """Register a new metric calculation class under a given name.

        Args:
            name: The identifier for the metric calculation type.

        Returns:
            A decorator that registers the decorated class under `name`.

        Examples:
            >>> @MetricRegistry.register("custom_metric")
            ... class CustomMetric(MetricCalculation):
            ...     pass
        """

        def decorator(metric_class: type[MetricCalculation]) -> type[MetricCalculation]:
            _registry[name] = metric_class
            return metric_class

        return decorator
