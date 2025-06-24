"""Helpers to load the new Pydantic-v2 statement structure models.

This thin wrapper keeps the public API stable regardless of where the concrete
implementation lives.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .structure.models_v2 import StatementStructure, load_structure as _load_structure_impl

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["StatementStructure", "load_structure"]


def load_structure(raw_cfg: dict[str, Any] | str | Path) -> StatementStructure:
    """See :func:`fin_statement_model.statements.structure.models_v2.load_structure`."""
    return _load_structure_impl(raw_cfg)
