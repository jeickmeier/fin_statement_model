"""Filesystem-backed Template Registry implementation.

This module provides a minimal, *local-only* registry that can:
1. Persist a :class:`~fin_statement_model.core.graph.Graph` to disk as a
   :class:`~fin_statement_model.templates.models.TemplateBundle`.
2. Maintain a JSON index for quick discovery.
3. Retrieve previously registered bundles.

It purposefully **does not** implement cloning, diffing or remote storage - these
features will be introduced in later roadmap PRs.
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
from importlib import import_module

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
from fin_statement_model.templates.backends import FileSystemStorageBackend, StorageBackend

logger = logging.getLogger(__name__)

__all__: list[str] = [
    "TemplateRegistry",
]

_INDEX_LOCK = threading.Lock()  # process-level lock safeguarding index writes

# ---------------------------------------------------------------------------
# Backend resolution helpers (defined *before* TemplateRegistry so it can be
# referenced by class-level attributes).
# ---------------------------------------------------------------------------

def _resolve_backend_from_env() -> StorageBackend:
    """Return backend instance implied by *FSM_TEMPLATES_BACKEND* env-var.

    Falls back to :class:`FileSystemStorageBackend` if the variable is unset or
    cannot be resolved.
    """
    path = os.getenv("FSM_TEMPLATES_BACKEND")
    if not path:
        return FileSystemStorageBackend()

    try:
        module_path, cls_name = path.rsplit(".", 1)
        module = import_module(module_path)
        backend_cls = getattr(module, cls_name)
        if not isinstance(backend_cls, type) or not issubclass(backend_cls, StorageBackend):  # type: ignore[arg-type]
            raise TypeError
    except Exception as exc:  # pragma: no cover – fallback on any error
        logger.exception(
            "Failed to import storage backend '%s': %s – falling back to file-system backend.",
            path,
            exc,
        )
        return FileSystemStorageBackend()
    else:
        return backend_cls()

class TemplateRegistry:
    """Local filesystem-backed template registry (singleton-style class)."""

    _ENV_VAR: str = "FSM_TEMPLATES_PATH"
    _INDEX_FILE: str = "index.json"
    _STORE_DIR: str = "store"

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    @classmethod
    def _registry_root(cls) -> Path:
        """Return the root directory used to persist registry data.

        Precedence order:
        1. Environment variable ``FSM_TEMPLATES_PATH`` (absolute or relative).
        2. ``~/.fin_statement_model/templates`` default.
        The directory is created on first access with POSIX permissions ``0700``
        to ensure private storage of potentially sensitive financial data.
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
        return cls._registry_root() / cls._INDEX_FILE

    # ------------------------------------------------------------------
    # Index helpers
    # ------------------------------------------------------------------
    @classmethod
    def _load_index(cls) -> MutableMapping[str, str]:
        """Load registry index from disk or return empty mapping."""
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
        """Atomically write *payload* text to *target* path (600 perms)."""
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
        """Persist *index* mapping atomically."""
        payload = json.dumps(index, indent=2, sort_keys=True)
        cls._atomic_write(cls._index_path(), payload)

    # ------------------------------------------------------------------
    # Public helper - deletion (used by install_builtin_templates overwrite)
    # ------------------------------------------------------------------
    @classmethod
    def _legacy_delete(cls, template_id: str) -> None:  # noqa: D401 – retained for backward-compat private use
        """Legacy file-system specific delete implementation (unused after refactor).

        Silently ignores unknown *template_id* so callers may blindly attempt
        deletion.  The operation is **destructive** - the bundle file is
        unlinked.  Errors are logged but not raised to avoid cascading
        failures during best-effort clean-up scenarios (e.g. reinstall).
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
        """Return absolute *bundle* path ensuring it remains within registry root.

        The function defends against malicious index entries that attempt to
        traverse outside the registry directory or use absolute paths.  Any
        violation raises ``ValueError``.
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
    # Backend configuration
    # ------------------------------------------------------------------
    _backend: StorageBackend = _resolve_backend_from_env()

    @classmethod
    def configure_backend(cls, backend: StorageBackend) -> None:
        """Override the singleton backend implementation used for persistence."""
        if not isinstance(backend, StorageBackend):
            raise TypeError("backend must implement the StorageBackend protocol")
        cls._backend = backend
        logger.info("TemplateRegistry backend configured to %s", backend.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API - foundational subset (list / register / get / delete)
    # ------------------------------------------------------------------
    @classmethod
    def list(cls) -> list[str]:
        """Return sorted list of registered template identifiers."""
        return cls._backend.list()

    @classmethod
    def _resolve_next_version(cls, name: str, existing_index: Mapping[str, str]) -> str:
        """Return the next semantic version tag ("v<int>")."""
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
        graph: "Graph",
        *,
        name: str,
        version: str | None = None,
        meta: Mapping[str, Any] | None = None,
        forecast: ForecastSpec | None = None,
        preprocessing: PreprocessingSpec | None = None,
    ) -> str:
        """Register *graph* under *name* returning the full template identifier.

        Args:
            graph: Graph instance to persist.
            name: Template name, e.g. ``"lbo.standard"``.
            version: Explicit semantic version ("v1" / "v2"). If *None*, the
                next minor version is calculated automatically.
            meta: Optional additional metadata fields. Keys ``name``,
                ``version`` and ``category`` are filled in automatically and override
                duplicates.
            forecast: Optional forecast specification for the template.
            preprocessing: Optional preprocessing configuration for the template.

        Returns:
            The canonical template identifier (e.g. ``"lbo.standard_v1"``).
        """
        if not name or not isinstance(name, str):
            raise TypeError("Template name must be a non-empty string.")

        existing_ids = cls._backend.list()
        if version is None:
            version = cls._resolve_next_version(name, {tid: "" for tid in existing_ids})

        template_id = f"{name}_{version}"
        if template_id in existing_ids:
            raise ValueError(f"Template '{template_id}' already exists.")

        # ------------------------------------------------------------------
        # Serialize graph ➜ dict ➜ TemplateBundle
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

        return cls._backend.save(bundle)

    @classmethod
    def get(cls, template_id: str) -> TemplateBundle:
        """Return :class:`TemplateBundle` for *template_id*.

        Raises ``KeyError`` if *template_id* is unknown.
        """
        return cls._backend.load(template_id)

    @classmethod
    def delete(cls, template_id: str) -> None:
        """Remove *template_id* from the registry (bundle & metadata)."""
        cls._backend.delete(template_id)

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
        """Instantiate a :class:`~fin_statement_model.core.graph.Graph` from *template_id*.

        The helper first loads the stored :class:`TemplateBundle`, reconstructs
        the original graph via the IO facade and finally performs a deep clone
        to ensure the returned graph is **independent** from the internal cache
        of the registry.  Optional extra periods and node-renaming are applied
        on the cloned instance.

        Args:
            template_id: Canonical identifier, e.g. ``"lbo.standard_v1"``.
            periods: Optional list of additional periods to append. Existing
                periods are preserved - duplicates are ignored.
            rename_map: Optional mapping ``old_node_name → new_node_name``.

        Returns:
            A ready-to-use :class:`Graph` instance.
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
        """Return structural / value diff between two registered templates.

        Args:
            template_id_a: Identifier for *base* template (left-hand side).
            template_id_b: Identifier for *comparison* template (right-hand side).
            include_values: When *True* (default) numerical deltas are computed in addition to topology.
            periods: Optional subset of periods to compare.  When *None* the intersection of periods is used.
            atol: Absolute tolerance used by value comparison (`compare_values`).

        Returns:
            DiffResult: Frozen Pydantic model capturing structure and, optionally, value differences.
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
