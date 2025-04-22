"""Statement factory module for building, formatting, and exporting financial statements.

Provides `StatementFactory` with convenience methods to build managers, format DataFrame/JSON outputs,
and export statements to Excel or JSON files.
"""

from typing import Any
import pandas as pd
from fin_statement_model.core.graph import Graph
from .manager import StatementManager
import os
import json


class StatementFactory:
    """Factory for building and formatting financial statements.

    Provides convenience methods to create a StatementManager and produce
    formatted outputs based on configuration files.
    """

    @staticmethod
    def build_manager(graph: Graph, config_path: str) -> StatementManager:
        """Create and return a StatementManager loaded with the given configuration.

        Args:
            graph: An instance of the core Graph to use for calculations.
            config_path: Path to the statement configuration file (JSON/YAML).

        Returns:
            StatementManager: Manager with the statement loaded and registered.
        """
        manager = StatementManager(graph)
        # Support loading a single config file or all configs in a directory
        if os.path.isdir(config_path):
            manager.load_statements_from_directory(config_path)
        else:
            manager.load_statement(config_path)
        return manager

    @staticmethod
    def create_statement_dataframe(
        graph: Graph, config_path: str, format_type: str = "dataframe", **kwargs: Any
    ) -> pd.DataFrame:
        """Load, calculate, and format the statement as a pandas DataFrame.

        Args:
            graph: An instance of the core Graph to use for calculations.
            config_path: Path to the statement configuration file.
            format_type: Formatting type to use (default 'dataframe').
            **kwargs: Additional parameters for the formatter (e.g., subtotals).

        Returns:
            pd.DataFrame: The formatted statement data.
        """
        manager = StatementFactory.build_manager(graph, config_path)
        stmt_ids = manager.get_all_statement_ids()
        if not stmt_ids:
            raise ValueError("No statements registered in manager.")
        # Generate formatted output for each statement
        outputs: dict[str, pd.DataFrame] = {}
        for stmt_id in stmt_ids:
            manager.create_calculations(stmt_id)
            outputs[stmt_id] = manager.format_statement(stmt_id, format_type, **kwargs)
        # If only one statement, return its DataFrame directly
        if len(outputs) == 1:
            return next(iter(outputs.values()))
        return outputs

    @staticmethod
    def create_statement_json(
        graph: Graph,
        config_path: str,
    ) -> dict[str, object]:
        """Load statements, calculate all, and return JSON-serializable dict of statement data."""
        manager = StatementFactory.build_manager(graph, config_path)
        stmt_ids = manager.get_all_statement_ids()
        if not stmt_ids:
            raise ValueError("No statements registered in manager.")
        json_outputs: dict[str, Any] = {}
        for stmt_id in stmt_ids:
            manager.create_calculations(stmt_id)
            json_outputs[stmt_id] = manager.build_data_dictionary(stmt_id)
        return json_outputs

    @staticmethod
    def export_statements_to_excel(
        graph: Graph, config_path: str, output_dir: str, **kwargs: Any
    ) -> None:
        """Export all registered statements to individual Excel files in output_dir."""
        manager = StatementFactory.build_manager(graph, config_path)
        os.makedirs(output_dir, exist_ok=True)
        for stmt_id in manager.get_all_statement_ids():
            manager.create_calculations(stmt_id)
            file_path = os.path.join(output_dir, f"{stmt_id}.xlsx")
            manager.export_to_excel(stmt_id, file_path, **kwargs)

    @staticmethod
    def export_statements_to_json(
        graph: Graph,
        config_path: str,
        output_dir: str,
    ) -> None:
        """Export all registered statements to individual JSON files in output_dir."""
        os.makedirs(output_dir, exist_ok=True)
        json_outputs = StatementFactory.create_statement_json(graph, config_path)
        for stmt_id, data in json_outputs.items():
            file_path = os.path.join(output_dir, f"{stmt_id}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
