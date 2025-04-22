"""Metrics Subpackage.

Handles definition, loading, and access for financial metrics.
"""

import logging
from pathlib import Path

from .registry import MetricRegistry, HAS_YAML

logger = logging.getLogger(__name__)

# --- Singleton Registry Instance ---
# Create a single instance of the registry for the application lifetime.
metric_registry = MetricRegistry()

# --- Auto-load Built-in Metrics ---
# Determine the path to the built-in metrics directory relative to this file.
_current_dir = Path(__file__).parent
_builtin_dir = _current_dir / "builtin"

# Attempt to load metrics only if PyYAML is installed and the directory exists.
if HAS_YAML:
    if _builtin_dir.is_dir():
        try:
            loaded_count = metric_registry.load_metrics_from_directory(_builtin_dir)
            logger.info(f"Auto-loaded {loaded_count} built-in metrics from {_builtin_dir}")
        except Exception as e:
            # Log error but don't prevent library import if built-ins fail to load
            logger.error(
                f"Failed to auto-load built-in metrics from {_builtin_dir}: {e}",
                exc_info=True,
            )
    else:
        logger.warning(
            f"Built-in metric directory not found: {_builtin_dir}. No built-in metrics loaded."
        )
else:
    logger.warning("PyYAML not installed. Cannot load YAML metrics. Skipping auto-load.")


# --- Public API ---
__all__ = [
    "MetricRegistry",
    "metric_registry",  # Expose the singleton instance
]

# --- Deprecation Warning for METRIC_DEFINITIONS ---
# Provide a way to access the old dictionary format for compatibility,
# but issue a warning.

# Optional: Remove this completely if breaking change is acceptable
# from .definitions_basic import METRIC_DEFINITIONS as _OLD_METRIC_DEFINITIONS
_OLD_METRIC_DEFINITIONS = {}  # Start empty, populate if needed
