"""Reusable helpers for loading YAML configuration files.

This tiny module centralises the *boring* boiler-plate needed across the
code-base (``MetricRegistry``, ``StandardNodeRegistry`` …) when we need to scan a
folder for ``*.yaml`` files, parse them safely and yield the resulting Python
dictionaries.  It deliberately keeps **zero** dependencies other than *PyYAML*
(which is optional at import-time because the caller might decide to handle the
ImportError in a custom way).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator, Tuple, Union

try:
    import yaml

    _HAS_YAML = True
except ImportError:  # pragma: no cover – optional dep
    _HAS_YAML = False

__all__: list[str] = [
    "HAS_YAML",
    "iter_yaml_files",
]

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

HAS_YAML: bool = _HAS_YAML


def iter_yaml_files(directory: Union[str, Path]) -> Iterator[Tuple[Path, Any]]:
    """Yield ``(filepath, parsed_data)`` tuples for each ``*.yaml`` file in *directory*.

    The helper is intentionally *lax*:
    • Empty / comment-only files are skipped silently.
    • YAML syntax errors are yielded as *None* so that the caller can decide
      whether to raise, warn or ignore on a per-file basis.

    Parameters
    ----------
    directory:
        Directory path to scan (non-recursive).
    """

    if not HAS_YAML:
        raise ImportError("PyYAML is required for YAML loading but is not installed.")

    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise FileNotFoundError(f"YAML directory not found: {dir_path}")

    for filepath in dir_path.glob("*.yaml"):
        try:
            with filepath.open("r", encoding="utf-8") as fh:
                content = fh.read()
            if not content.strip():
                # Empty file – nothing to yield
                continue
            try:
                data = yaml.safe_load(content)
            except yaml.YAMLError as exc:
                # Yield the exception back for caller to handle
                yield filepath, exc
                continue
            yield filepath, data
        except Exception as exc:  # pragma: no cover – unexpected IO errors
            yield filepath, exc
