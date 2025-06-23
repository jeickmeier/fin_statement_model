"""Validation utilities previously hosted in the monolithic *mixins.py* file.

This split keeps the API and runtime behaviour identical while making the
codebase easier to navigate and keeping individual modules under the 300-LOC
budget mandated by the workspace rules.
"""

from __future__ import annotations

import logging
from typing import Any

from fin_statement_model.io.exceptions import ReadError

logger = logging.getLogger(__name__)

MAX_ERROR_PREVIEW: int = 10
MAX_WARNING_PREVIEW: int = 5


class ValidationResultCollector:
    """Collects validation results (errors & warnings) during reader processing."""

    def __init__(self, context: dict[str, Any] | None = None) -> None:
        """Create a new collector.

        Args:
            context: Optional context information (e.g., file path) that will
                be included in summary reports.
        """
        self.results: list[tuple[str, bool, str, str]] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.context = context or {}
        self._categories: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add_result(self, item_name: str, is_valid: bool, message: str, category: str = "general") -> None:
        """Record a validation *result* (error or success).

        Args:
            item_name: Human-readable identifier of the item being validated.
            is_valid: Whether the validation succeeded.
            message: Associated message (error/warning/ok information).
            category: Logical category used for aggregated statistics.
        """
        self.results.append((item_name, is_valid, message, category))
        if not is_valid:
            self.errors.append(f"{item_name}: {message}")
            self._categories[category] = self._categories.get(category, 0) + 1
        elif "warning" in message.lower():
            self.warnings.append(f"{item_name}: {message}")

    def add_warning(self, item_name: str, message: str, category: str = "warning") -> None:
        """Convenience wrapper to add a *warning* result."""
        self.warnings.append(f"{item_name}: {message}")
        self.results.append((item_name, True, f"WARNING: {message}", category))

    # Simple accessors ---------------------------------------------------
    def has_errors(self) -> bool:
        """Return ``True`` when any validation errors have been recorded."""
        return bool(self.errors)

    def has_warnings(self) -> bool:
        """Return ``True`` if one or more warnings were recorded."""
        return bool(self.warnings)

    def get_error_count_by_category(self) -> dict[str, int]:
        """Return aggregated error counts keyed by *category*."""
        return self._categories.copy()

    def get_items_with_errors(self) -> list[str]:
        """Return the set of item names that failed validation."""
        return [item for item, valid, _, _ in self.results if not valid]

    def get_summary(self) -> dict[str, Any]:
        """Return a machine-readable summary of collected validation results."""
        total = len(self.results)
        valid = sum(1 for _, is_valid, _, _ in self.results if is_valid)
        return {
            "total": total,
            "valid": valid,
            "invalid": total - valid,
            "errors": self.errors.copy(),
            "warnings": self.warnings.copy(),
            "error_rate": (total - valid) / total if total else 0.0,
            "warning_count": len(self.warnings),
            "categories": self._categories.copy(),
            "context": self.context.copy(),
            "items_with_errors": self.get_items_with_errors(),
        }

    # Mutating helpers ---------------------------------------------------
    def clear(self) -> None:
        """Reset the collector, discarding **all** stored results."""
        self.results.clear()
        self.errors.clear()
        self.warnings.clear()
        self._categories.clear()

    def merge(self, other: ValidationResultCollector) -> None:
        """Merge *other* collector contents into *self*."""
        for item, valid, message, category in other.results:
            self.add_result(item, valid, message, category)

    # Pretty print -------------------------------------------------------
    def get_detailed_report(self) -> str:
        """Return a human-readable multi-line validation report."""
        summary = self.get_summary()
        lines: list[str] = [
            "=== Validation Report ===",
            f"Total items processed: {summary['total']}",
            f"Valid items: {summary['valid']}",
            f"Invalid items: {summary['invalid']}",
            f"Warnings: {summary['warning_count']}",
            f"Overall success rate: {(1 - summary['error_rate']) * 100:.1f}%",
        ]
        if self.errors:
            lines.append("\n--- First 10 Errors ---")
            lines.extend(f"  * {e}" for e in self.errors[:MAX_ERROR_PREVIEW])
            if len(self.errors) > MAX_ERROR_PREVIEW:
                lines.append(f"  ... and {len(self.errors) - MAX_ERROR_PREVIEW} more errors")
        if self.warnings:
            lines.append("\n--- First 5 Warnings ---")
            lines.extend(f"  * {w}" for w in self.warnings[:MAX_WARNING_PREVIEW])
            if len(self.warnings) > MAX_WARNING_PREVIEW:
                lines.append(f"  ... and {len(self.warnings) - MAX_WARNING_PREVIEW} more warnings")
        return "\n".join(lines)


class ValidationMixin:  # pylint: disable=too-many-public-methods
    """Provides reusable dataframe/series validation helpers for readers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialise ValidationMixin state and propagate to next MRO element."""
        super().__init__(*args, **kwargs)
        self._validation_context: dict[str, Any] = {}

    # Context helpers ----------------------------------------------------
    def set_validation_context(self, **context: Any) -> None:
        """Store arbitrary context (e.g., file path) for inclusion in reports."""
        self._validation_context.update(context)

    def get_validation_context(self) -> dict[str, Any]:
        """Return a shallow copy of the current validation context mapping."""
        return self._validation_context.copy()

    # Column & period validation ----------------------------------------
    def validate_required_columns(self, df: Any, required: list[str], source_identifier: str = "data source") -> None:
        """Ensure *df* contains all *required* columns.

        Raises:
            ReadError: When one or more columns are missing.
        """
        if not hasattr(df, "columns"):
            raise ReadError(
                "Invalid data structure: expected DataFrame with columns attribute",
                source=source_identifier,
            )
        missing = set(required) - set(df.columns)
        if missing:
            raise ReadError(
                f"Missing required columns in {source_identifier}: {missing}",
                source=source_identifier,
            )

    def validate_column_bounds(
        self,
        df: Any,
        column_index: int,
        source_identifier: str = "data source",
        context: str = "column",
    ) -> None:
        """Validate that *column_index* is within the bounds of *df.columns*."""
        if not hasattr(df, "columns"):
            raise ReadError(
                "Invalid data structure: expected DataFrame with columns attribute",
                source=source_identifier,
            )
        if column_index >= len(df.columns) or column_index < 0:
            raise ReadError(
                f"{context} index ({column_index + 1}) is out of bounds. Found {len(df.columns)} columns.",
                source=source_identifier,
            )

    def validate_periods_exist(
        self,
        periods: list[str],
        source_identifier: str = "data source",
        min_periods: int = 1,
    ) -> None:
        """Validate that at least *min_periods* periods are present."""
        if not periods:
            raise ReadError(f"No periods found in {source_identifier}", source=source_identifier)
        if len(periods) < min_periods:
            raise ReadError(
                f"Insufficient periods in {source_identifier}. Found {len(periods)}, minimum required: {min_periods}",
                source=source_identifier,
            )

    # Numeric validation -------------------------------------------------
    def validate_numeric_value(
        self,
        value: Any,
        item_name: str,
        period: str,
        collector: ValidationResultCollector | None = None,
        allow_conversion: bool = True,
    ) -> tuple[bool, float | None]:
        """Validate and optionally convert *value* to ``float``.

        This refactored implementation keeps branching readable while
        reducing the total number of ``return`` statements to comply with
        lint rule *PLR0911* (≤ 6 distinct returns).
        """
        import numpy as np
        import pandas as pd

        def _record_failure(msg: str) -> None:
            if collector is not None:
                collector.add_result(item_name, False, msg)

        # Case 1 - value is explicitly missing / NaN ---------------------------------
        if pd.isna(value) or value is None:
            return True, None

        is_valid: bool = True
        numeric_value: float | None = None

        # Case 2 - numeric input ------------------------------------------------------
        if isinstance(value, (int, float)):  # noqa: UP038
            numeric_value = float(value)
            if not np.isfinite(numeric_value):
                is_valid = False
                _record_failure(f"Non-finite numeric value '{value}' for period '{period}'")

        # Case 3 - attempt conversion -------------------------------------------------
        elif allow_conversion:
            try:
                numeric_value = float(value)
                if not np.isfinite(numeric_value):
                    is_valid = False
                    _record_failure(f"Converted to non-finite value '{numeric_value}' for period '{period}'")
            except (ValueError, TypeError):
                is_valid = False
                _record_failure(f"Non-numeric value '{value}' for period '{period}'")

        # Case 4 - conversion not allowed --------------------------------------------
        else:
            is_valid = False
            _record_failure(f"Non-numeric value '{value}' for period '{period}'")

        return is_valid, numeric_value if is_valid else None

    # Node-name helper ---------------------------------------------------
    def validate_node_name(self, node_name: Any, *, allow_empty: bool = False) -> tuple[bool, str | None]:
        """Validate a node name, ensuring it is not empty."""
        import pandas as pd

        if pd.isna(node_name) or node_name is None:
            return allow_empty, None
        if not node_name or (isinstance(node_name, str) and not node_name.strip()):
            return allow_empty, None
        return True, str(node_name).strip()

    # Summary ------------------------------------------------------------
    def create_validation_summary(
        self,
        collector: ValidationResultCollector,
        source_identifier: str,
        *,
        operation: str = "processing",
    ) -> str:
        """Create a concise summary message from a validation collector."""
        if not collector.has_errors():
            return f"Successfully completed {operation} {source_identifier}"
        errors = "; ".join(collector.errors[:MAX_ERROR_PREVIEW])
        if len(collector.errors) > MAX_ERROR_PREVIEW:
            errors += f" (and {len(collector.errors) - MAX_ERROR_PREVIEW} more errors)"
        return f"Validation errors occurred during {operation} {source_identifier}: {errors}"


__all__ = [
    "ValidationMixin",
    "ValidationResultCollector",
]
