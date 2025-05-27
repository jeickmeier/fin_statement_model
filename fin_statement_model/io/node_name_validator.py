"""Node name validation and standardization utilities.

This module provides utilities for validating and standardizing node names
during data import operations.
"""

import logging
from typing import Optional
from fin_statement_model.core.nodes import standard_node_registry

logger = logging.getLogger(__name__)


class NodeNameValidator:
    """Validator for node names with standardization support.

    This class helps data readers validate and optionally standardize
    node names according to the standard node registry.
    """

    def __init__(
        self,
        strict_mode: bool = False,
        auto_standardize: bool = True,
        warn_on_non_standard: bool = True,
    ):
        """Initialize the validator.

        Args:
            strict_mode: If True, only standard names are allowed (no alternates).
            auto_standardize: If True, automatically convert alternate names to standard.
            warn_on_non_standard: If True, log warnings for non-standard names.
        """
        self.strict_mode = strict_mode
        self.auto_standardize = auto_standardize
        self.warn_on_non_standard = warn_on_non_standard
        self._validation_results: list[tuple[str, bool, str]] = []

    def validate_and_standardize(self, name: str) -> tuple[str, bool, str]:
        """Validate a node name and optionally standardize it.

        Args:
            name: The node name to validate.

        Returns:
            Tuple of (standardized_name, is_valid, message).
        """
        # Check if it's a recognized name
        is_valid, message = standard_node_registry.validate_node_name(name, strict=self.strict_mode)

        standardized_name = name

        if standard_node_registry.is_alternate_name(name):
            standard_name = standard_node_registry.get_standard_name(name)

            if self.auto_standardize:
                standardized_name = standard_name
                message = f"Standardized '{name}' to '{standard_name}'"
                logger.info(message)
            elif self.warn_on_non_standard:
                logger.warning(
                    f"Node name '{name}' is an alternate. "
                    f"Consider using standard name '{standard_name}'"
                )

        elif not standard_node_registry.is_recognized_name(name):
            if self.strict_mode:
                is_valid = False
                message = f"Node name '{name}' is not in the standard registry"
            elif self.warn_on_non_standard:
                logger.warning(
                    f"Node name '{name}' is not recognized in the standard registry. "
                    "This may cause issues with metrics that expect standard names."
                )

        # Store result for reporting
        self._validation_results.append((name, is_valid, message))

        return standardized_name, is_valid, message

    def validate_batch(self, names: list[str]) -> dict[str, tuple[str, bool, str]]:
        """Validate and standardize a batch of node names.

        Args:
            names: List of node names to validate.

        Returns:
            Dict mapping original names to (standardized_name, is_valid, message).
        """
        results = {}
        for name in names:
            standardized, is_valid, message = self.validate_and_standardize(name)
            results[name] = (standardized, is_valid, message)
        return results

    def get_validation_summary(self) -> dict[str, any]:
        """Get a summary of all validation results.

        Returns:
            Dictionary with validation statistics and details.
        """
        total = len(self._validation_results)
        valid = sum(1 for _, is_valid, _ in self._validation_results if is_valid)
        invalid = total - valid

        standard_names = []
        alternate_names = []
        unrecognized_names = []

        for name, _, _ in self._validation_results:
            if standard_node_registry.is_standard_name(name):
                standard_names.append(name)
            elif standard_node_registry.is_alternate_name(name):
                alternate_names.append(name)
            else:
                unrecognized_names.append(name)

        return {
            "total_validated": total,
            "valid": valid,
            "invalid": invalid,
            "standard_names": len(standard_names),
            "alternate_names": len(alternate_names),
            "unrecognized_names": len(unrecognized_names),
            "details": {
                "standard": standard_names,
                "alternate": alternate_names,
                "unrecognized": unrecognized_names,
            },
        }

    def clear_results(self) -> None:
        """Clear stored validation results."""
        self._validation_results.clear()


def create_node_name_mapping(
    input_names: list[str], auto_standardize: bool = True
) -> dict[str, str]:
    """Create a mapping from input names to standardized names.

    Args:
        input_names: List of input node names.
        auto_standardize: If True, map to standard names.

    Returns:
        Dict mapping input names to standardized names.
    """
    mapping = {}
    for name in input_names:
        if auto_standardize:
            standardized = standard_node_registry.get_standard_name(name)
            mapping[name] = standardized
        else:
            mapping[name] = name

    return mapping


def suggest_standard_name(name: str, threshold: float = 0.8) -> Optional[str]:
    """Suggest a standard name for an unrecognized name using fuzzy matching.

    Args:
        name: The unrecognized node name.
        threshold: Similarity threshold (0-1) for suggestions.

    Returns:
        Suggested standard name if a good match is found, None otherwise.
    """
    # This is a placeholder for future fuzzy matching implementation
    # For now, just check for exact case-insensitive matches
    name_lower = name.lower()

    for std_name in standard_node_registry.list_standard_names():
        if std_name.lower() == name_lower:
            return std_name

    # Check alternate names too
    for alt_name, std_name in standard_node_registry._alternate_to_standard.items():
        if alt_name.lower() == name_lower:
            return std_name

    return None
