"""Context-aware node name validation with sub-node recognition.

This module provides enhanced validation that understands the relationship
between nodes and their sub-components.
"""

import logging
import re
from typing import ClassVar, Optional
from fin_statement_model.core.nodes import Node, standard_node_registry

logger = logging.getLogger(__name__)


class ContextAwareNodeValidator:
    """Enhanced validator that understands node relationships and patterns.

    This validator is smarter about:
    - Sub-nodes that aggregate to standard nodes (e.g., revenue_region_X)
    - Formula nodes with descriptive names
    - Temporary calculation nodes
    - Custom metric nodes
    """

    # Common sub-node patterns
    SUBNODE_PATTERNS: ClassVar[list[str]] = [
        r"^(.+)_(q[1-4])$",  # Quarterly: revenue_q1, revenue_q2
        r"^(.+)_(fy\d{4})$",  # Fiscal year: revenue_fy2023
        r"^(.+)_(\d{4})$",  # Year: revenue_2023
        r"^(.+)_(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)$",  # Monthly
        r"^(.+)_([a-z_]+)$",  # Geographic/segment: revenue_north_america
        r"^(.+)_(actual|budget|forecast)$",  # Scenario: revenue_actual
    ]

    # Node type patterns that should be treated differently
    FORMULA_PATTERNS: ClassVar[list[str]] = [
        r"^(.+)_margin$",  # Margin calculations
        r"^(.+)_ratio$",  # Ratio calculations
        r"^(.+)_growth$",  # Growth calculations
        r"^(.+)_change$",  # Change calculations
        r"^(.+)_pct$",  # Percentage calculations
    ]

    def __init__(
        self,
        strict_mode: bool = False,
        auto_standardize: bool = True,
        validate_subnodes: bool = True,
        validate_formulas: bool = True,
    ):
        """Initialize the context-aware validator.

        Args:
            strict_mode: If True, enforce strict standard naming for base nodes.
            auto_standardize: If True, convert alternate names to standard.
            validate_subnodes: If True, validate that sub-node bases are standard.
            validate_formulas: If True, check formula node patterns.
        """
        self.strict_mode = strict_mode
        self.auto_standardize = auto_standardize
        self.validate_subnodes = validate_subnodes
        self.validate_formulas = validate_formulas
        self._validation_results: list[tuple[str, bool, str, str]] = []

    def validate_node(
        self,
        name: str,
        node_type: Optional[str] = None,
        parent_nodes: Optional[list[str]] = None,
    ) -> tuple[str, bool, str, str]:
        """Validate a node name with context awareness.

        Args:
            name: The node name to validate.
            node_type: Optional node type (e.g., 'data', 'calculation', 'formula').
            parent_nodes: Optional list of parent node names for context.

        Returns:
            Tuple of (standardized_name, is_valid, message, category).
        """
        # Check standard and alternate names
        result = self._check_standard_or_alternate(name)
        if result:
            return result

        # Check sub-node patterns
        if self.validate_subnodes:
            result = self._check_subnode_validation(name)
            if result:
                return result

        # Check formula patterns
        if self.validate_formulas and node_type in ["calculation", "formula", None]:
            result = self._check_formula_validation(name)
            if result:
                return result

        # Check parent relationships
        if parent_nodes:
            result = self._check_parent_validation(name, parent_nodes)
            if result:
                return result

        # Default to custom node
        return self._handle_custom_node(name)

    def _check_standard_or_alternate(self, name: str) -> Optional[tuple[str, bool, str, str]]:
        """Check if name is standard or alternate."""
        if standard_node_registry.is_standard_name(name):
            return name, True, f"Standard node: {name}", "standard"

        if standard_node_registry.is_alternate_name(name):
            standard_name = standard_node_registry.get_standard_name(name)
            if self.auto_standardize:
                return (
                    standard_name,
                    True,
                    f"Standardized '{name}' to '{standard_name}'",
                    "alternate",
                )
            else:
                return name, True, f"Alternate name for '{standard_name}'", "alternate"

        return None

    def _check_subnode_validation(self, name: str) -> Optional[tuple[str, bool, str, str]]:
        """Validate sub-node patterns."""
        sub_result = self._check_subnode_pattern(name)
        if sub_result:
            base_name, suffix, pattern_type = sub_result
            if standard_node_registry.is_recognized_name(base_name):
                return (
                    name,
                    True,
                    f"Valid sub-node of '{base_name}' ({pattern_type})",
                    "subnode",
                )
            else:
                msg = f"Sub-node with non-standard base: '{base_name}' ({pattern_type})"
                return name, not self.strict_mode, msg, "subnode_nonstandard"
        return None

    def _check_formula_validation(self, name: str) -> Optional[tuple[str, bool, str, str]]:
        """Validate formula patterns."""
        formula_result = self._check_formula_pattern(name)
        if formula_result:
            base_name, formula_type = formula_result
            return (
                name,
                True,
                f"Formula node: {formula_type} of '{base_name}'",
                "formula",
            )
        return None

    def _check_parent_validation(
        self, name: str, parent_nodes: list[str]
    ) -> Optional[tuple[str, bool, str, str]]:
        """Validate based on parent relationships."""
        if self._check_parent_relationship(name, parent_nodes):
            return (
                name,
                True,
                f"Related to parent nodes: {', '.join(parent_nodes)}",
                "derived",
            )
        return None

    def _handle_custom_node(self, name: str) -> tuple[str, bool, str, str]:
        """Handle custom nodes."""
        is_valid = not self.strict_mode
        if self.strict_mode:
            msg = f"Non-standard node name: '{name}'"
        else:
            msg = f"Custom node: '{name}' (not in standard registry)"

        return name, is_valid, msg, "custom"

    def _check_subnode_pattern(self, name: str) -> Optional[tuple[str, str, str]]:
        """Check if name matches a sub-node pattern.

        Returns:
            Tuple of (base_name, suffix, pattern_type) if matches, None otherwise.
        """
        for pattern in self.SUBNODE_PATTERNS:
            match = re.match(pattern, name.lower())
            if match:
                base_name = match.group(1)
                suffix = match.group(2) if match.lastindex > 1 else ""

                # Determine pattern type
                if "_q" in name:
                    pattern_type = "quarterly"
                elif "_fy" in name or re.match(r".*_\d{4}$", name):
                    pattern_type = "annual"
                elif any(
                    month in name
                    for month in [
                        "jan",
                        "feb",
                        "mar",
                        "apr",
                        "may",
                        "jun",
                        "jul",
                        "aug",
                        "sep",
                        "oct",
                        "nov",
                        "dec",
                    ]
                ):
                    pattern_type = "monthly"
                elif any(scenario in name for scenario in ["actual", "budget", "forecast"]):
                    pattern_type = "scenario"
                else:
                    pattern_type = "segment"

                return base_name, suffix, pattern_type

        return None

    def _check_formula_pattern(self, name: str) -> Optional[tuple[str, str]]:
        """Check if name matches a formula pattern.

        Returns:
            Tuple of (base_name, formula_type) if matches, None otherwise.
        """
        for pattern in self.FORMULA_PATTERNS:
            match = re.match(pattern, name.lower())
            if match:
                base_name = match.group(1)

                # Determine formula type
                if name.endswith("_margin"):
                    formula_type = "margin"
                elif name.endswith("_ratio"):
                    formula_type = "ratio"
                elif name.endswith("_growth"):
                    formula_type = "growth"
                elif name.endswith("_change"):
                    formula_type = "change"
                elif name.endswith("_pct"):
                    formula_type = "percentage"
                else:
                    formula_type = "calculation"

                return base_name, formula_type

        return None

    def _check_parent_relationship(self, name: str, parent_nodes: list[str]) -> bool:
        """Check if node name is related to its parents."""
        name_lower = name.lower()

        # Check if any parent name is contained in this node name
        for parent in parent_nodes:
            parent_lower = parent.lower()
            if parent_lower in name_lower:
                return True

            # Check if parent is a standard name and this derives from it
            if standard_node_registry.is_standard_name(parent):
                definition = standard_node_registry.get_definition(parent)
                if definition:
                    # Check against alternate names too
                    for alt in definition.alternate_names:
                        if alt.lower() in name_lower:
                            return True

        return False

    def validate_graph_nodes(self, nodes: list[Node]) -> dict[str, any]:
        """Validate all nodes in a graph with full context.

        Args:
            nodes: List of Node objects from the graph.

        Returns:
            Validation report with categorized results.
        """
        results = {
            "standard": [],
            "alternate": [],
            "subnode": [],
            "formula": [],
            "derived": [],
            "custom": [],
            "invalid": [],
        }

        for node in nodes:
            # Get parent node names for context - handle both list and dict inputs
            parent_names = None
            if hasattr(node, "inputs"):
                if isinstance(node.inputs, dict):
                    # FormulaCalculationNode has dict inputs
                    parent_names = [p.name for p in node.inputs.values()]
                elif isinstance(node.inputs, list):
                    # CalculationNode and CustomCalculationNode have list inputs
                    parent_names = [p.name for p in node.inputs]

            # Determine node type
            node_type = None
            if hasattr(node, "__class__"):
                class_name = node.__class__.__name__
                if "Formula" in class_name:
                    node_type = "formula"
                elif "Calculation" in class_name:
                    node_type = "calculation"
                elif "Item" in class_name:
                    node_type = "data"

            # Validate with context
            std_name, is_valid, msg, category = self.validate_node(
                node.name, node_type=node_type, parent_nodes=parent_names
            )

            # Store result
            result = {
                "name": node.name,
                "standardized": std_name,
                "valid": is_valid,
                "message": msg,
                "node_type": node_type,
                "parents": parent_names,
            }

            if not is_valid:
                results["invalid"].append(result)
            else:
                results[category].append(result)

        return results

    def suggest_naming_improvements(self, name: str) -> list[str]:
        """Suggest improvements for non-standard node names.

        Args:
            name: The node name to improve.

        Returns:
            List of suggested improvements.
        """
        suggestions = []

        # First check if the name is already standard - no suggestions needed
        if standard_node_registry.is_standard_name(name):
            return suggestions

        # Check if it's an alternate name - suggest the standard version
        if standard_node_registry.is_alternate_name(name):
            standard_name = standard_node_registry.get_standard_name(name)
            suggestions.append(f"Consider using standard name: '{standard_name}'")
            return suggestions

        # Check if it's close to a standard name (for typos or similar names)
        name_lower = name.lower().replace("_", "").replace("-", "")

        for std_name in standard_node_registry.list_standard_names():
            std_lower = std_name.lower().replace("_", "")

            # Only suggest if it's similar but not the same
            if (
                std_name != name
                and (std_lower in name_lower or name_lower in std_lower)
                and len(name_lower) > 3
                and len(std_lower) > 3
            ):
                # Additional check to avoid suggesting very different names
                # Only suggest if there's substantial overlap
                overlap = len(set(name_lower) & set(std_lower))
                if overlap >= min(len(name_lower), len(std_lower)) * 0.6:
                    suggestions.append(f"Consider using standard name: '{std_name}'")

        # Check sub-node patterns
        if "_" in name:
            parts = name.split("_")
            base = parts[0]

            if standard_node_registry.is_recognized_name(base):
                # This is a valid sub-node pattern, no suggestions needed
                return suggestions
            else:
                # Check if base is close to a standard name
                matching_suggestions = [
                    f"Consider using '{std_name}_{parts[1]}' for consistency"
                    for std_name in standard_node_registry.list_standard_names()
                    if base.lower() in std_name.lower() and base != std_name
                ]
                suggestions.extend(matching_suggestions)

        # If no specific suggestions and it's not recognized, suggest general guidance
        if not suggestions and not standard_node_registry.is_recognized_name(name):
            # Check if it might be a formula pattern
            if any(
                suffix in name for suffix in ["_margin", "_ratio", "_growth", "_change", "_pct"]
            ):
                suggestions.append(
                    "Formula node detected - ensure base name follows standard conventions"
                )
            else:
                suggestions.append(
                    "Consider using a standard node name for better metric compatibility"
                )

        return suggestions
