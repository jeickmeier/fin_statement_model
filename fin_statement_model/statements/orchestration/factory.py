"""Statement processing facade.

This module provides the main public API for statement processing,
delegating to specialized modules for specific functionality.

The factory module serves as a convenient entry point that maintains
backward compatibility while the actual implementation is split across:
- orchestrator.py: Main workflow coordination
- loader.py: Configuration loading and validation
- exporter.py: Export functionality
"""

from fin_statement_model.statements.orchestration.exporter import (
    export_statements_to_excel,
    export_statements_to_json,
)
from fin_statement_model.statements.orchestration.orchestrator import (
    create_statement_dataframe,
)

__all__ = [
    "create_statement_dataframe",
    "export_statements_to_excel",
    "export_statements_to_json",
]
