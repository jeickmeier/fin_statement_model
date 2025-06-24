"""IOConfig sub-model.

Handles settings for read/write operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["IOConfig"]


class IOConfig(BaseModel):
    """Configuration for input/output operations.

    Attributes:
        default_excel_sheet (str): Default sheet name for Excel operations.
        default_csv_delimiter (str): Default delimiter for CSV files.
        auto_create_output_dirs (bool): Automatically create output directories.
        validate_on_read (bool): Validate data when reading.
        default_mapping_configs_dir (Optional[Path]): Directory for mapping configs.
        auto_standardize_columns (bool): Standardize column names on read.
        skip_invalid_rows (bool): Skip rows with invalid data.
        strict_validation (bool): Enforce strict data validation on read.

    Example:
        >>> IOConfig(default_csv_delimiter=";").default_csv_delimiter
        ';'
    """

    default_excel_sheet: str = Field("Sheet1", description="Default sheet name for Excel operations")
    default_csv_delimiter: str = Field(",", description="Default delimiter for CSV files")
    auto_create_output_dirs: bool = Field(
        True,
        description="Automatically create output directories if they don't exist",
    )
    validate_on_read: bool = Field(True, description="Validate data on read operations")
    default_mapping_configs_dir: Path | None = Field(
        None,
        description="Directory containing custom mapping configuration files",
    )
    auto_standardize_columns: bool = Field(True, description="Automatically standardize column names when reading data")
    skip_invalid_rows: bool = Field(False, description="Skip rows with invalid data instead of raising errors")
    strict_validation: bool = Field(False, description="Use strict validation when reading data")

    model_config = ConfigDict(extra="forbid")
