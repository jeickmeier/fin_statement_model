"""Provide a registry for loading and accessing metric definitions from YAML files.

This module defines:
    - MetricRegistry: Load, validate, and retrieve metric definitions.
    - metric_registry: Singleton instance of MetricRegistry.

Example:
    >>> from fin_statement_model.core.metrics.registry import MetricRegistry
    >>> registry = MetricRegistry()
    >>> count = registry.load_metrics_from_directory("./metrics")
    >>> print(f"Loaded {count} metrics.")
    >>> registry.list_metrics()
    ['current_ratio', 'debt_equity_ratio']
    >>> definition = registry.get("current_ratio")
    >>> definition.name
    'Current Ratio'
"""

import logging
from pathlib import Path
from typing import ClassVar

# Use a try-except block for the YAML import
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from pydantic import ValidationError

from fin_statement_model.core.metrics.models import MetricDefinition

logger = logging.getLogger(__name__)


class MetricRegistry:
    """Registry for loading, discovering, and retrieving metric definitions from YAML files.

    The MetricRegistry provides methods to load metric definitions from a directory of YAML files,
    validate them, and retrieve them by ID. It supports both single-metric and multi-metric YAML files.

    Example:
        >>> from fin_statement_model.core.metrics.registry import MetricRegistry
        >>> registry = MetricRegistry()
        >>> count = registry.load_metrics_from_directory("./metrics")
        >>> print(f"Loaded {count} metrics.")
        >>> registry.list_metrics()
        ['current_ratio', 'debt_equity_ratio']
        >>> definition = registry.get("current_ratio")
        >>> definition.name
        'Current Ratio'
    """

    _REQUIRED_FIELDS: ClassVar[list[str]] = ["inputs", "formula", "description", "name"]

    def __init__(self) -> None:
        """Initialize the MetricRegistry with an empty metrics store.

        Example:
            >>> registry = MetricRegistry()
            >>> len(registry)
            0
        """
        self._metrics: dict[str, MetricDefinition] = {}
        logger.info("MetricRegistry initialized.")

    def load_metrics_from_directory(self, directory_path: str | Path) -> int:
        """Load all metric definitions from a directory of YAML files.

        This method searches for '*.yaml' files, validates their content,
        and stores them in the registry. Each YAML file can contain either:
          - A single metric definition (YAML dictionary at the root)
          - A list of metric definitions (YAML list of dictionaries at the root)

        Args:
            directory_path: Path to the directory containing metric YAML files.

        Returns:
            int: The number of metrics successfully loaded.

        Raises:
            ImportError: If PyYAML is not installed.
            FileNotFoundError: If the directory_path does not exist.

        Example:
            >>> registry = MetricRegistry()
            >>> count = registry.load_metrics_from_directory("./metrics")
            >>> print(f"Loaded {count} metrics.")
        """
        if not HAS_YAML:
            logger.error("PyYAML is required to load metrics from YAML files. Please install it.")
            raise ImportError("PyYAML is required to load metrics from YAML files.")

        dir_path = Path(directory_path)
        if not dir_path.is_dir():
            logger.error("Metric directory not found: %s", dir_path)
            raise FileNotFoundError(f"Metric directory not found: {dir_path}")

        logger.info("Loading metrics from directory: %s", dir_path)
        loaded_count = 0

        for filepath in dir_path.glob("*.yaml"):
            logger.debug("Processing file: %s", filepath)
            try:
                content = filepath.read_text(encoding="utf-8")

                # Use standard YAML parsing
                try:
                    data = yaml.safe_load(content)
                except yaml.YAMLError as e:
                    logger.warning("Failed to parse YAML file %s: %s", filepath, e)
                    continue

                if not data:
                    logger.debug("Empty or null content in %s, skipping", filepath)
                    continue

                # Handle both single metric and list of metrics
                metrics_to_process = []

                if isinstance(data, dict):
                    # Single metric definition
                    metrics_to_process = [data]
                elif isinstance(data, list):
                    # List of metric definitions
                    metrics_to_process = data
                else:
                    logger.warning(
                        "Invalid YAML structure in %s: expected dict or list, got %s",
                        filepath,
                        type(data).__name__,
                    )
                    continue

                # Process each metric definition
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
                        # Validate and register the metric
                        model = MetricDefinition.model_validate(metric_data)
                        self.register_definition(model)
                        loaded_count += 1
                        logger.debug("Successfully loaded metric '%s' from %s", model.name, filepath)

                    except ValidationError as ve:
                        logger.warning("Invalid metric definition at index %s in %s: %s", i, filepath, ve)
                        continue

            except Exception:
                logger.exception("Failed to process file %s", filepath)
                continue

        logger.info("Successfully loaded %s metrics from %s.", loaded_count, dir_path)
        return loaded_count

    def get(self, metric_id: str) -> MetricDefinition:
        """Retrieve a loaded metric definition by its ID.

        Args:
            metric_id: Identifier of the metric (filename stem or metric name in snake_case).

        Returns:
            MetricDefinition: The metric definition object.

        Raises:
            KeyError: If the metric_id is not found in the registry.

        Example:
            >>> registry = MetricRegistry()
            >>> # registry.load_metrics_from_directory(...) must be called first
            >>> # registry.get('gross_profit')
        """
        try:
            return self._metrics[metric_id]
        except KeyError:
            logger.warning("Metric ID '%s' not found in registry.", metric_id)
            raise KeyError(f"Metric ID '{metric_id}' not found. Available: {self.list_metrics()}") from None

    def list_metrics(self) -> list[str]:
        """Get a sorted list of all loaded metric IDs.

        Returns:
            list[str]: A sorted list of available metric IDs.

        Example:
            >>> registry = MetricRegistry()
            >>> registry.list_metrics()
            ['current_ratio', 'debt_equity_ratio']
        """
        return sorted(self._metrics.keys())

    def __len__(self) -> int:
        """Return the number of loaded metrics.

        Returns:
            int: The count of metrics loaded into the registry.

        Example:
            >>> registry = MetricRegistry()
            >>> len(registry)
            5
        """
        return len(self._metrics)

    def __contains__(self, metric_id: str) -> bool:
        """Check if a metric ID exists in the registry.

        Args:
            metric_id: The metric identifier to check.

        Returns:
            bool: True if the metric is present, False otherwise.

        Example:
            >>> registry = MetricRegistry()
            >>> "current_ratio" in registry
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
            >>> model = MetricDefinition(name="test", description="desc", inputs=["a"], formula="a", tags=[])
            >>> registry.register_definition(model)
            >>> "test" in registry
            True
        """
        metric_id = definition.name.lower().replace(" ", "_").replace("-", "_")
        if metric_id in self._metrics:
            logger.debug("Overwriting existing metric definition for '%s'", metric_id)
        self._metrics[metric_id] = definition
        logger.debug("Registered metric definition: %s", metric_id)


# Create the singleton instance (without auto-loading to prevent duplicates)
metric_registry = MetricRegistry()
