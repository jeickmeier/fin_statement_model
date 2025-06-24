"""ValidationConfig sub-model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ValidationConfig"]


class ValidationConfig(BaseModel):
    """Settings for data validation within the graph."""

    strict_mode: bool = Field(False, description="Enable strict validation mode")
    auto_standardize_names: bool = Field(True, description="Automatically standardize node names to canonical form")
    warn_on_non_standard: bool = Field(True, description="Warn when using non-standard node names")
    check_balance_sheet_balance: bool = Field(True, description="Validate that Assets = Liabilities + Equity")
    balance_tolerance: float = Field(1.0, description="Maximum acceptable difference for balance sheet validation")
    warn_on_negative_assets: bool = Field(True, description="Warn when asset values are negative")
    validate_sign_conventions: bool = Field(True, description="Validate that items follow expected sign conventions")

    @field_validator("balance_tolerance")
    @classmethod
    def _validate_tolerance(cls, v: float) -> float:
        if v < 0:
            raise ValueError("balance_tolerance must be non-negative")
        return v

    model_config = ConfigDict(extra="forbid")
