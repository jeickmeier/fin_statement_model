"""Domain models for the Template Registry & Engine (TRE).

This module defines immutable Pydantic *v2* data-models that underpin the
Template Registry & Engine subsystem. They are intentionally isolated from the
rest of the code-base so they remain a stable contract for IO and higher-level
services.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "DiffResult",
    "ForecastSpec",
    "StructureDiff",
    "TemplateBundle",
    "TemplateMeta",
    "ValuesDiff",
]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _calculate_sha256_checksum(obj: Mapping[str, Any]) -> str:
    """Return the SHA-256 checksum of *obj*.

    The object is first serialised to canonical JSON using :pyfunc:`json.dumps`
    with ``sort_keys=True`` and a stable ``separators`` setting. The resulting
    UTF-8 encoded bytes are then hashed with :pyfunc:`hashlib.sha256`.

    Args:
        obj: An arbitrary JSON-serialisable mapping.

    Returns:
        Lower-case hexadecimal digest string.
    """
    json_blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(json_blob).hexdigest()


# ---------------------------------------------------------------------------
# Forecast specification
# ---------------------------------------------------------------------------


class ForecastSpec(BaseModel):
    """Declarative forecasting recipe attached to a template.

    Mirrors the parameters accepted by :class:`fin_statement_model.forecasting.StatementForecaster` so a
    template can declare how its forward-looking periods should be generated at instantiation time.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    periods: list[str] = Field(..., description="Future periods to generate via forecasting.")
    node_configs: dict[str, Any] = Field(
        default_factory=dict,
        description="Mapping node-name ➜ forecast configuration (method & config) exactly as expected by StatementForecaster.",
    )


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------


class TemplateMeta(BaseModel):
    """Immutable metadata for a statement template."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., description="Template short-name, e.g. 'lbo'.")
    version: str = Field(..., description="Semantic version, e.g. 'v1'.")
    category: str = Field(..., description="High-level grouping, e.g. 'real_estate'.")
    description: str | None = Field(default=None, description="Optional human-readable description.")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="UTC creation timestamp.")
    tags: dict[str, str] = Field(default_factory=dict, description="Free-form key/value metadata tags.")


class TemplateBundle(BaseModel):
    """A serialisable bundle containing template graph and metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    meta: TemplateMeta = Field(..., description="Immutable template metadata.")
    graph_dict: dict[str, Any] = Field(..., description="Graph definition exported via IO facade.")
    checksum: str = Field(..., description="SHA-256 checksum of *graph_dict* JSON.")

    # New in v0.2 - declarative forecast specification (optional)
    forecast: ForecastSpec | None = Field(
        default=None,
        description="Optional forecast recipe applied on instantiation.",
    )

    # ---------------------------------------------------------------------
    # Validation helpers
    # ---------------------------------------------------------------------

    @model_validator(mode="after")
    def _validate_checksum(self) -> TemplateBundle:
        """Ensure *checksum* matches the SHA-256 of *graph_dict*."""
        expected = _calculate_sha256_checksum(self.graph_dict)
        if expected != self.checksum:
            raise ValueError("Checksum does not match the provided graph_dict.")
        return self


# ---------------------------------------------------------------------------
# Diff models
# ---------------------------------------------------------------------------


class StructureDiff(BaseModel):
    """Topology differences between two templates/graphs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    added_nodes: list[str] = Field(default_factory=list, description="Node IDs present only in B.")
    removed_nodes: list[str] = Field(default_factory=list, description="Node IDs present only in A.")
    changed_nodes: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping node-id → change description (e.g. 'formula').",
    )


class ValuesDiff(BaseModel):
    """Numerical deltas between two graphs on a per-cell basis."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    changed_cells: dict[str, float] = Field(
        default_factory=dict,
        description="Mapping '<node_id>|<period>' → Δ (GraphB - GraphA).",
    )
    max_delta: float | None = Field(
        default=None,
        description="Largest absolute delta observed, useful for quick summaries.",
    )


class DiffResult(BaseModel):
    """Aggregated structure and value differences between two templates."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    structure: StructureDiff = Field(..., description="Structural differences (nodes, edges, metadata).")
    values: ValuesDiff | None = Field(default=None, description="Optional value-level differences.")
