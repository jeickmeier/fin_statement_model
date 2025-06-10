from fin_statement_model.statements.utilities.result_types import ErrorDetail


def pretty_print_errors(errors: list[ErrorDetail]) -> None:
    """
    Pretty-print a list of ErrorDetail objects as a table to the console.

    Args:
        errors: List of ErrorDetail instances to display.
    """
    if not errors:
        return

    # Prepare table headers
    headers = ["SEVERITY", "CODE", "CONTEXT", "SOURCE", "MESSAGE"]
    rows: list[list[str]] = []
    for err in errors:
        rows.append(
            [
                err.severity.value.upper(),
                err.code,
                err.context or "",
                err.source or "",
                err.message,
            ]
        )

    # Calculate column widths
    col_widths = [max(len(str(val)) for val in col) for col in zip(headers, *rows)]

    # Build header row and separator
    header_row = " | ".join(
        headers[i].ljust(col_widths[i]) for i in range(len(headers))
    )
    separator = "-+-".join("".ljust(col_widths[i], "-") for i in range(len(headers)))

    # Print table
    print(header_row)
    print(separator)
    for row in rows:
        line = " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers)))
        print(line)
