"""Provide a registry for loading and accessing metric definitions from YAML files.

This module defines:
- MetricRegistry: Load, validate, and retrieve metric definitions.
- metric_registry: Singleton instance of MetricRegistry.
"""

import logging
from pathlib import Path
from typing import Any, ClassVar, Union

from pydantic import ValidationError

from fin_statement_model.core.metrics.models import MetricDefinition
from fin_statement_model.core.utils.yaml_loader import (
    HAS_YAML,
    iter_yaml_files,
)

logger = logging.getLogger(__name__)


class MetricRegistry:
    """Provide methods to load, discover, and retrieve metric definitions from YAML files.

    Example:
        >>> from fin_statement_model.core.metrics.registry import MetricRegistry
        >>> registry = MetricRegistry()
        >>> registry.list_metrics()
        []
    """

    _REQUIRED_FIELDS: ClassVar[list[str]] = ["inputs", "formula", "description", "name"]

    def __init__(self) -> None:
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
        and stores them in the registry. Each YAML file can contain either:
        - A single metric definition (a YAML dictionary at the root)
        - A list of metric definitions (a YAML list of dictionaries at the root)

        Args:
            directory_path: Path to the directory containing metric YAML files.

        Returns:
            The number of metrics successfully loaded.

        Raises:
            ImportError: If PyYAML is not installed.
            FileNotFoundError: If the directory_path does not exist.

        Examples:
            >>> registry = MetricRegistry()
            >>> count = registry.load_metrics_from_directory("./metrics")
            >>> print(f"Loaded {count} metrics.")
        """
        if not HAS_YAML:
            logger.error(
                "PyYAML is required to load metrics from YAML files. Please install it."
            )
            raise ImportError("PyYAML is required to load metrics from YAML files.")

        dir_path = Path(directory_path)
        if not dir_path.is_dir():
            logger.error("Metric directory not found: %s", dir_path)
            raise FileNotFoundError(f"Metric directory not found: {dir_path}")

        logger.info("Loading metrics from directory: %s", dir_path)
        loaded_count = 0

        for filepath, data in iter_yaml_files(dir_path):
            if isinstance(data, Exception):
                logger.warning("Failed to parse YAML file %s: %s", filepath, data)
                continue

            if not data:
                logger.debug("Empty or null content in %s, skipping", filepath)
                continue

            # Accept single-dict or list-of-dicts structures -------------------
            metrics_to_process: list[dict[str, Any]]
            if isinstance(data, dict):
                metrics_to_process = [data]
            elif isinstance(data, list):
                metrics_to_process = data
            else:
                logger.warning(
                    "Invalid YAML structure in %s: expected dict or list, got %s",
                    filepath,
                    type(data).__name__,
                )
                continue

            for i, metric_data in enumerate(metrics_to_process):
                if not isinstance(metric_data, dict):
                    logger.warning(
                        "Invalid metric definition at index %s in %s: expected dict, got %s",
                        i,
                        filepath,
                        type(metric_data).__name__,
                    )
                    continue

                try:
                    model = MetricDefinition.model_validate(metric_data)
                    self.register_definition(model)
                    loaded_count += 1
                    logger.debug(
                        "Successfully loaded metric '%s' from %s", model.name, filepath
                    )
                except ValidationError as ve:
                    logger.warning(
                        "Invalid metric definition at index %s in %s: %s",
                        i,
                        filepath,
                        ve,
                    )

        logger.info("Successfully loaded %s metrics from %s.", loaded_count, dir_path)
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
            raise KeyError(  # noqa: B904
                f"Metric ID '{metric_id}' not found. Available: {self.list_metrics()}"
            )

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

    def register_definition(self, definition: MetricDefinition) -> None:
        """Register a single metric definition.

        Args:
            definition: The metric definition to register.

        Example:
            >>> from fin_statement_model.core.metrics.registry import MetricRegistry
            >>> from fin_statement_model.core.metrics.models import MetricDefinition
            >>> registry = MetricRegistry()
            >>> model = MetricDefinition(name='test', description='desc', inputs=['a'], formula='a', tags=[])
            >>> registry.register_definition(model)
            >>> 'test' in registry
        """
        metric_id = definition.name.lower().replace(" ", "_").replace("-", "_")
        if metric_id in self._metrics:
            logger.debug(f"Overwriting existing metric definition for '{metric_id}'")
        self._metrics[metric_id] = definition
        logger.debug(f"Registered metric definition: {metric_id}")


# Create the singleton instance (without auto-loading to prevent duplicates)
metric_registry = MetricRegistry()
