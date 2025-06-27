"""Domain models for the Template Registry & Engine (TRE).

This module defines immutable Pydantic v2 data models that form the foundation
of the Template Registry & Engine subsystem. These models provide type-safe
contracts for template serialization, metadata management, and diff operations.

The models are intentionally isolated from the core graph implementation to
maintain stable APIs for persistence and inter-service communication.

Key Model Types:
    - **TemplateMeta**: Template metadata (name, version, categories, tags)
    - **TemplateBundle**: Complete serializable template with graph and configs
    - **ForecastSpec**: Declarative forecasting configuration
    - **PreprocessingSpec**: Data transformation pipeline definition
    - **DiffResult**: Template comparison results (structure + values)

Example:
    >>> from fin_statement_model.templates.models import TemplateMeta, TemplateBundle
    >>>
    >>> # Create template metadata
    >>> meta = TemplateMeta(name="my.model", version="v1", category="custom", description="Custom financial model")
    >>>
    >>> # Bundle includes graph dict and checksum
    >>> bundle = TemplateBundle(meta=meta, graph_dict={"periods": ["2024"], "nodes": {}}, checksum="abc123...")
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
    "PreprocessingSpec",
    "PreprocessingStep",
    "StructureDiff",
    "TemplateBundle",
    "TemplateMeta",
    "ValuesDiff",
]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _calculate_sha256_checksum(obj: Mapping[str, Any]) -> str:
    """Calculate SHA-256 checksum of a JSON-serializable object.

    The object is first serialized to canonical JSON with sorted keys and
    stable separators, then hashed with SHA-256 for content verification.

    Args:
        obj: JSON-serializable mapping (typically a graph_dict)

    Returns:
        Lowercase hexadecimal SHA-256 digest string

    Example:
        >>> data = {"nodes": {"Revenue": {"type": "item"}}, "periods": ["2024"]}
        >>> checksum = _calculate_sha256_checksum(data)
        >>> len(checksum)  # SHA-256 produces 64-character hex string
        64
        >>> checksum.isalnum()
        True
    """
    json_blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(json_blob).hexdigest()


# ---------------------------------------------------------------------------
# Forecast specification
# ---------------------------------------------------------------------------


class ForecastSpec(BaseModel):
    """Declarative forecasting configuration for template instantiation.

    Defines how future periods should be generated when a template is
    instantiated. Mirrors the parameter structure expected by
    StatementForecaster to enable automated forecasting workflows.

    Attributes:
        periods: List of future period identifiers to generate
        node_configs: Mapping of node names to their forecast configurations,
            where each config specifies the method and parameters

    Example:
        >>> forecast_spec = ForecastSpec(
        ...     periods=["2027", "2028"],
        ...     node_configs={
        ...         "Revenue": {"method": "simple", "config": 0.1},
        ...         "COGS": {"method": "historical_growth", "config": {"aggregation": "mean"}},
        ...     },
        ... )
        >>> forecast_spec.periods
        ['2027', '2028']
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    periods: list[str] = Field(..., description="Future periods to generate via forecasting.")
    node_configs: dict[str, Any] = Field(
        default_factory=dict,
        description="Mapping node-name ➜ forecast configuration (method & config) exactly as expected by StatementForecaster.",
    )


# ---------------------------------------------------------------------------
# Preprocessing specification
# ---------------------------------------------------------------------------


class PreprocessingStep(BaseModel):
    """Single data transformation step in a preprocessing pipeline.

    Represents one transformer invocation with its parameters. Steps are
    executed sequentially in the order they appear in a PreprocessingSpec.

    Attributes:
        name: Registered transformer name (e.g., "time_series", "normalization")
        params: Keyword arguments passed to the transformer

    Example:
        >>> step = PreprocessingStep(
        ...     name="time_series", params={"transformation_type": "yoy", "periods": 1, "as_percent": True}
        ... )
        >>> step.name
        'time_series'
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., description="Registered transformer name to execute.")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Keyword arguments forwarded to the transformer constructor/executor.",
    )


class PreprocessingSpec(BaseModel):
    """Ordered data transformation pipeline for template instantiation.

    Defines a sequence of preprocessing steps that are automatically applied
    when a template is instantiated. Each step references a registered
    transformer with its configuration parameters.

    Attributes:
        pipeline: Ordered list of preprocessing steps to execute

    Example:
        >>> preprocessing = PreprocessingSpec(
        ...     pipeline=[
        ...         PreprocessingStep(name="normalization", params={"method": "min_max", "feature_range": (0, 1)}),
        ...         PreprocessingStep(name="time_series", params={"transformation_type": "yoy"}),
        ...     ]
        ... )
        >>> len(preprocessing.pipeline)
        2
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    pipeline: list[PreprocessingStep] = Field(
        ..., description="Ordered list of preprocessing steps to run at instantiation time."
    )


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------


class TemplateMeta(BaseModel):
    """Immutable metadata for a financial statement template.

    Contains identifying information, versioning, categorization, and
    free-form metadata tags for organizing and discovering templates.

    Attributes:
        name: Template identifier (e.g., "lbo.standard", "real_estate.lending")
        version: Semantic version string (e.g., "v1", "v2.1")
        category: High-level grouping for organization (e.g., "lbo", "real_estate")
        description: Optional human-readable description
        created_at: UTC timestamp of template creation
        tags: Free-form key-value metadata for custom categorization

    Example:
        >>> meta = TemplateMeta(
        ...     name="lbo.standard",
        ...     version="v1",
        ...     category="lbo",
        ...     description="Standard LBO model with 3-statement integration",
        ...     tags={"complexity": "basic", "industry": "general"},
        ... )
        >>> f"{meta.name}_{meta.version}"
        'lbo.standard_v1'
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., description="Template short-name, e.g. 'lbo'.")
    version: str = Field(..., description="Semantic version, e.g. 'v1'.")
    category: str = Field(..., description="High-level grouping, e.g. 'real_estate'.")
    description: str | None = Field(default=None, description="Optional human-readable description.")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="UTC creation timestamp.")
    tags: dict[str, str] = Field(default_factory=dict, description="Free-form key/value metadata tags.")


class TemplateBundle(BaseModel):
    """Complete serializable template with graph definition and configurations.

    A TemplateBundle represents a fully-specified financial statement template
    that can be persisted, transmitted, and instantiated. It includes the core
    graph structure plus optional forecasting and preprocessing specifications.

    The bundle's integrity is verified via SHA-256 checksum of the graph_dict
    to detect tampering or corruption during storage/transmission.

    Attributes:
        meta: Template metadata (name, version, description, etc.)
        graph_dict: Serialized graph definition with nodes, periods, adjustments
        checksum: SHA-256 hash of graph_dict for integrity verification
        forecast: Optional declarative forecasting configuration
        preprocessing: Optional data transformation pipeline

    Example:
        >>> from fin_statement_model.templates.models import TemplateMeta, TemplateBundle
        >>>
        >>> meta = TemplateMeta(name="test", version="v1", category="test")
        >>> graph_dict = {"periods": ["2024"], "nodes": {}, "adjustments": []}
        >>>
        >>> # Checksum is calculated automatically if not provided
        >>> bundle = TemplateBundle(meta=meta, graph_dict=graph_dict, checksum=_calculate_sha256_checksum(graph_dict))
        >>> bundle.meta.name
        'test'
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    meta: TemplateMeta = Field(..., description="Immutable template metadata.")
    graph_dict: dict[str, Any] = Field(..., description="Graph definition exported via IO facade.")
    checksum: str = Field(..., description="SHA-256 checksum of *graph_dict* JSON.")

    # Optional declarative forecast specification
    forecast: ForecastSpec | None = Field(
        default=None,
        description="Optional forecast recipe applied on instantiation.",
    )

    # Optional preprocessing pipeline specification
    preprocessing: PreprocessingSpec | None = Field(
        default=None,
        description="Optional preprocessing pipeline applied on instantiation.",
    )

    # ---------------------------------------------------------------------
    # Validation helpers
    # ---------------------------------------------------------------------

    @model_validator(mode="after")
    def _validate_checksum(self) -> TemplateBundle:
        """Validate that checksum matches the SHA-256 hash of graph_dict.

        Raises:
            ValueError: If the provided checksum doesn't match the calculated
                hash of graph_dict, indicating potential data corruption.
        """
        expected = _calculate_sha256_checksum(self.graph_dict)
        if expected != self.checksum:
            raise ValueError("Checksum does not match the provided graph_dict.")
        return self


# ---------------------------------------------------------------------------
# Diff models
# ---------------------------------------------------------------------------


class StructureDiff(BaseModel):
    """Structural differences between two financial statement templates.

    Captures topology changes at the node level, identifying additions,
    removals, and configuration changes. Does not include value-level
    differences which are handled separately by ValuesDiff.

    Attributes:
        added_nodes: Node IDs present only in the comparison template
        removed_nodes: Node IDs present only in the base template
        changed_nodes: Nodes present in both but with different configurations

    Example:
        >>> diff = StructureDiff(
        ...     added_nodes=["NewMetric"], removed_nodes=["OldMetric"], changed_nodes={"Revenue": "formula updated"}
        ... )
        >>> len(diff.added_nodes + diff.removed_nodes + list(diff.changed_nodes))
        3
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    added_nodes: list[str] = Field(default_factory=list, description="Node IDs present only in B.")
    removed_nodes: list[str] = Field(default_factory=list, description="Node IDs present only in A.")
    changed_nodes: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping node-id → change description (e.g. 'formula').",
    )


class ValuesDiff(BaseModel):
    """Numerical value differences between two templates on a per-cell basis.

    Captures period-by-period value deltas for nodes that exist in both
    templates. Only includes cells where the absolute difference exceeds
    the specified tolerance threshold.

    Attributes:
        changed_cells: Mapping of "node|period" keys to numerical deltas
        max_delta: Largest absolute difference found (useful for summaries)

    Example:
        >>> values_diff = ValuesDiff(changed_cells={"Revenue|2024": 100.0, "COGS|2025": -50.0}, max_delta=100.0)
        >>> values_diff.max_delta
        100.0
        >>> len(values_diff.changed_cells)
        2
    """

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
    """Comprehensive comparison result between two financial statement templates.

    Aggregates both structural (topology) and value-level differences into
    a single result object. Value comparison is optional and can be disabled
    for performance when only structural changes are needed.

    Attributes:
        structure: Structural differences (nodes, configuration changes)
        values: Optional value-level differences (numerical deltas)

    Example:
        >>> structure = StructureDiff(added_nodes=["NewNode"])
        >>> values = ValuesDiff(changed_cells={"Revenue|2024": 100.0})
        >>>
        >>> diff_result = DiffResult(structure=structure, values=values)
        >>> len(diff_result.structure.added_nodes)
        1
        >>> diff_result.values.max_delta
        100.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    structure: StructureDiff = Field(..., description="Structural differences (nodes, edges, metadata).")
    values: ValuesDiff | None = Field(default=None, description="Optional value-level differences.")
