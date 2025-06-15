"""Unified node name validation and standardization utilities.

This module provides a comprehensive validator that combines basic validation
with context-aware pattern recognition for financial statement nodes.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional

from fin_statement_model.core.nodes import Node
from fin_statement_model.core.nodes.standard_registry import StandardNodeRegistry

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a node name validation."""

    original_name: str
    standardized_name: str
    is_valid: bool
    message: str
    category: str
    confidence: float = 1.0
    suggestions: list[str] = field(default_factory=list)


class UnifiedNodeValidator:
    """Unified validator for node names with pattern recognition and standardization.

    This validator combines the functionality of NodeNameValidator and
    ContextAwareNodeValidator into a single, more efficient implementation.
    """

    # Common sub-node patterns
    SUBNODE_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"^(.+)_(q[1-4])$", "quarterly"),
        (r"^(.+)_(fy\d{4})$", "fiscal_year"),
        (r"^(.+)_(\d{4})$", "annual"),
        (r"^(.+)_(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)$", "monthly"),
        (r"^(.+)_(actual|budget|forecast)$", "scenario"),
    ]

    # Generic segment pattern - must be checked separately
    SEGMENT_PATTERN = r"^(.+)_([a-z_]+)$"

    # Formula patterns - check exact endings
    FORMULA_ENDINGS: ClassVar[list[str]] = [
        "_margin",
        "_ratio",
        "_growth",
        "_change",
        "_pct",
    ]

    def __init__(
        self,
        registry: StandardNodeRegistry,
        strict_mode: Optional[bool] = None,
        auto_standardize: Optional[bool] = None,
        warn_on_non_standard: Optional[bool] = None,
        enable_patterns: bool = True,
    ):
        """Initialize the unified validator.

        Args:
            registry: The StandardNodeRegistry instance.
            strict_mode: If True, only standard names are allowed.
                        If None, uses config.validation.strict_mode.
            auto_standardize: If True, convert alternate names to standard.
                            If None, uses config.validation.auto_standardize_names.
            warn_on_non_standard: If True, log warnings for non-standard names.
                                If None, uses config.validation.warn_on_non_standard.
            enable_patterns: If True, recognize sub-node and formula patterns.
        """
        from fin_statement_model import get_config

        config = get_config()

        self._registry = registry
        self.strict_mode = (
            strict_mode if strict_mode is not None else config.validation.strict_mode
        )
        self.auto_standardize = (
            auto_standardize
            if auto_standardize is not None
            else config.validation.auto_standardize_names
        )
        self.warn_on_non_standard = (
            warn_on_non_standard
            if warn_on_non_standard is not None
            else config.validation.warn_on_non_standard
        )
        self.enable_patterns = enable_patterns
        self._validation_cache: dict[str, ValidationResult] = {}

    def validate(
        self,
        name: str,
        node_type: Optional[str] = None,
        parent_nodes: Optional[list[str]] = None,
        use_cache: bool = True,
    ) -> ValidationResult:
        """Validate a node name with full context awareness.

        Args:
            name: The node name to validate.
            node_type: Optional node type hint.
            parent_nodes: Optional list of parent node names.
            use_cache: Whether to use cached results.

        Returns:
            ValidationResult with all validation details.
        """
        # Check cache first
        cache_key = f"{name}:{node_type}:{','.join(parent_nodes or [])}"
        if use_cache and cache_key in self._validation_cache:
            return self._validation_cache[cache_key]

        # Start validation
        result = self._perform_validation(name, node_type, parent_nodes)

        # Cache result
        if use_cache:
            self._validation_cache[cache_key] = result

        # Log warnings if configured
        if self.warn_on_non_standard and result.category in ["custom", "invalid"]:
            logger.warning(f"{result.message}")
            if result.suggestions:
                logger.info(
                    f"Suggestions for '{name}': {'; '.join(result.suggestions)}"
                )

        return result

    def _perform_validation(
        self,
        name: str,
        node_type: Optional[str],
        parent_nodes: Optional[list[str]],
    ) -> ValidationResult:
        """Perform the actual validation logic."""
        # Normalize name to lowercase for registry checks
        normalized_name = name.lower()

        # Check standard names first (using normalized name)
        if self._registry.is_standard_name(normalized_name):
            # If original name is different case, standardize to lowercase
            standardized = normalized_name if name != normalized_name else name
            return ValidationResult(
                original_name=name,
                standardized_name=standardized,
                is_valid=True,
                message=f"Standard node: {normalized_name}",
                category="standard",
                confidence=1.0,
            )

        # Check alternate names (using normalized name)
        if self._registry.is_alternate_name(normalized_name):
            standard_name = self._registry.get_standard_name(normalized_name)
            return ValidationResult(
                original_name=name,
                standardized_name=standard_name if self.auto_standardize else name,
                is_valid=True,
                message=f"{'Standardized' if self.auto_standardize else 'Alternate name for'} '{standard_name}'",
                category="alternate",
                confidence=1.0,
            )

        # Pattern recognition if enabled
        if self.enable_patterns:
            pattern_result = self._check_pattern_validations(
                name, node_type, parent_nodes
            )
            if pattern_result:
                return pattern_result

        # Generate suggestions for unrecognized names
        suggestions = self._generate_suggestions(name)

        # Default to custom/invalid
        return ValidationResult(
            original_name=name,
            standardized_name=name,
            is_valid=not self.strict_mode,
            message=f"{'Non-standard' if self.strict_mode else 'Custom'} node: '{name}'",
            category="invalid" if self.strict_mode else "custom",
            confidence=0.5,
            suggestions=suggestions,
        )

    def _check_pattern_validations(
        self,
        name: str,
        node_type: Optional[str],
        parent_nodes: Optional[list[str]],
    ) -> Optional[ValidationResult]:
        """Check all pattern-based validations."""
        # Check formula patterns first (more specific)
        if node_type in ["calculation", "formula", None]:
            pattern_result = self._check_formula_ending(name)
            if pattern_result:
                base_name, formula_type = pattern_result

                return ValidationResult(
                    original_name=name,
                    standardized_name=name,
                    is_valid=True,
                    message=f"Formula node: {formula_type} of '{base_name}'",
                    category="formula",
                    confidence=0.85,
                )

        # Check specific sub-node patterns
        subnode_match = self._check_patterns(name, self.SUBNODE_PATTERNS, "subnode")
        if subnode_match:
            base_name, suffix, pattern_type = subnode_match
            # Normalize base name for registry check
            is_base_standard = self._registry.is_recognized_name(base_name.lower())

            return ValidationResult(
                original_name=name,
                standardized_name=name,
                is_valid=not self.strict_mode or is_base_standard,
                message=f"{'Valid' if is_base_standard else 'Non-standard'} sub-node of '{base_name}' ({pattern_type})",
                category="subnode" if is_base_standard else "subnode_nonstandard",
                confidence=0.9 if is_base_standard else 0.7,
            )

        # Check generic segment pattern last
        match = re.match(self.SEGMENT_PATTERN, name.lower())
        if match and "_" in name:
            base_name = match.group(1)
            suffix = match.group(2)

            # Only treat as segment if it doesn't match other patterns
            # and has a reasonable structure (geographic/business segment)
            segment_keywords = [
                "america",
                "europe",
                "asia",
                "pacific",
                "africa",
                "region",
                "domestic",
                "international",
                "global",
                "local",
                "retail",
                "wholesale",
                "online",
                "digital",
                "services",
                "products",
                "solutions",
                "segment",
                "division",
                "unit",
            ]

            if len(suffix) > 2 and any(
                keyword in suffix.lower() for keyword in segment_keywords
            ):
                # Normalize base name for registry check
                is_base_standard = self._registry.is_recognized_name(base_name.lower())

                return ValidationResult(
                    original_name=name,
                    standardized_name=name,
                    is_valid=not self.strict_mode or is_base_standard,
                    message=f"{'Valid' if is_base_standard else 'Non-standard'} sub-node of '{base_name}' (segment)",
                    category="subnode" if is_base_standard else "subnode_nonstandard",
                    confidence=0.85 if is_base_standard else 0.65,
                )

        return None

    def _check_formula_ending(self, name: str) -> Optional[tuple[str, str]]:
        """Check if name ends with a formula pattern."""
        name_lower = name.lower()

        for ending in self.FORMULA_ENDINGS:
            if name_lower.endswith(ending):
                base_name = name[: -len(ending)]
                formula_type = ending[1:]  # Remove underscore
                return base_name, formula_type

        return None

    def _check_patterns(
        self,
        name: str,
        patterns: list[tuple[str, str]],
        pattern_category: str,
    ) -> Optional[tuple[str, str, str]]:
        """Check if name matches any pattern in the list."""
        name_lower = name.lower()

        for pattern, pattern_type in patterns:
            match = re.match(pattern, name_lower)
            if match:
                base_name = match.group(1)
                suffix = (
                    match.group(2)
                    if (match.lastindex is not None and match.lastindex > 1)
                    else ""
                )
                return base_name, suffix, pattern_type

        return None

    def _generate_suggestions(self, name: str) -> list[str]:
        """Generate improvement suggestions for non-standard names."""
        suggestions_with_scores = []
        name_lower = name.lower()

        # Find similar standard names
        for std_name in self._registry.list_standard_names():
            std_lower = std_name.lower()

            # Calculate similarity score
            score = 0.0

            # Exact prefix match gets highest score
            if std_lower.startswith(name_lower) or name_lower.startswith(std_lower):
                score = 0.9
            # Check character overlap
            elif self._is_similar(name_lower, std_lower):
                overlap = len(set(name_lower) & set(std_lower))
                min_len = min(len(name_lower), len(std_lower))
                score = overlap / min_len * 0.8

            if score > 0:
                suggestions_with_scores.append(
                    (score, f"Consider using standard name: '{std_name}'")
                )

        # Sort by score (highest first) and take top suggestions
        suggestions_with_scores.sort(key=lambda x: x[0], reverse=True)
        suggestions = [msg for _, msg in suggestions_with_scores[:3]]

        # Check for pattern improvements
        if "_" in name and len(suggestions) < 3:
            parts = name.split("_", 1)
            base = parts[0]

            # Suggest standardizing the base
            for std_name in self._registry.list_standard_names():
                if self._is_similar(base.lower(), std_name.lower()):
                    suggestions.append(
                        f"Consider using '{std_name}_{parts[1]}' for consistency"
                    )
                    break

        # Generic suggestions if nothing specific found
        if not suggestions:
            if any(
                suffix in name for suffix in ["_margin", "_ratio", "_growth", "_pct"]
            ):
                suggestions.append(
                    "Formula node detected - ensure base name follows standard conventions"
                )
            else:
                suggestions.append(
                    "Consider using a standard node name for better metric compatibility"
                )

        return suggestions[:3]  # Return top 3 suggestions

    def _is_similar(self, str1: str, str2: str, threshold: float = 0.6) -> bool:
        """Check if two strings are similar enough."""
        if len(str1) < 3 or len(str2) < 3:
            return False

        # Check if one is a prefix of the other
        if str1.startswith(str2) or str2.startswith(str1):
            return True

        # Check containment
        if str1 in str2 or str2 in str1:
            return True

        # Check character overlap
        overlap = len(set(str1) & set(str2))
        min_len = min(len(str1), len(str2))

        return overlap / min_len >= threshold

    def validate_batch(
        self,
        names: list[str],
        node_types: Optional[dict[str, str]] = None,
        parent_map: Optional[dict[str, list[str]]] = None,
    ) -> dict[str, ValidationResult]:
        """Validate multiple node names efficiently.

        Args:
            names: List of node names to validate.
            node_types: Optional mapping of names to node types.
            parent_map: Optional mapping of names to parent node lists.

        Returns:
            Dictionary mapping names to ValidationResults.
        """
        results = {}
        node_types = node_types or {}
        parent_map = parent_map or {}

        for name in names:
            result = self.validate(
                name,
                node_type=node_types.get(name),
                parent_nodes=parent_map.get(name),
            )
            results[name] = result

        return results

    def validate_graph(self, nodes: list[Node]) -> dict[str, Any]:
        """Validate all nodes in a graph with full context.

        Args:
            nodes: List of Node objects from the graph.

        Returns:
            Comprehensive validation report.
        """
        # Build context maps
        node_types = {}
        parent_map = {}

        for node in nodes:
            # Determine node type
            class_name = node.__class__.__name__
            if "Formula" in class_name:
                node_types[node.name] = "formula"
            elif "Calculation" in class_name:
                node_types[node.name] = "calculation"
            elif "Forecast" in class_name:
                node_types[node.name] = "forecast"
            else:
                node_types[node.name] = "data"

            # Extract parent nodes
            if hasattr(node, "inputs"):
                if isinstance(node.inputs, dict):
                    parent_map[node.name] = [p.name for p in node.inputs.values()]
                elif isinstance(node.inputs, list):
                    parent_map[node.name] = [p.name for p in node.inputs]

        # Validate all nodes
        node_names = [node.name for node in nodes]
        results = self.validate_batch(node_names, node_types, parent_map)

        # Build summarized report
        by_category: dict[str, list[str]] = {}
        by_validity: dict[str, int] = {"valid": 0, "invalid": 0}
        suggestions: dict[str, list[str]] = {}
        # Populate report sections
        for name, result in results.items():
            # Count by category
            cat = result.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(name)
            # Count by validity
            if result.is_valid:
                by_validity["valid"] += 1
            else:
                by_validity["invalid"] += 1
            # Collect suggestions
            if result.suggestions:
                suggestions[name] = result.suggestions
        return {
            "total": len(results),
            "by_category": by_category,
            "by_validity": by_validity,
            "suggestions": suggestions,
            "details": results,
        }

    def clear_cache(self) -> None:
        """Clear the validation cache."""
        self._validation_cache.clear()


def create_validator(
    registry: StandardNodeRegistry, **kwargs: Any
) -> UnifiedNodeValidator:
    """Create a validator instance with the given configuration."""
    return UnifiedNodeValidator(registry, **kwargs)
