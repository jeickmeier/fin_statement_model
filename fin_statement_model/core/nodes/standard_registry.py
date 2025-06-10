"""Registry for standard node names.

This module provides a registry system for standardized node names,
ensuring consistency across financial models and enabling metrics to work properly.
"""

import logging
from pathlib import Path
from typing import Any, Optional
import yaml
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class StandardNodeDefinition(BaseModel):
    """Represent metadata for a standard node definition.

    Attributes:
        category (str): Main category (e.g., 'balance_sheet_assets').
        subcategory (str): Subcategory within the main category.
        description (str): Human-readable description of the node.
        alternate_names (list[str]): Alternate names mapping to this standard.
        sign_convention (str): Sign convention ('positive' or 'negative').
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    category: str
    subcategory: str
    description: str
    alternate_names: list[str] = []
    sign_convention: str = "positive"  # 'positive' or 'negative'


class StandardNodeRegistry:
    """Manage loading and access to standard node definitions.

    Provide methods to load definitions, validate node names, and resolve alternate names.

    Attributes:
        _standard_nodes (dict[str, StandardNodeDefinition]): Map standard names to definitions.
        _alternate_to_standard (dict[str, str]): Map alternate names to standard names.
        _categories (set[str]): Registered categories.
        _initialized (bool): Whether default nodes have been initialized.
        _loaded_from (Optional[str]): Source path of loaded definitions.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._standard_nodes: dict[str, StandardNodeDefinition] = {}
        self._alternate_to_standard: dict[str, str] = {}
        self._categories: set[str] = set()
        self._initialized: bool = False  # Track initialization state
        self._loaded_from: Optional[str] = None  # Track source

    def _load_nodes_from_data(
        self,
        data: dict[str, Any],
        source_description: str,
        overwrite_existing: bool = False,
    ) -> int:
        """Load and process node definitions from parsed YAML data.

        Args:
            data (dict[str, Any]): Parsed YAML mapping node names to definitions.
            source_description (str): Description of the data source for logging.
            overwrite_existing (bool): Whether to replace existing definitions.

        Returns:
            int: Number of nodes successfully loaded.

        Raises:
            TypeError: If `data` is not a dict.
            ValueError: If definitions are invalid or duplicates are detected.
        """
        if not isinstance(data, dict):
            raise TypeError(
                f"Expected dict at root of {source_description}, got {type(data)}"
            )

        nodes_loaded = 0

        # Load each node definition
        for node_name, node_data in data.items():
            if not isinstance(node_data, dict):
                logger.warning(
                    f"Skipping invalid node definition '{node_name}' "
                    f"in {source_description}: not a dict"
                )
                continue

            try:
                definition = StandardNodeDefinition(**node_data)

                # Handle duplicate standard names
                if node_name in self._standard_nodes:
                    if not overwrite_existing:
                        raise ValueError(f"Duplicate standard node name: {node_name}")
                    else:
                        logger.debug(
                            f"Overwriting existing standard node: {node_name} "
                            f"from {source_description}"
                        )

                # Add to main registry
                self._standard_nodes[node_name] = definition
                self._categories.add(definition.category)

                # Map alternate names
                for alt_name in definition.alternate_names:
                    if alt_name in self._alternate_to_standard:
                        existing_standard = self._alternate_to_standard[alt_name]
                        if not overwrite_existing and existing_standard != node_name:
                            raise ValueError(
                                f"Alternate name '{alt_name}' already maps to "
                                f"'{existing_standard}', cannot also map to '{node_name}'"
                            )
                        elif overwrite_existing and existing_standard != node_name:
                            logger.debug(
                                f"Alternate name '{alt_name}' already maps to "
                                f"'{existing_standard}', now mapping to '{node_name}'"
                            )
                    self._alternate_to_standard[alt_name] = node_name

                nodes_loaded += 1

            except Exception as e:
                logger.exception(
                    f"Error loading node '{node_name}' from {source_description}"
                )
                raise ValueError(
                    f"Invalid node definition for '{node_name}': {e}"
                ) from e

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
                name
                for name, defn in self._standard_nodes.items()
                if defn.category == category
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

    def initialize_default_nodes(
        self,
        organized_path: Optional[Path] = None,
        force_reload: bool = False,
    ) -> int:
        """Load default standard nodes from organized directory.

        Args:
            organized_path (Path | None): Base path to `standard_nodes_defn`. Defaults to package directory.
            force_reload (bool): If True, reload even if already initialized.

        Returns:
            int: Count of nodes loaded.
        """
        if self._initialized and not force_reload:
            logger.debug(
                f"Standard nodes already initialized from {self._loaded_from}, skipping reload."
            )
            return len(self._standard_nodes)

        if organized_path is None:
            organized_path = Path(__file__).parent / "standard_nodes_defn"

        count = self._load_from_organized_structure(organized_path)
        self._initialized = True
        self._loaded_from = f"organized structure at {organized_path}"
        logger.info(
            f"Successfully loaded {count} standard nodes from organized structure"
        )
        return count

    def _load_from_organized_structure(self, base_path: Path) -> int:
        """Load standard nodes from an organized directory structure.

        Args:
            base_path (Path): Directory containing organized YAML node definition files.

        Returns:
            int: Number of nodes loaded.

        Raises:
            FileNotFoundError: If `base_path` does not exist.
            ImportError: If module loading fails.
            Exception: For other loading errors.
        """
        if not base_path.exists():
            raise FileNotFoundError(f"Organized structure path not found: {base_path}")

        # Check if it has the expected structure (contains __init__.py)
        init_file = base_path / "__init__.py"
        if not init_file.exists():
            raise ValueError(
                f"Invalid organized structure: missing __init__.py in {base_path}"
            )

        # Import and use the load_all_standard_nodes function
        import importlib.util

        spec = importlib.util.spec_from_file_location("standard_nodes_defn", init_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to load module from {init_file}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Clear existing data before loading
        self._standard_nodes.clear()
        self._alternate_to_standard.clear()
        self._categories.clear()

        # Call the loading function
        if hasattr(module, "load_all_standard_nodes"):
            loaded_count = module.load_all_standard_nodes(base_path)
            return int(loaded_count)
        else:
            raise AttributeError(
                f"Module at {init_file} missing load_all_standard_nodes function"
            )

    def is_initialized(self) -> bool:
        """Check if the registry has been initialized with default nodes."""
        return self._initialized

    def get_load_source(self) -> Optional[str]:
        """Get the source from which nodes were loaded."""
        return self._loaded_from

    def reload(self) -> int:
        """Force reload of standard nodes."""
        return self.initialize_default_nodes(force_reload=True)

    def __len__(self) -> int:
        """Return the number of standard nodes in the registry."""
        return len(self._standard_nodes)

    def load_from_yaml_file(self, yaml_path: Path) -> int:
        """Load standard node definitions from a YAML file.

        Does not clear existing definitions before loading.

        Args:
            yaml_path (Path): Path to the YAML file with node definitions.

        Returns:
            int: Number of nodes loaded from the file.

        Raises:
            FileNotFoundError: If `yaml_path` does not exist.
            ValueError: If YAML is invalid or structure is incorrect.
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"Standard nodes file not found: {yaml_path}")

        try:
            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {yaml_path}: {e}") from e

        # Process the data without clearing existing
        nodes_loaded = self._load_nodes_from_data(
            data, str(yaml_path), overwrite_existing=True
        )
        if nodes_loaded:
            self._initialized = True
            self._loaded_from = str(yaml_path)
        logger.debug(f"Loaded {nodes_loaded} nodes from {yaml_path}")
        return nodes_loaded


# Global registry instance
standard_node_registry = StandardNodeRegistry()


# NOTE: Auto-loading is disabled to prevent conflicts with organized structure
# The nodes/__init__.py will handle loading from the appropriate source
