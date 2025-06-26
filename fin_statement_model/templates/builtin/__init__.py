"""Built-in Template Loader.

Auto-discovers TemplateBundle JSON files shipped inside the
`fin_statement_model.templates.builtin.data` package and registers the
contained Graph objects with the local filesystem-backed
:class:`fin_statement_model.templates.registry.TemplateRegistry`.

Example:
    >>> from fin_statement_model.templates.builtin import install_builtin_templates
    >>> install_builtin_templates()  # idempotent
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
    """Return paths for all packaged bundle JSON files (may be empty).

    The helper locates the **data** sub-directory next to this module using
    :pyfunc:`importlib.resources.files`.  Unlike the previous implementation it
    no longer relies on *data* being a Python package (i.e. it does **not**
    require an ``__init__.py`` file).  This makes the loader compatible with
    standard wheel layouts where ``data/`` is a plain resources directory.
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
    """Install built-in templates into the local registry.

    The function is *idempotent*; calling it multiple times does not create
    duplicates. Pass ``force=True`` to re-install templates that are already
    present.
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
            if force:
                TemplateRegistry.delete(template_id)
                existing.remove(template_id)
            else:
                logger.debug("Template '%s' already registered - skipping.", template_id)
                continue

        # Re-hydrate Graph and register ------------------------------------------------
        graph = read_data("graph_definition_dict", bundle.graph_dict)

        try:
            TemplateRegistry.register_graph(
                graph,
                name=bundle.meta.name,
                version=bundle.meta.version,
                meta=bundle.meta.model_dump(exclude={"name", "version"}),
                forecast=bundle.forecast,
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
