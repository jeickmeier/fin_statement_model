"""Display-related configuration models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["DisplayConfig", "DisplayFlags"]


class DisplayFlags(BaseModel):
    """Boolean feature flags for statement display."""

    apply_sign_conventions: bool = Field(True, description="Whether to apply sign conventions by default")
    include_empty_items: bool = Field(False, description="Whether to include items with no data by default")
    include_metadata_cols: bool = Field(False, description="Whether to include metadata columns by default")
    add_is_adjusted_column: bool = Field(False, description="Add an 'is_adjusted' column by default")
    include_units_column: bool = Field(False, description="Include units column by default")
    include_css_classes: bool = Field(False, description="Include CSS class column by default")
    include_notes_column: bool = Field(False, description="Include notes column by default")
    apply_item_scaling: bool = Field(True, description="Apply item-specific scaling by default")
    apply_item_formatting: bool = Field(True, description="Apply item-specific formatting by default")
    apply_contra_formatting: bool = Field(True, description="Apply contra-specific formatting by default")
    add_contra_indicator_column: bool = Field(False, description="Add a contra indicator column by default")

    model_config = ConfigDict(extra="forbid")


# pylint: disable=too-many-public-methods
class DisplayConfig(BaseModel):
    """Settings for formatting and displaying statement outputs."""

    default_number_format: str = Field(",.2f", description="Default number format string")
    default_currency_format: str = Field(",.2f", description="Default currency format string")
    default_percentage_format: str = Field(".1%", description="Default percentage format string")
    hide_zero_rows: bool = Field(False, description="Hide rows where all values are zero")
    contra_display_style: Literal["parentheses", "brackets", "negative"] = Field(
        "parentheses",
        description="How to display contra items",
    )
    thousands_separator: str = Field(",", description="Thousands separator character")
    decimal_separator: str = Field(".", description="Decimal separator character")
    default_units: str = Field("USD", description="Default currency/units for display")
    scale_factor: float = Field(1.0, description="Default scale factor for display (e.g., 0.001 for thousands)")
    indent_character: str = Field("  ", description="Indentation characters used for nested line items")
    subtotal_style: str = Field("bold", description="CSS/markup style keyword for subtotal rows")
    total_style: str = Field("bold", description="CSS/markup style keyword for total rows")
    header_style: str = Field("bold", description="CSS/markup style keyword for header cells")
    contra_css_class: str = Field("contra-item", description="Default CSS class name for contra items")
    show_negative_sign: bool = Field(
        True, description="Prefix negative numbers with a minus sign when not using parentheses"
    )
    flags: DisplayFlags = Field(
        default_factory=DisplayFlags,
        description="Grouped boolean feature flags controlling optional display behaviour",
    )

    @field_validator("scale_factor")
    @classmethod
    def _validate_scale_factor(cls, v: float) -> float:
        """Ensure *scale_factor* is positive."""
        if v <= 0:
            raise ValueError("scale_factor must be positive")
        return v

    model_config = ConfigDict(extra="forbid")

    # Provide attribute passthrough to ``flags`` for backwards-compatibility.
    def __getattr__(self, item: str) -> Any:
        """Delegate unknown attribute access to ``flags``.

        This maintains compatibility with code that previously accessed
        flag attributes directly on the :class:`DisplayConfig` instance
        before they were nested under ``flags``.
        """
        if item in self.flags.__fields__:
            return getattr(self.flags, item)
        raise AttributeError(item)
