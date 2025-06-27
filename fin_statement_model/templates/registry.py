"""Filesystem-backed Template Registry for Financial Statement Models.

The TemplateRegistry provides a local, persistent storage solution for financial
statement templates with built-in versioning, integrity checking, and powerful
instantiation capabilities. Templates are stored as JSON bundles on the local
filesystem with automatic indexing for fast discovery.

Core Features:
    - **Local Storage**: Templates stored in user's home directory with secure permissions
    - **Automatic Versioning**: Semantic version management with auto-increment
    - **Integrity Verification**: SHA-256 checksums prevent data corruption
    - **Template Instantiation**: Clone templates with customizations (periods, node renaming)
    - **Diff Analysis**: Compare templates structurally and numerically
    - **Forecasting Integration**: Automatic application of forecast specifications
    - **Preprocessing Support**: Built-in data transformation pipeline execution

Registry Structure:
    ```
    ~/.fin_statement_model/templates/
    ├── index.json                    # Fast lookup index
    └── store/                        # Template storage
        ├── lbo.standard/
        │   ├── v1/
        │   │   └── bundle.json       # Template bundle
        │   └── v2/
        │       └── bundle.json
        └── real_estate_lending/
            └── v3/
                └── bundle.json
    ```

Basic Usage:
    >>> from fin_statement_model.templates import TemplateRegistry
    >>> 
    >>> # List available templates
    >>> templates = TemplateRegistry.list()
    >>> print(templates)  # ['lbo.standard_v1', 'real_estate_lending_v3']
    >>> 
    >>> # Instantiate a template
    >>> graph = TemplateRegistry.instantiate('lbo.standard_v1')
    >>> print(f"Graph: {len(graph.nodes)} nodes, {len(graph.periods)} periods")
    >>> 
    >>> # Register a custom template
    >>> template_id = TemplateRegistry.register_graph(
    ...     my_graph, 
    ...     name="custom.model",
    ...     meta={"category": "custom", "description": "My model"}
    ... )

Advanced Usage:
    >>> # Compare templates
    >>> diff_result = TemplateRegistry.diff('lbo.standard_v1', 'custom.model_v1')
    >>> print(f"Structural changes: {len(diff_result.structure.added_nodes)} added")
    >>> 
    >>> # Instantiate with customizations
    >>> customized = TemplateRegistry.instantiate(
    ...     'lbo.standard_v1',
    ...     periods=['2029', '2030'],                    # Add extra periods
    ...     rename_map={'Revenue': 'TotalRevenue'}       # Rename nodes
    ... )

Environment Configuration:
    Set ``FSM_TEMPLATES_PATH`` environment variable to customize the registry location:
    ```bash
    export FSM_TEMPLATES_PATH=/path/to/custom/templates
    ```

Security Notes:
    - Registry directory created with 0700 permissions (user-only access)
    - Template bundles stored with 0600 permissions (user read/write only)
    - SHA-256 checksums verify template integrity on load
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
import json
import logging
import os
from pathlib import Path
import tempfile
import threading  # thread-safety
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:  # pragma: no cover
    import builtins

    from fin_statement_model.core.graph import Graph


from fin_statement_model.io import write_data
from fin_statement_model.templates.models import (
    DiffResult,
    ForecastSpec,
    PreprocessingSpec,
    TemplateBundle,
    TemplateMeta,
    _calculate_sha256_checksum,
)

logger = logging.getLogger(__name__)

__all__: list[str] = [
    "TemplateRegistry",
]

_INDEX_LOCK = threading.Lock()  # process-level lock safeguarding index writes


class TemplateRegistry:
    """Local filesystem-backed registry for financial statement templates.

    A singleton-style class providing centralized template storage, versioning,
    and retrieval. Templates are persisted as JSON bundles with automatic
    indexing for efficient discovery and integrity verification.

    The registry supports the complete template lifecycle:
    - Registration of new templates with automatic versioning
    - Retrieval and instantiation of stored templates  
    - Comparison between different template versions
    - Deletion and cleanup of obsolete templates

    All operations are thread-safe and atomic where possible to support
    concurrent access patterns.

    Class Attributes:
        _ENV_VAR: Environment variable name for custom registry path
        _INDEX_FILE: Name of the JSON index file
        _STORE_DIR: Directory name for template storage

    Example:
        >>> # Basic registry operations
        >>> templates = TemplateRegistry.list()
        >>> bundle = TemplateRegistry.get('lbo.standard_v1')
        >>> graph = TemplateRegistry.instantiate('lbo.standard_v1')
        >>> 
        >>> # Register new template
        >>> template_id = TemplateRegistry.register_graph(
        ...     my_graph,
        ...     name="custom.model"
        ... )

    Note:
        The registry creates secure storage with restrictive permissions
        (0700 for directories, 0600 for files) to protect potentially
        sensitive financial data.
    """

    _ENV_VAR: str = "FSM_TEMPLATES_PATH"
    _INDEX_FILE: str = "index.json"
    _STORE_DIR: str = "store"

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    @classmethod
    def _registry_root(cls) -> Path:
        """Determine and create the root directory for template storage.

        Follows a precedence order for locating the registry:
        1. Environment variable FSM_TEMPLATES_PATH (if set)
        2. Default: ~/.fin_statement_model/templates

        The directory is created with secure permissions (0700) on first access
        to ensure private storage of potentially sensitive financial data.

        Returns:
            Absolute path to the registry root directory

        Example:
            >>> root = TemplateRegistry._registry_root()
            >>> print(root)  # /home/user/.fin_statement_model/templates
            >>> root.exists()
            True
        """
        custom = os.getenv(cls._ENV_VAR)
        root = Path(custom).expanduser().resolve() if custom else Path.home() / ".fin_statement_model" / "templates"
        # `mkdir` is no-op if the directory already exists.
        root.mkdir(parents=True, exist_ok=True)
        try:
            root.chmod(0o700)
        except PermissionError:  # pragma: no cover - best effort on non-POSIX
            logger.debug("Unable to set registry root permissions; continuing anyway.")
        return root

    @classmethod
    def _index_path(cls) -> Path:
        """Return the absolute path to the registry index file.

        Returns:
            Path to index.json within the registry root

        Example:
            >>> index_path = TemplateRegistry._index_path()
            >>> print(index_path.name)
            'index.json'
        """
        return cls._registry_root() / cls._INDEX_FILE

    # ------------------------------------------------------------------
    # Index helpers
    # ------------------------------------------------------------------
    @classmethod
    def _load_index(cls) -> MutableMapping[str, str]:
        """Load the registry index from disk.

        Reads the JSON index file mapping template IDs to relative bundle paths.
        Returns an empty mapping if the index doesn't exist or is corrupted.

        Returns:
            Mutable mapping of template_id → relative_bundle_path

        Example:
            >>> index = TemplateRegistry._load_index()
            >>> print(index)  # {'lbo.standard_v1': 'store/lbo/standard/v1/bundle.json'}
        """
        idx_path = cls._index_path()
        if not idx_path.exists():
            return {}
        try:
            with idx_path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise TypeError("Registry index JSON must be an object mapping template_id→relative_path.")
        except Exception:  # pragma: no cover - defensive, should never occur in tests
            logger.exception("Failed to parse registry index - resetting to empty.")
            return {}
        else:
            return data

    @classmethod
    def _atomic_write(cls, target: Path, payload: str) -> None:
        """Atomically write text payload to target path with secure permissions.

        Uses a temporary file in the same directory followed by atomic rename
        to ensure the write operation is either fully completed or has no effect.
        Sets restrictive permissions (0600) for security.

        Args:
            target: Destination file path
            payload: Text content to write

        Example:
            >>> content = '{"template": "data"}'
            >>> TemplateRegistry._atomic_write(Path("/tmp/test.json"), content)
        """
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=str(target.parent), delete=False, encoding="utf-8") as tmp:
            tmp.write(payload)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)
        try:
            tmp_path.chmod(0o600)
        except PermissionError:  # pragma: no cover
            logger.debug("Unable to set permissions on temp file; continuing anyway.")
        # `Path.replace` is atomic on POSIX and Windows (NTFS)
        tmp_path.replace(target)

    @classmethod
    def _save_index(cls, index: Mapping[str, str]) -> None:
        """Persist the registry index to disk atomically.

        Args:
            index: Template ID to relative path mapping

        Example:
            >>> index = {"my_template_v1": "store/my/template/v1/bundle.json"}
            >>> TemplateRegistry._save_index(index)
        """
        payload = json.dumps(index, indent=2, sort_keys=True)
        cls._atomic_write(cls._index_path(), payload)

    # ------------------------------------------------------------------
    # Public helper - deletion (used by install_builtin_templates overwrite)
    # ------------------------------------------------------------------
    @classmethod
    def delete(cls, template_id: str) -> None:
        """Remove a template from the registry permanently.

        Deletes both the template bundle file and its index entry. The operation
        is destructive and cannot be undone. Silently ignores unknown template IDs
        to support idempotent cleanup scenarios.

        Args:
            template_id: Template identifier to delete (e.g., "lbo.standard_v1")

        Example:
            >>> TemplateRegistry.delete('old_template_v1')  # Removes completely
            >>> TemplateRegistry.delete('nonexistent')      # Silently ignored

        Note:
            The function also attempts to clean up empty parent directories
            after deletion to maintain a tidy registry structure.
        """
        with _INDEX_LOCK:
            index = cls._load_index()
            rel_path = index.pop(template_id, None)
            if rel_path is None:
                logger.debug("Template '%s' not found - nothing to delete.", template_id)
                cls._save_index(index)
                return

            # Delete bundle JSON (ignore if already gone)
            try:
                abs_path = cls._resolve_bundle_path(rel_path)
                if abs_path.exists():
                    abs_path.unlink()
                    # Remove now-empty parent directories up to registry root
                    for parent in abs_path.parent.parents:
                        try:
                            parent.rmdir()
                        except OSError:
                            break  # not empty - stop ascent
                        if parent == cls._registry_root():
                            break
            except Exception:  # pragma: no cover - cautious cleanup
                logger.exception("Failed to remove bundle for '%s'", template_id)
            finally:
                cls._save_index(index)

    # ------------------------------------------------------------------
    # Path validation helpers
    # ------------------------------------------------------------------
    @classmethod
    def _resolve_bundle_path(cls, rel: str | Path) -> Path:
        """Resolve relative bundle path to absolute path with security validation.

        Converts relative paths from the index to absolute filesystem paths while
        defending against directory traversal attacks. Rejects paths that attempt
        to escape the registry root directory.

        Args:
            rel: Relative path from registry index

        Returns:
            Validated absolute path within registry root

        Raises:
            ValueError: If path is absolute, contains traversal components (..), 
                or resolves outside the registry root

        Example:
            >>> path = TemplateRegistry._resolve_bundle_path("store/lbo/standard/v1/bundle.json")
            >>> print(path.is_absolute())
            True
            >>> path.relative_to(TemplateRegistry._registry_root())  # Validates containment
            PosixPath('store/lbo/standard/v1/bundle.json')
        """
        rel_path = Path(rel)
        # Reject absolute paths outright
        if rel_path.is_absolute():
            raise ValueError("Registry index contains absolute bundle path - potential security risk.")
        # Reject parent directory traversal ("..") components
        if any(part == ".." for part in rel_path.parts):
            raise ValueError("Registry index contains path traversal components (..).")

        root = cls._registry_root().resolve()
        abs_path = (root / rel_path).resolve()
        try:
            abs_path.relative_to(root)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError("Resolved bundle path escapes registry root.") from exc
        return abs_path

    # ------------------------------------------------------------------
    # Public API - foundational subset (list / register / get)
    # ------------------------------------------------------------------
    @classmethod
    def list(cls) -> list[str]:
        """List all registered template identifiers.

        Returns:
            Sorted list of template IDs in the registry

        Example:
            >>> templates = TemplateRegistry.list()
            >>> print(templates)
            ['lbo.standard_v1', 'real_estate_lending_v3', 'custom.model_v1']
            >>> 
            >>> # Check if specific template exists
            >>> if 'lbo.standard_v1' in TemplateRegistry.list():
            ...     print("LBO template available")
        """
        return sorted(cls._load_index())

    @classmethod
    def _resolve_next_version(cls, name: str, existing_index: Mapping[str, str]) -> str:
        """Calculate the next semantic version for a template name.

        Scans existing template IDs with the same name prefix to determine
        the next available version number in the v<N> format.

        Args:
            name: Template name (e.g., "lbo.standard")
            existing_index: Current registry index

        Returns:
            Next version string (e.g., "v2", "v3")

        Example:
            >>> # Assuming lbo.standard_v1 and lbo.standard_v2 exist
            >>> next_ver = TemplateRegistry._resolve_next_version(
            ...     "lbo.standard", 
            ...     {"lbo.standard_v1": "path1", "lbo.standard_v2": "path2"}
            ... )
            >>> print(next_ver)  # "v3"
        """
        prefix = f"{name}_v"
        max_ver = 0
        for key in existing_index:
            if key.startswith(prefix):
                try:
                    candidate = int(key[len(prefix) :])
                    max_ver = max(max_ver, candidate)
                except ValueError:
                    continue
        return f"v{max_ver + 1}"

    @classmethod
    def register_graph(
        cls,
        graph: Graph,
        *,
        name: str,
        version: str | None = None,
        meta: Mapping[str, Any] | None = None,
        forecast: ForecastSpec | None = None,
        preprocessing: PreprocessingSpec | None = None,
    ) -> str:
        """Register a financial statement graph as a reusable template.

        Serializes the graph and stores it in the registry with metadata,
        optional forecasting configuration, and preprocessing pipeline.
        Automatically calculates version numbers if not specified.

        Args:
            graph: Graph instance to persist as a template
            name: Template name (e.g., "lbo.standard", "real_estate.construction")
            version: Explicit version string ("v1", "v2"). If None, automatically
                calculates the next available version
            meta: Additional metadata fields. Standard fields (name, version, category)
                are set automatically and override any duplicates in meta
            forecast: Optional declarative forecasting specification
            preprocessing: Optional data transformation pipeline

        Returns:
            Complete template identifier (e.g., "lbo.standard_v1")

        Raises:
            TypeError: If name is not a non-empty string
            ValueError: If template_id already exists in registry
            OSError: If filesystem operations fail

        Example:
            >>> # Basic registration with auto-versioning
            >>> template_id = TemplateRegistry.register_graph(
            ...     my_graph,
            ...     name="custom.model",
            ...     meta={"description": "Custom financial model", "category": "custom"}
            ... )
            >>> print(template_id)  # "custom.model_v1"
            >>> 
            >>> # Registration with forecasting
            >>> from fin_statement_model.templates.models import ForecastSpec
            >>> forecast_spec = ForecastSpec(
            ...     periods=["2027", "2028"],
            ...     node_configs={"Revenue": {"method": "simple", "config": 0.1}}
            ... )
            >>> template_id = TemplateRegistry.register_graph(
            ...     my_graph,
            ...     name="forecast.model",
            ...     forecast=forecast_spec
            ... )

        Note:
            The graph is deep-cloned during serialization to ensure the stored
            template is independent of the original graph instance. Template
            bundles include SHA-256 checksums for integrity verification.
        """
        if not name or not isinstance(name, str):
            raise TypeError("Template name must be a non-empty string.")

        with _INDEX_LOCK:
            index = cls._load_index()
            if version is None:
                version = cls._resolve_next_version(name, index)

            template_id = f"{name}_{version}"
            if template_id in index:
                raise ValueError(f"Template '{template_id}' already exists.")

            # ------------------------------------------------------------------
            # Build filesystem path (store/<name>/<version>/bundle.json)
            # ------------------------------------------------------------------
            rel_path = Path(cls._STORE_DIR) / Path(*name.split(".")) / version / "bundle.json"
            bundle_path = cls._registry_root() / rel_path
            bundle_path.parent.mkdir(parents=True, exist_ok=True)

            # ------------------------------------------------------------------
            # Serialize graph ➜ dict ➜ TemplateBundle ➜ JSON
            # ------------------------------------------------------------------
            graph_dict = cast("dict[str, Any]", write_data("graph_definition_dict", graph, target=None))
            checksum = _calculate_sha256_checksum(graph_dict)

            meta_payload: dict[str, Any] = {
                "name": name,
                "version": version,
                "category": meta.get("category") if meta else name.split(".")[0],
            }
            if meta:
                meta_payload.update(meta)

            bundle = TemplateBundle(
                meta=TemplateMeta.model_validate(meta_payload),
                graph_dict=graph_dict,
                checksum=checksum,
                forecast=forecast,
                preprocessing=preprocessing,
            )
            payload = json.dumps(bundle.model_dump(mode="json"), indent=2)

            # Atomic write of bundle then update index
            cls._atomic_write(bundle_path, payload)

            # Update index in-memory and persist
            index[template_id] = rel_path.as_posix()
            cls._save_index(index)

            logger.info("Registered template '%s' (path=%s)", template_id, bundle_path)
            return template_id

    @classmethod
    def get(cls, template_id: str) -> TemplateBundle:
        """Retrieve a template bundle by identifier.

        Loads and validates the stored template bundle from disk, including
        checksum verification to ensure data integrity.

        Args:
            template_id: Template identifier (e.g., "lbo.standard_v1")

        Returns:
            Validated TemplateBundle instance

        Raises:
            KeyError: If template_id is not found in registry
            ValueError: If bundle checksum validation fails
            OSError: If bundle file cannot be read

        Example:
            >>> bundle = TemplateRegistry.get('lbo.standard_v1')
            >>> print(f"Template: {bundle.meta.name} v{bundle.meta.version}")
            >>> print(f"Category: {bundle.meta.category}")
            >>> print(f"Checksum: {bundle.checksum[:8]}...")
            >>> 
            >>> # Access graph structure
            >>> graph_dict = bundle.graph_dict
            >>> periods = graph_dict.get('periods', [])
            >>> nodes = graph_dict.get('nodes', {})
        """
        index = cls._load_index()
        try:
            rel = index[template_id]
        except KeyError as exc:  # pragma: no cover - explicit failure expected in tests
            raise KeyError(f"Template '{template_id}' not found in registry.") from exc
        bundle_path = cls._resolve_bundle_path(rel)
        with bundle_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return TemplateBundle.model_validate(data)

    # ------------------------------------------------------------------
    # Public API - instantiation (clone + optional transforms)
    # ------------------------------------------------------------------
    @classmethod
    def instantiate(  # noqa: C901
        cls,
        template_id: str,
        *,
        periods: builtins.list[str] | None = None,
        rename_map: Mapping[str, str] | None = None,
    ) -> Graph:
        """Create a working graph instance from a stored template.

        Loads the template bundle, reconstructs the graph, applies any embedded
        forecast and preprocessing specifications, and optionally customizes
        the result with additional periods and node renaming.

        Args:
            template_id: Template identifier (e.g., "lbo.standard_v1")
            periods: Additional periods to append to the graph. Existing periods
                are preserved; duplicates are ignored
            rename_map: Node renaming mapping (old_name → new_name). Maintains
                all calculation relationships and edge connections

        Returns:
            Independent Graph instance ready for analysis and modification

        Raises:
            KeyError: If template_id is not found or old node names don't exist
            TypeError: If periods or rename_map have incorrect types
            ValueError: If rename target names already exist in the graph

        Example:
            >>> # Basic instantiation
            >>> graph = TemplateRegistry.instantiate('lbo.standard_v1')
            >>> revenue_2024 = graph.calculate('Revenue', '2024')
            >>> 
            >>> # Instantiation with customizations
            >>> custom_graph = TemplateRegistry.instantiate(
            ...     'lbo.standard_v1',
            ...     periods=['2029', '2030'],               # Add forecast periods
            ...     rename_map={                            # Rename nodes
            ...         'Revenue': 'TotalRevenue',
            ...         'COGS': 'DirectCosts'
            ...     }
            ... )
            >>> 
            >>> # Verify customizations
            >>> print(custom_graph.periods)  # Includes 2029, 2030
            >>> print('TotalRevenue' in custom_graph.nodes)  # True
            >>> print('Revenue' in custom_graph.nodes)       # False

        Template Processing Order:
            1. Load template bundle and reconstruct base graph
            2. Apply embedded forecast specification (if present)
            3. Deep clone for independence from registry caches
            4. Add additional periods (if specified)
            5. Apply node renaming (if specified) 
            6. Apply preprocessing pipeline (if embedded)
            7. Clear caches and return clean graph

        Note:
            The returned graph is completely independent of the template registry
            and can be modified without affecting the stored template. All
            forecasting and preprocessing happens automatically based on the
            template's embedded specifications.
        """
        # ------------------------------------------------------------------
        # 1. Load bundle & re-construct Graph via IO facade
        # ------------------------------------------------------------------
        bundle = cls.get(template_id)

        from fin_statement_model.io import read_data

        graph = read_data("graph_definition_dict", bundle.graph_dict)

        # ------------------------------------------------------------------
        # 1b. Apply forecast recipe if present
        # ------------------------------------------------------------------
        if bundle.forecast is not None:
            try:
                from fin_statement_model.forecasting import StatementForecaster

                fc = StatementForecaster(graph)
                fc.create_forecast(
                    forecast_periods=bundle.forecast.periods,
                    node_configs=bundle.forecast.node_configs,
                )
            except Exception:
                logger.exception("Failed to apply forecast for template '%s'", template_id)
                raise

        # ------------------------------------------------------------------
        # 2. Deep-clone to decouple from in-memory caches (safety & perf)
        # ------------------------------------------------------------------
        graph = graph.clone(deep=True)

        # ------------------------------------------------------------------
        # 3. Extend periods if requested
        # ------------------------------------------------------------------
        if periods:
            if not isinstance(periods, list):
                raise TypeError("'periods' must be a list of strings if provided.")
            graph.add_periods([p for p in periods if p not in graph.periods])

        # ------------------------------------------------------------------
        # 4. Apply node renames - maintain edge wiring
        # ------------------------------------------------------------------
        if rename_map:
            if not isinstance(rename_map, Mapping):
                raise TypeError("'rename_map' must be a mapping of old→new node IDs.")

            # Basic validations -------------------------------------------------
            for old_name, new_name in rename_map.items():
                if old_name not in graph.nodes:
                    raise KeyError(f"Node '{old_name}' not found in graph - cannot rename.")
                if new_name in graph.nodes:
                    raise ValueError(f"Target node name '{new_name}' already exists in graph.")

            # Perform the rename ------------------------------------------------
            for old_name, new_name in rename_map.items():
                node = graph.nodes.pop(old_name)
                node.name = new_name
                graph.nodes[new_name] = node

            # Refresh calculation nodes' input references ----------------------
            try:
                graph.manipulator._update_calculation_nodes()  # pylint: disable=protected-access
            except AttributeError:
                # Fallback - update input_names manually where present
                for nd in graph.nodes.values():
                    if hasattr(nd, "input_names") and isinstance(nd.input_names, list):
                        nd.input_names = [rename_map.get(n, n) for n in nd.input_names]

        # ------------------------------------------------------------------
        # 5. Apply preprocessing pipeline if declared
        # ------------------------------------------------------------------
        if bundle.preprocessing is not None:
            try:
                from fin_statement_model.preprocessing.utils import apply_pipeline_to_graph

                apply_pipeline_to_graph(graph, bundle.preprocessing, in_place=True)
            except Exception:
                logger.exception("Failed to apply preprocessing for template '%s'", template_id)
                raise

        # Clear caches again to ensure a clean state after preprocessing
        graph.clear_all_caches()

        logger.info(
            "Instantiated template '%s' as graph - periods=%s, rename_map=%s",
            template_id,
            periods,
            rename_map,
        )

        return graph

    # ------------------------------------------------------------------
    # Public API - diffing
    # ------------------------------------------------------------------
    @classmethod
    def diff(
        cls,
        template_id_a: str,
        template_id_b: str,
        *,
        include_values: bool = True,
        periods: builtins.list[str] | None = None,
        atol: float = 1e-9,
    ) -> DiffResult:
        """Compare two registered templates for structural and value differences.

        Loads both templates, reconstructs their graphs (including forecast
        application), and performs comprehensive comparison analysis. Useful
        for understanding evolution between template versions or comparing
        different modeling approaches.

        Args:
            template_id_a: Base template identifier (left-hand side of comparison)
            template_id_b: Target template identifier (right-hand side of comparison)
            include_values: Whether to include numerical value comparison in
                addition to structural analysis. Set False for faster topology-only diffs
            periods: Specific periods to compare. If None, uses intersection of
                periods from both templates
            atol: Absolute tolerance for value comparison. Differences below this
                threshold are considered equal and excluded from results

        Returns:
            DiffResult containing:
                - structure: Structural differences (added/removed/changed nodes)
                - values: Numerical differences (only if include_values=True)

        Raises:
            KeyError: If either template_id is not found in registry

        Example:
            >>> # Compare template versions
            >>> diff_result = TemplateRegistry.diff(
            ...     'lbo.standard_v1', 
            ...     'lbo.standard_v2',
            ...     include_values=True
            ... )
            >>> 
            >>> # Analyze structural changes
            >>> structure = diff_result.structure
            >>> print(f"Added nodes: {structure.added_nodes}")
            >>> print(f"Removed nodes: {structure.removed_nodes}")
            >>> print(f"Changed nodes: {list(structure.changed_nodes.keys())}")
            >>> 
            >>> # Analyze value changes (if enabled)
            >>> if diff_result.values:
            ...     values = diff_result.values
            ...     print(f"Changed cells: {len(values.changed_cells)}")
            ...     print(f"Max delta: ${values.max_delta:,.2f}")
            >>> 
            >>> # Compare specific periods with tolerance
            >>> focused_diff = TemplateRegistry.diff(
            ...     'template_a_v1',
            ...     'template_b_v1', 
            ...     periods=['2024', '2025'],
            ...     atol=1.0  # Ignore sub-dollar differences
            ... )

        Processing Details:
            Both templates are loaded and their embedded forecast specifications
            are applied to create fully-realized graphs before comparison. This
            ensures the diff reflects the complete template behavior, not just
            the base graph structure.

        Performance Notes:
            - Structure comparison is always fast (O(N) in number of nodes)
            - Value comparison can be expensive for large graphs/many periods
            - Use include_values=False when only topology matters
            - Specify focused period lists for faster value comparison
        """
        # Lazy import to avoid heavyweight dependencies on registry import
        from fin_statement_model.io import read_data
        from fin_statement_model.templates import diff as _diff_helpers

        # ------------------------------------------------------------------
        # Re-hydrate both graphs via IO facade (no mutation - read-only path)
        # ------------------------------------------------------------------
        bundle_a = cls.get(template_id_a)
        bundle_b = cls.get(template_id_b)

        graph_a = read_data("graph_definition_dict", bundle_a.graph_dict)
        graph_b = read_data("graph_definition_dict", bundle_b.graph_dict)

        # Apply forecast recipes when present so diff works on fully realised graphs
        from fin_statement_model.forecasting import StatementForecaster

        for graph, bundle in ((graph_a, bundle_a), (graph_b, bundle_b)):
            if bundle.forecast is not None:
                try:
                    fc = StatementForecaster(graph)
                    fc.create_forecast(
                        forecast_periods=bundle.forecast.periods,
                        node_configs=bundle.forecast.node_configs,
                    )
                except Exception:  # pragma: no cover
                    logger.exception(
                        "Failed to apply forecast while diffing templates '%s' and '%s'", template_id_a, template_id_b
                    )
                    raise

        # Deep clone to avoid accidental shared caches / state
        graph_a = graph_a.clone(deep=True)
        graph_b = graph_b.clone(deep=True)

        # ------------------------------------------------------------------
        # Delegate to diff helpers
        # ------------------------------------------------------------------
        result = _diff_helpers.diff(
            graph_a,
            graph_b,
            include_values=include_values,
            periods=periods,
            atol=atol,
        )

        logger.info(
            "Diff between '%s' and '%s' - added=%d removed=%d changed=%d value_cells=%d",
            template_id_a,
            template_id_b,
            len(result.structure.added_nodes),
            len(result.structure.removed_nodes),
            len(result.structure.changed_nodes),
            0 if result.values is None else len(result.values.changed_cells),
        )

        return result
