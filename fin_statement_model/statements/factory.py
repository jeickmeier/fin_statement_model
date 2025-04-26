"""Statement factory module for building, formatting, and exporting financial statements.

Provides `StatementFactory` with convenience methods to build managers, format DataFrame/JSON outputs,
and export statements to Excel or JSON files.
"""

from typing import Any, Union
import pandas as pd
from fin_statement_model.core.graph import Graph
from .manager import StatementManager
import os
import json
import logging

logger = logging.getLogger(__name__)


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
    ) -> Union[pd.DataFrame, dict[str, pd.DataFrame]]:
        """Load, calculate, and format the statement(s) as pandas DataFrame(s).

        Args:
            graph: An instance of the core Graph to use for calculations.
            config_path: Path to the statement configuration file or directory.
            format_type: Formatting type to use (default 'dataframe').
            **kwargs: Additional parameters for the formatter (e.g., subtotals).

        Returns:
            pd.DataFrame or Dict[str, pd.DataFrame]: The formatted statement data.
                                                     Returns a single DataFrame if config_path
                                                     points to a file, or a dict of DataFrames
                                                     if it points to a directory.
        """
        manager = StatementFactory.build_manager(graph, config_path)
        stmt_ids = manager.get_all_statement_ids()
        if not stmt_ids:
            raise ValueError("No statements registered in manager from config path.")

        outputs: dict[str, pd.DataFrame] = {}
        for stmt_id in stmt_ids:
            manager.create_calculations(stmt_id)
            # Assuming format_statement returns DataFrame for 'dataframe' type
            formatted_output = manager.format_statement(stmt_id, format_type, **kwargs)
            if isinstance(formatted_output, pd.DataFrame):
                 outputs[stmt_id] = formatted_output
            else:
                # Handle unexpected format type return if necessary
                logger.warning(f"Received unexpected format type for {stmt_id}: {type(formatted_output)}")

        # If only one statement was loaded (likely from a single file path)
        if len(outputs) == 1 and os.path.isfile(config_path):
            return next(iter(outputs.values()))
        # Otherwise, return the dictionary of statement_id -> DataFrame
        return outputs

    @staticmethod
    def create_statement_json(
        graph: Graph,
        config_path: str,
    ) -> dict[str, dict[str, dict[str, float]]]:
        """Load statements, calculate all, and return JSON-serializable dict of statement data dictionaries."""
        manager = StatementFactory.build_manager(graph, config_path)
        stmt_ids = manager.get_all_statement_ids()
        if not stmt_ids:
            raise ValueError("No statements registered in manager.")
        json_outputs: dict[str, dict[str, dict[str, float]]] = {}
        for stmt_id in stmt_ids:
            manager.create_calculations(stmt_id)
            json_outputs[stmt_id] = manager.build_data_dictionary(stmt_id)
        return json_outputs

    @staticmethod
    def export_statements_to_excel(
        graph: Graph, config_path: str, output_dir: str, **kwargs: Any
    ) -> None:
        """Export all registered statements to individual Excel files using the StatementManager."""
        manager = StatementFactory.build_manager(graph, config_path)
        os.makedirs(output_dir, exist_ok=True)
        stmt_ids = manager.get_all_statement_ids()
        if not stmt_ids:
             logger.warning(f"No statements loaded from {config_path}, nothing to export to Excel.")
             return

        for stmt_id in stmt_ids:
            # Ensure calculations exist before exporting
            manager.create_calculations(stmt_id)
            file_path = os.path.join(output_dir, f"{stmt_id}.xlsx")
            try:
                # Delegate export entirely to manager
                manager.export_to_excel(stmt_id, file_path, **kwargs)
            except Exception as e:
                 # Log error and continue exporting others if possible
                 logger.exception(f"Failed to export statement '{stmt_id}' to Excel: {e}")

    @staticmethod
    def export_statements_to_json(
        graph: Graph,
        config_path: str,
        output_dir: str,
        orient: str = "records",
        **kwargs: Any
    ) -> None:
        """Export all registered statements to individual JSON files using the StatementManager."""
        manager = StatementFactory.build_manager(graph, config_path)
        os.makedirs(output_dir, exist_ok=True)
        stmt_ids = manager.get_all_statement_ids()
        if not stmt_ids:
             logger.warning(f"No statements loaded from {config_path}, nothing to export to JSON.")
             return

        for stmt_id in stmt_ids:
            # Ensure calculations exist before exporting
            manager.create_calculations(stmt_id)
            file_path = os.path.join(output_dir, f"{stmt_id}.json")
            try:
                # Delegate export entirely to manager
                # Pass orient and kwargs through
                manager.export_to_json(stmt_id, file_path, orient=orient, **kwargs)
            except Exception as e:
                 logger.exception(f"Failed to export statement '{stmt_id}' to JSON: {e}")
