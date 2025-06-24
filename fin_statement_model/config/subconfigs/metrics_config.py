"""MetricsConfig sub-model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["MetricsConfig"]


class MetricsConfig(BaseModel):
    """Settings for metric registry behavior."""

    custom_metrics_dir: Path | None = Field(None, description="Directory containing custom metric definitions")
    validate_metric_inputs: bool = Field(True, description="Validate metric inputs exist in graph")
    auto_register_metrics: bool = Field(True, description="Automatically register metrics from definition files")

    model_config = ConfigDict(extra="forbid")
