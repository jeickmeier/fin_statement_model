"""Data models for markdown formatting."""

from typing import Optional, TypedDict, Union


class MarkdownStatementItem(TypedDict):
    """Enhanced representation of a line item for Markdown output.

    This extends the basic StatementItem concept from the old implementation
    with additional formatting and display properties.
    """

    name: str
    values: dict[str, Union[float, int, str, None]]  # Values per period
    level: int
    is_subtotal: bool  # Indicates if the row is a subtotal or section header
    sign_convention: int  # 1 for normal, -1 for inverted
    display_format: Optional[str]  # Optional number format string
    units: Optional[str]  # Unit description
    display_scale_factor: float  # Factor to scale values for display
    is_contra: bool  # Whether this is a contra item for special formatting
