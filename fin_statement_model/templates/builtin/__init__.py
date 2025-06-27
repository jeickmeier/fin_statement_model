"""Built-in Template Loader for Financial Statement Models.

This module provides automatic discovery and installation of pre-built financial
statement templates shipped with the library. Templates are stored as JSON bundles
in the `data/` subdirectory and include common financial models like LBO analysis
and real estate lending scenarios.

The loader handles:
    - **Auto-discovery**: Scans for .json template bundles in the data directory
    - **Validation**: Ensures template integrity via checksum verification
    - **Registry Integration**: Installs templates into the local TemplateRegistry
    - **Update Detection**: Automatically refreshes templates when JSON files change
    - **Idempotent Installation**: Safe to call multiple times without duplication

Available Built-in Templates:
    - **lbo.standard_v1**: Minimal 3-node LBO model with Revenue, COGS, and calculated metrics
    - **real_estate_lending_v3**: Construction loan waterfall with interest calculations

Example:
    >>> from fin_statement_model.templates.builtin import install_builtin_templates
    >>> from fin_statement_model.templates import TemplateRegistry
    >>>
    >>> # Install all built-in templates (idempotent)
    >>> install_builtin_templates()
    >>>
    >>> # Verify installation
    >>> templates = TemplateRegistry.list()
    >>> assert "lbo.standard_v1" in templates
    >>> assert "real_estate_lending_v3" in templates
    >>>
    >>> # Use a built-in template
    >>> lbo_graph = TemplateRegistry.instantiate("lbo.standard_v1")
    >>> revenue_2024 = lbo_graph.calculate("Revenue", "2024")
    >>> print(f"2024 Revenue: ${revenue_2024:,.0f}")  # 2024 Revenue: $1,000

Template Bundle Structure:
    Each JSON file contains:
    - **meta**: Template metadata (name, version, description)
    - **graph_dict**: Serialized graph definition with nodes and relationships
    - **forecast**: Optional forecasting configuration
    - **preprocessing**: Optional data transformation pipeline
    - **checksum**: SHA-256 integrity hash
"""

from __future__ import annotations

from importlib import resources
import json
import logging
from typing import TYPE_CHECKING, Any

from fin_statement_model.io import read_data
from fin_statement_model.templates.models import TemplateBundle
from fin_statement_model.templates.registry import TemplateRegistry

if TYPE_CHECKING:  # pragma: no cover - import only for type hints
    from pathlib import Path

logger = logging.getLogger(__name__)

__all__: list[str] = ["install_builtin_templates"]

_DATA_PACKAGE_ROOT = __name__  # 'fin_statement_model.templates.builtin'


def _iter_bundle_files() -> list[Path]:
    """Return paths for all packaged bundle JSON files.

    Locates the **data** sub-directory using importlib.resources and returns
    all .json files found. Compatible with both regular installations and
    zipped wheel distributions.

    Returns:
        List of Path objects for JSON template bundle files. May be empty
        if no templates are packaged or if the data directory doesn't exist.

    Example:
        >>> paths = _iter_bundle_files()
        >>> json_files = [p.name for p in paths if p.suffix == ".json"]
        >>> print(json_files)  # ['lbo.standard_v1.json', 'real_estate_lending_v3.json']
    """
    try:
        # Locate the package directory for *fin_statement_model.templates.builtin*
        pkg_root = resources.files(_DATA_PACKAGE_ROOT)
        data_root = pkg_root.joinpath("data")
    except (ModuleNotFoundError, AttributeError):
        return []

    if not data_root.is_dir():
        return []

    # Convert Traversable → real filesystem path (works for zipped wheels as well)
    with resources.as_file(data_root) as root_path:
        return [p for p in root_path.iterdir() if p.suffix == ".json"]


def install_builtin_templates(*, force: bool = False) -> None:
    """Install built-in financial statement templates into the local registry.

    Discovers and loads all JSON template bundles from the built-in data directory,
    validates their integrity, and registers them with the TemplateRegistry. The
    function is idempotent and safe to call multiple times.

    Args:
        force: When True, unconditionally re-install all templates even if they
            already exist with matching checksums. When False (default), only
            installs templates that are missing or have changed checksums.

    Raises:
        ValueError: If a template bundle is malformed or conflicts with existing
            registrations (only in non-force mode).
        OSError: If template files cannot be read from the data directory.

    Examples:
        Basic installation:
        >>> from fin_statement_model.templates.builtin import install_builtin_templates
        >>> install_builtin_templates()  # Install all built-in templates

        Force reinstallation:
        >>> install_builtin_templates(force=True)  # Overwrite existing templates

        Check what was installed:
        >>> from fin_statement_model.templates import TemplateRegistry
        >>> templates = TemplateRegistry.list()
        >>> builtin_templates = [t for t in templates if not t.startswith("custom")]
        >>> print(f"Installed {len(builtin_templates)} built-in templates")

    Note:
        The function automatically detects changes to template JSON files via
        checksum comparison and updates the registry accordingly. This makes
        development workflows smoother when editing template definitions.
    """
    bundle_paths = _iter_bundle_files()
    if not bundle_paths:
        logger.info("No built-in template bundles found - nothing to install.")
        return

    existing = set(TemplateRegistry.list())
    installed: list[str] = []

    for path in bundle_paths:
        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            bundle = TemplateBundle.model_validate(data)
        except (OSError, ValueError) as exc:  # pragma: no cover - defensive only
            logger.warning("Skipping malformed bundle '%s': %s", getattr(path, "name", path), exc)
            continue

        template_id = f"{bundle.meta.name}_{bundle.meta.version}"
        if template_id in existing:
            # ------------------------------------------------------------------
            # Detect changes in the packaged bundle (via checksum) and decide
            # whether the existing registry entry must be replaced.  This makes
            # the loader workflow smoother for analysts who tweak JSON files -
            # their edits will be picked-up automatically on the next run.
            # ------------------------------------------------------------------
            if not force:
                try:
                    current_bundle = TemplateRegistry.get(template_id)
                except KeyError:
                    # Index is out-of-sync - fall back to re-install logic below.
                    pass
                else:
                    if current_bundle.checksum == bundle.checksum:
                        logger.debug("Template '%s' already registered and up-to-date - skipping.", template_id)
                        continue  # No changes - keep as-is
            # Either *force* is True OR checksum differs - replace existing
            TemplateRegistry.delete(template_id)
            existing.discard(template_id)

        # Re-hydrate Graph and register ------------------------------------------------
        graph = read_data("graph_definition_dict", bundle.graph_dict)

        try:
            TemplateRegistry.register_graph(
                graph,
                name=bundle.meta.name,
                version=bundle.meta.version,
                meta=bundle.meta.model_dump(exclude={"name", "version"}),
                forecast=bundle.forecast,
                preprocessing=bundle.preprocessing,
            )
        except ValueError as exc:
            # Duplicate template_id - possible race condition; skip in force mode
            if force:
                logger.debug("Could not overwrite existing template '%s': %s", template_id, exc)
                continue
            raise

        installed.append(template_id)

    if installed:
        logger.info("Installed %d built-in templates: %s", len(installed), ", ".join(installed))
    else:
        logger.info("All built-in templates already installed.")
