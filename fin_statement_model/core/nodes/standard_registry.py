"""Registry for standard node names and metadata.

This module provides a registry system for standardized node names,
ensuring consistency across financial models and enabling metrics to work properly.

Features:
    - StandardNodeDefinition: Pydantic model for node metadata (category, subcategory, description, alternate names, sign convention).
    - StandardNodeRegistry: Manages loading, validation, and lookup of standard node definitions.
    - Supports loading from organized YAML files and direct YAML file loading.
    - Provides methods to resolve alternate names, validate names, list categories, and retrieve sign conventions.
    - Used by the financial statement model to ensure canonical naming and robust metric calculation.

Example:
    >>> from fin_statement_model.core.nodes.standard_registry import standard_node_registry
    >>> standard_node_registry.is_standard_name("revenue")
    True
    >>> standard_node_registry.get_standard_name("sales")
    'revenue'
    >>> defn = standard_node_registry.get_definition("revenue")
    >>> defn.category
    'income_statement'
    >>> standard_node_registry.list_standard_names("balance_sheet_assets")[:3]
    ['accounts_receivable', 'cash_and_equivalents', 'current_assets']
    >>> standard_node_registry.get_sign_convention("treasury_stock")
    'negative'
"""

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict
import yaml

logger = logging.getLogger(__name__)


class StandardNodeDefinition(BaseModel):
    """Represent metadata for a standard node definition.

    Attributes:
        category (str): Main category (e.g., 'balance_sheet_assets').
        subcategory (str): Subcategory within the main category.
        description (str): Human-readable description of the node.
        alternate_names (list[str]): Alternate names mapping to this standard.
        sign_convention (str): Sign convention ('positive' or 'negative').

    Example:
        >>> from fin_statement_model.core.nodes.standard_registry import StandardNodeDefinition
        >>> defn = StandardNodeDefinition(
        ...     category="income_statement",
        ...     subcategory="top_line",
        ...     description="Total revenue/sales",
        ...     alternate_names=["sales", "total_revenue"],
        ...     sign_convention="positive",
        ... )
        >>> defn.category
        'income_statement'
        >>> defn.alternate_names
        ['sales', 'total_revenue']
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

    Example:
        >>> from fin_statement_model.core.nodes.standard_registry import StandardNodeRegistry
        >>> reg = StandardNodeRegistry()
        >>> reg._load_nodes_from_data(
        ...     {
        ...         "revenue": {
        ...             "category": "income_statement",
        ...             "subcategory": "top_line",
        ...             "description": "Total revenue",
        ...             "alternate_names": ["sales"],
        ...             "sign_convention": "positive",
        ...         }
        ...     },
        ...     "test",
        ... )
        1
        >>> reg.is_standard_name("revenue")
        True
        >>> reg.get_standard_name("sales")
        'revenue'
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._standard_nodes: dict[str, StandardNodeDefinition] = {}
        self._alternate_to_standard: dict[str, str] = {}
        self._categories: set[str] = set()
        self._initialized: bool = False  # Track initialization state
        self._loaded_from: str | None = None  # Track source

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
            raise TypeError(f"Expected dict at root of {source_description}, got {type(data)}")

        nodes_loaded = 0

        # Load each node definition
        for node_name, node_data in data.items():
            if not isinstance(node_data, dict):
                logger.warning("Skipping invalid node definition '%s' in %s: not a dict", node_name, source_description)
                continue

            try:
                definition = StandardNodeDefinition(**node_data)

                # Handle duplicate standard names
                if node_name in self._standard_nodes:
                    if not overwrite_existing:
                        raise ValueError(f"Duplicate standard node name: {node_name}")
                    else:
                        logger.debug("Overwriting existing standard node: %s from %s", node_name, source_description)

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
                                "Alternate name '%s' already maps to '%s', now mapping to '%s'",
                                alt_name,
                                existing_standard,
                                node_name,
                            )
                    self._alternate_to_standard[alt_name] = node_name

                nodes_loaded += 1

            except Exception as e:
                logger.exception("Error loading node '%s' from %s", node_name, source_description)
                raise ValueError(f"Invalid node definition for '{node_name}': {e}") from e

        return nodes_loaded

    def get_standard_name(self, name: str) -> str:
        """Get the standard name for a given node name.

        If the name is already standard, returns it unchanged.
        If it's an alternate name, returns the corresponding standard name.
        If it's not recognized, returns the original name.

        Args:
            name (str): The node name to standardize.

        Returns:
            str: The standardized node name.

        Example:
            >>> from fin_statement_model.core.nodes.standard_registry import standard_node_registry
            >>> standard_node_registry.get_standard_name("sales")
            'revenue'
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
            name (str): The node name to check.

        Returns:
            bool: True if the name is a standard node name, False otherwise.

        Example:
            >>> from fin_statement_model.core.nodes.standard_registry import standard_node_registry
            >>> standard_node_registry.is_standard_name("revenue")
            True
        """
        return name in self._standard_nodes

    def is_alternate_name(self, name: str) -> bool:
        """Check if a name is a recognized alternate name.

        Args:
            name (str): The node name to check.

        Returns:
            bool: True if the name is an alternate name, False otherwise.

        Example:
            >>> from fin_statement_model.core.nodes.standard_registry import standard_node_registry
            >>> standard_node_registry.is_alternate_name("sales")
            True
        """
        return name in self._alternate_to_standard

    def is_recognized_name(self, name: str) -> bool:
        """Check if a name is either standard or alternate.

        Args:
            name (str): The node name to check.

        Returns:
            bool: True if the name is recognized, False otherwise.

        Example:
            >>> from fin_statement_model.core.nodes.standard_registry import standard_node_registry
            >>> standard_node_registry.is_recognized_name("revenue")
            True
            >>> standard_node_registry.is_recognized_name("sales")
            True
            >>> standard_node_registry.is_recognized_name("not_a_node")
            False
        """
        return self.is_standard_name(name) or self.is_alternate_name(name)

    def get_definition(self, name: str) -> StandardNodeDefinition | None:
        """Get the definition for a node name.

        Works with both standard and alternate names.

        Args:
            name (str): The node name to look up.

        Returns:
            Optional[StandardNodeDefinition]: The node definition if found, None otherwise.

        Example:
            >>> from fin_statement_model.core.nodes.standard_registry import standard_node_registry
            >>> defn = standard_node_registry.get_definition("revenue")
            >>> defn.category
            'income_statement'
        """
        standard_name = self.get_standard_name(name)
        return self._standard_nodes.get(standard_name)

    def list_standard_names(self, category: str | None = None) -> list[str]:
        """List all standard node names, optionally filtered by category.

        Args:
            category (Optional[str]): Optional category to filter by.

        Returns:
            list[str]: Sorted list of standard node names.

        Example:
            >>> from fin_statement_model.core.nodes.standard_registry import standard_node_registry
            >>> standard_node_registry.list_standard_names("balance_sheet_assets")[:3]
            ['accounts_receivable', 'cash_and_equivalents', 'current_assets']
        """
        if category:
            names = [name for name, defn in self._standard_nodes.items() if defn.category == category]
        else:
            names = list(self._standard_nodes.keys())

        return sorted(names)

    def list_categories(self) -> list[str]:
        """List all available categories.

        Returns:
            list[str]: Sorted list of categories.

        Example:
            >>> from fin_statement_model.core.nodes.standard_registry import standard_node_registry
            >>> "income_statement" in standard_node_registry.list_categories()
            True
        """
        return sorted(self._categories)

    def validate_node_name(self, name: str, strict: bool = False) -> tuple[bool, str]:
        """Validate a node name against standards.

        Args:
            name (str): The node name to validate.
            strict (bool): If True, only standard names are valid. If False, alternate names are also valid.

        Returns:
            tuple[bool, str]: Tuple of (is_valid, message).

        Example:
            >>> from fin_statement_model.core.nodes.standard_registry import standard_node_registry
            >>> standard_node_registry.validate_node_name("revenue")
            (True, "'revenue' is a standard node name")
            >>> standard_node_registry.validate_node_name("sales")
            (True, "'sales' is valid (alternate for 'revenue')")
            >>> standard_node_registry.validate_node_name("not_a_node")
            (False, "'not_a_node' is not a recognized node name")
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

    def get_sign_convention(self, name: str) -> str | None:
        """Get the sign convention for a node.

        Args:
            name (str): The node name (standard or alternate).

        Returns:
            Optional[str]: The sign convention ('positive' or 'negative') if found, None otherwise.

        Example:
            >>> from fin_statement_model.core.nodes.standard_registry import standard_node_registry
            >>> standard_node_registry.get_sign_convention("treasury_stock")
            'negative'
        """
        definition = self.get_definition(name)
        return definition.sign_convention if definition else None

    def initialize_default_nodes(
        self,
        organized_path: Path | None = None,
        force_reload: bool = False,
    ) -> int:
        """Load default standard nodes from organized directory.

        Args:
            organized_path (Optional[Path]): Base path to `standard_nodes_defn`. Defaults to package directory.
            force_reload (bool): If True, reload even if already initialized.

        Returns:
            int: Count of nodes loaded.

        Example:
            >>> from fin_statement_model.core.nodes.standard_registry import standard_node_registry
            >>> count = standard_node_registry.initialize_default_nodes()
            >>> count > 0
            True
        """
        if self._initialized and not force_reload:
            logger.debug("Standard nodes already initialized from %s, skipping reload.", self._loaded_from)
            return len(self._standard_nodes)

        if organized_path is None:
            organized_path = Path(__file__).parent / "standard_nodes_defn"

        count = self._load_from_organized_structure(organized_path)
        self._initialized = True
        self._loaded_from = f"organized structure at {organized_path}"
        logger.info("Successfully loaded %s standard nodes from organized structure", count)
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
            raise ValueError(f"Invalid organized structure: missing __init__.py in {base_path}")

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
            raise AttributeError(f"Module at {init_file} missing load_all_standard_nodes function")

    def is_initialized(self) -> bool:
        """Check if the registry has been initialized with default nodes."""
        return self._initialized

    def get_load_source(self) -> str | None:
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

        Example:
            >>> from pathlib import Path
            >>> from fin_statement_model.core.nodes.standard_registry import StandardNodeRegistry
            >>> reg = StandardNodeRegistry()
            >>> # reg.load_from_yaml_file(Path('path/to/file.yaml'))  # doctest: +SKIP
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"Standard nodes file not found: {yaml_path}")

        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {yaml_path}: {e}") from e

        # Process the data without clearing existing
        nodes_loaded = self._load_nodes_from_data(data, str(yaml_path), overwrite_existing=True)
        if nodes_loaded:
            self._initialized = True
            self._loaded_from = str(yaml_path)
        logger.debug("Loaded %s nodes from %s", nodes_loaded, yaml_path)
        return nodes_loaded


# Global registry instance
standard_node_registry = StandardNodeRegistry()


# NOTE: Auto-loading is disabled to prevent conflicts with organized structure
# The nodes/__init__.py will handle loading from the appropriate source
