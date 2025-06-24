"""StatementsConfig sub-model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from fin_statement_model.statements.configs.models import AdjustmentFilterSpec

__all__ = ["StatementsConfig"]


class StatementsConfig(BaseModel):
    """Settings for building and formatting financial statements."""

    default_adjustment_filter: AdjustmentFilterSpec | list[str] | None = Field(
        None,
        description="Default adjustment filter spec or list of tags to apply when building statements",
    )
    enable_node_validation: bool = Field(
        False,
        description="Enable node ID validation during statement building by default",
    )
    node_validation_strict: bool = Field(
        False,
        description="Treat node validation failures as errors (strict) by default",
    )

    model_config = ConfigDict(extra="forbid")
