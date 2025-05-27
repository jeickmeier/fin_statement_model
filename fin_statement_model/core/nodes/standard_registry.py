"""Registry for standard node names.

This module provides a registry system for standardized node names,
ensuring consistency across financial models and enabling metrics to work properly.
"""

import logging
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class StandardNodeDefinition(BaseModel):
    """Define a standard node with metadata.

    Attributes:
        category: The main category (e.g., balance_sheet_assets, income_statement)
        subcategory: The subcategory within the main category
        description: Human-readable description of the node
        alternate_names: List of alternate names that should map to this standard name
        sign_convention: Whether values are typically positive or negative
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    category: str
    subcategory: str
    description: str
    alternate_names: list[str] = []
    sign_convention: str = "positive"  # 'positive' or 'negative'


class StandardNodeRegistry:
    """Registry for standard node definitions.

    This class manages loading and accessing standardized node definitions,
    providing validation and alternate name resolution capabilities.

    Attributes:
        _standard_nodes: Dict mapping standard node names to their definitions
        _alternate_to_standard: Dict mapping alternate names to standard names
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._standard_nodes: dict[str, StandardNodeDefinition] = {}
        self._alternate_to_standard: dict[str, str] = {}
        self._categories: set[str] = set()

    def load_from_yaml(self, yaml_path: Path) -> int:
        """Load standard node definitions from a YAML file.

        Args:
            yaml_path: Path to the YAML file containing node definitions.

        Returns:
            Number of nodes loaded.

        Raises:
            ValueError: If the YAML file has invalid structure or duplicate names.
            FileNotFoundError: If the YAML file doesn't exist.
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"Standard nodes file not found: {yaml_path}")

        try:
            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {yaml_path}: {e}") from e

        if not isinstance(data, dict):
            raise TypeError(f"Expected dict at root of {yaml_path}, got {type(data)}")

        # Clear existing data
        self._standard_nodes.clear()
        self._alternate_to_standard.clear()
        self._categories.clear()

        nodes_loaded = 0

        # Load each node definition
        for node_name, node_data in data.items():
            if not isinstance(node_data, dict):
                logger.warning(f"Skipping invalid node definition '{node_name}': not a dict")
                continue

            try:
                definition = StandardNodeDefinition(**node_data)

                # Check for duplicate standard names
                if node_name in self._standard_nodes:
                    raise ValueError(f"Duplicate standard node name: {node_name}")

                # Add to main registry
                self._standard_nodes[node_name] = definition
                self._categories.add(definition.category)

                # Map alternate names
                for alt_name in definition.alternate_names:
                    if alt_name in self._alternate_to_standard:
                        existing_standard = self._alternate_to_standard[alt_name]
                        raise ValueError(
                            f"Alternate name '{alt_name}' already maps to '{existing_standard}', "
                            f"cannot also map to '{node_name}'"
                        )
                    self._alternate_to_standard[alt_name] = node_name

                nodes_loaded += 1

            except Exception as e:
                logger.exception(f"Error loading node '{node_name}'")
                raise ValueError(f"Invalid node definition for '{node_name}': {e}") from e

        logger.info(
            f"Loaded {nodes_loaded} standard node definitions "
            f"with {len(self._alternate_to_standard)} alternate names"
        )
        return nodes_loaded

    def load_from_yaml_file(self, yaml_path: Path) -> int:
        """Load standard node definitions from a single YAML file without clearing existing data.

        Args:
            yaml_path: Path to the YAML file containing node definitions.

        Returns:
            Number of nodes loaded from this file.

        Raises:
            ValueError: If the YAML file has invalid structure or duplicate names.
            FileNotFoundError: If the YAML file doesn't exist.
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"Standard nodes file not found: {yaml_path}")

        try:
            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {yaml_path}: {e}") from e

        if not isinstance(data, dict):
            raise TypeError(f"Expected dict at root of {yaml_path}, got {type(data)}")

        nodes_loaded = 0

        # Load each node definition
        for node_name, node_data in data.items():
            if not isinstance(node_data, dict):
                logger.warning(f"Skipping invalid node definition '{node_name}': not a dict")
                continue

            try:
                definition = StandardNodeDefinition(**node_data)

                # Check for duplicate standard names
                if node_name in self._standard_nodes:
                    logger.debug(f"Overwriting existing standard node: {node_name}")

                # Add to main registry
                self._standard_nodes[node_name] = definition
                self._categories.add(definition.category)

                # Map alternate names
                for alt_name in definition.alternate_names:
                    if alt_name in self._alternate_to_standard:
                        existing_standard = self._alternate_to_standard[alt_name]
                        if existing_standard != node_name:
                            logger.debug(
                                f"Alternate name '{alt_name}' already maps to '{existing_standard}', "
                                f"now mapping to '{node_name}'"
                            )
                    self._alternate_to_standard[alt_name] = node_name

                nodes_loaded += 1

            except Exception as e:
                logger.exception(f"Error loading node '{node_name}' from {yaml_path}")
                raise ValueError(f"Invalid node definition for '{node_name}': {e}") from e

        logger.debug(f"Loaded {nodes_loaded} nodes from {yaml_path}")
        return nodes_loaded

    def get_standard_name(self, name: str) -> str:
        """Get the standard name for a given node name.

        If the name is already standard, returns it unchanged.
        If it's an alternate name, returns the corresponding standard name.
        If it's not recognized, returns the original name.

        Args:
            name: The node name to standardize.

        Returns:
            The standardized node name.
        """
        # Check if it's already a standard name
        if name in self._standard_nodes:
            return name

        # Check if it's an alternate name
        if name in self._alternate_to_standard:
            return self._alternate_to_standard[name]

        # Not recognized, return as-is
        return name

    def is_standard_name(self, name: str) -> bool:
        """Check if a name is a recognized standard node name.

        Args:
            name: The node name to check.

        Returns:
            True if the name is a standard node name, False otherwise.
        """
        return name in self._standard_nodes

    def is_alternate_name(self, name: str) -> bool:
        """Check if a name is a recognized alternate name.

        Args:
            name: The node name to check.

        Returns:
            True if the name is an alternate name, False otherwise.
        """
        return name in self._alternate_to_standard

    def is_recognized_name(self, name: str) -> bool:
        """Check if a name is either standard or alternate.

        Args:
            name: The node name to check.

        Returns:
            True if the name is recognized, False otherwise.
        """
        return self.is_standard_name(name) or self.is_alternate_name(name)

    def get_definition(self, name: str) -> Optional[StandardNodeDefinition]:
        """Get the definition for a node name.

        Works with both standard and alternate names.

        Args:
            name: The node name to look up.

        Returns:
            The node definition if found, None otherwise.
        """
        standard_name = self.get_standard_name(name)
        return self._standard_nodes.get(standard_name)

    def list_standard_names(self, category: Optional[str] = None) -> list[str]:
        """List all standard node names, optionally filtered by category.

        Args:
            category: Optional category to filter by.

        Returns:
            Sorted list of standard node names.
        """
        if category:
            names = [
                name for name, defn in self._standard_nodes.items() if defn.category == category
            ]
        else:
            names = list(self._standard_nodes.keys())

        return sorted(names)

    def list_categories(self) -> list[str]:
        """List all available categories.

        Returns:
            Sorted list of categories.
        """
        return sorted(self._categories)

    def validate_node_name(self, name: str, strict: bool = False) -> tuple[bool, str]:
        """Validate a node name against standards.

        Args:
            name: The node name to validate.
            strict: If True, only standard names are valid.
                   If False, alternate names are also valid.

        Returns:
            Tuple of (is_valid, message).
        """
        if strict:
            if self.is_standard_name(name):
                return True, f"'{name}' is a standard node name"
            elif self.is_alternate_name(name):
                standard = self.get_standard_name(name)
                return (
                    False,
                    f"'{name}' is an alternate name. Use standard name '{standard}'",
                )
            else:
                return False, f"'{name}' is not a recognized node name"
        elif self.is_recognized_name(name):
            if self.is_alternate_name(name):
                standard = self.get_standard_name(name)
                return True, f"'{name}' is valid (alternate for '{standard}')"
            else:
                return True, f"'{name}' is a standard node name"
        else:
            return False, f"'{name}' is not a recognized node name"

    def get_sign_convention(self, name: str) -> Optional[str]:
        """Get the sign convention for a node.

        Args:
            name: The node name (standard or alternate).

        Returns:
            The sign convention ('positive' or 'negative') if found, None otherwise.
        """
        definition = self.get_definition(name)
        return definition.sign_convention if definition else None

    def __len__(self) -> int:
        """Return the number of standard nodes in the registry."""
        return len(self._standard_nodes)


# Global registry instance
standard_node_registry = StandardNodeRegistry()


def load_standard_nodes(yaml_path: Optional[Path] = None) -> None:
    """Load standard nodes into the global registry.

    Args:
        yaml_path: Path to YAML file. If None, uses default location.
    """
    if yaml_path is None:
        # Default location relative to this file
        yaml_path = Path(__file__).parent / "standard_nodes.yaml"

    count = standard_node_registry.load_from_yaml(yaml_path)
    logger.info(f"Loaded {count} standard node definitions")


# NOTE: Auto-loading is disabled to prevent conflicts with organized structure
# The nodes/__init__.py will handle loading from the appropriate source
#
# # Auto-load standard nodes on import if file exists
# default_yaml = Path(__file__).parent / "standard_nodes.yaml"
# if default_yaml.exists():
#     try:
#         load_standard_nodes(default_yaml)
#     except Exception as e:
#         logger.warning(f"Failed to auto-load standard nodes: {e}")
