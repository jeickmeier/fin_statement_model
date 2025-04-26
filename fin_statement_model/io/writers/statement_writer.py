"""Writers for exporting financial statement data (usually DataFrames)."""

import pandas as pd

from fin_statement_model.io.exceptions import WriteError

__all__ = ["write_statement_to_excel", "write_statement_to_json"]


def write_statement_to_excel(
    statement_df: pd.DataFrame,
    file_path: str,
    **kwargs: dict[str, object],
) -> None:
    """Write a statement DataFrame to an Excel file.

    Args:
        statement_df: The pandas DataFrame containing the formatted statement data.
        file_path: Path to save the Excel file.
        **kwargs: Additional arguments passed directly to pandas.DataFrame.to_excel
                 (e.g., sheet_name, index, header).

    Raises:
        WriteError: If writing the file fails.
    """
    try:
        # Default index=False is common for statement exports
        kwargs.setdefault("index", False)
        statement_df.to_excel(file_path, **kwargs)
    except Exception as e:
        # Removed StatementError handling as it's no longer relevant here
        raise WriteError(
            message="Failed to export statement DataFrame to Excel",
            target=file_path,
            format_type="excel", # Corrected parameter name
            original_error=e,
        ) from e


def write_statement_to_json(
    statement_df: pd.DataFrame,
    file_path: str,
    orient: str = "columns",
    **kwargs: dict[str, object],
) -> None:
    """Write a statement DataFrame to a JSON file.

    Args:
        statement_df: The pandas DataFrame containing the formatted statement data.
        file_path: Path to save the JSON file.
        orient: JSON orientation format (passed to pandas.DataFrame.to_json).
        **kwargs: Additional arguments passed directly to pandas.DataFrame.to_json
                 (e.g., indent, date_format).

    Raises:
        WriteError: If writing the file fails.
    """
    try:
        statement_df.to_json(file_path, orient=orient, **kwargs)
    except Exception as e:
        # Removed StatementError handling
        raise WriteError(
            message="Failed to export statement DataFrame to JSON",
            target=file_path,
            format_type="json", # Corrected parameter name
            original_error=e,
        ) from e
