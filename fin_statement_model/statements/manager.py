"""Statement manager for Financial Statement Model.

This module provides a manager for handling statement structures and formatting
in the Financial Statement Model.
"""

import os
import logging
from typing import Any, Optional, Union
import pandas as pd
from pathlib import Path

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.errors import StatementError, ConfigurationError
from .structure import (
    StatementStructure,
    LineItem,
)
from .config.loader import load_statement_config
from .services.calculation_service import CalculationService
from .services.export_service import ExportService
from fin_statement_model.statements.formatter import StatementFormatter

# Configure logging
logger = logging.getLogger(__name__)


class StatementManager:
    """Manages financial statement structures and their integration with the graph.

    This class handles loading statement configurations, creating the necessary
    nodes in the graph, calculating values, and formatting the results.
    """

    def __init__(self, graph: Graph):
        """Initialize a statement manager.

        Args:
            graph: The graph to use for calculations
        """
        self.graph = graph
        self.statements: dict[str, StatementStructure] = {}
        self.calculation_service = CalculationService(self.graph)
        self.export_service = ExportService(self)

    def load_statement(self, config_path: str) -> StatementStructure:
        """Load a statement configuration and register it with the manager.

        Args:
            config_path: Path to the statement configuration file

        Returns:
            StatementStructure: The loaded statement structure

        Raises:
            ConfigurationError: If the configuration file is invalid or cannot be loaded
            StatementError: If the statement cannot be registered
        """
        logger.info(f"Loading statement configuration from {config_path}")
        try:
            statement = load_statement_config(config_path)
            self.register_statement(statement)
        except ConfigurationError:
            # Re-raise ConfigurationError directly
            raise
        except Exception as e:
            logger.exception(f"Unexpected error loading statement configuration from {config_path}")
            raise StatementError(
                message="Failed to load statement configuration",
                statement_id=os.path.basename(config_path),
            ) from e
        else:
            return statement

    def register_statement(self, statement: StatementStructure) -> None:
        """Register a statement structure with the manager.

        Args:
            statement: The statement structure to register

        Raises:
            StatementError: If a statement with the same ID is already registered
                or if the statement is invalid
        """
        try:
            if statement.id in self.statements:
                raise StatementError(
                    message="Statement with this ID is already registered",
                    statement_id=statement.id,
                )

            self.statements[statement.id] = statement
            logger.info(f"Registered statement '{statement.name}' with ID '{statement.id}'")
        except Exception as e:
            if isinstance(e, StatementError):
                # Re-raise StatementError
                raise
            else:
                # Wrap other exceptions
                statement_id = getattr(statement, "id", "unknown")
                logger.exception(f"Error registering statement '{statement_id}'")
                raise StatementError(
                    message="Failed to register statement", statement_id=statement_id
                ) from e

    def get_statement(self, statement_id: str) -> Optional[StatementStructure]:
        """Get a registered statement by ID.

        Args:
            statement_id: The ID of the statement to get

        Returns:
            Optional[StatementStructure]: The statement structure, or None if not found
        """
        return self.statements.get(statement_id)

    def create_calculations(self, statement_id: str) -> list[str]:
        """Delegate calculation creation to the CalculationService.

        Args:
            statement_id: The ID of the statement to create calculations for

        Returns:
            List[str]: List of created calculation node IDs
        """
        statement = self.get_statement(statement_id)
        if statement is None:
            raise StatementError(message="Statement not found", statement_id=statement_id)
        return self.calculation_service.create_calculations(statement)

    def build_data_dictionary(self, statement_id: str) -> dict[str, dict[str, float]]:
        """Build a data dictionary for a statement from the graph.

        Args:
            statement_id: The ID of the statement to build data for

        Returns:
            Dict[str, Dict[str, float]]: Dictionary mapping node IDs to period values

        Raises:
            StatementError: If the statement ID is not registered
        """
        statement = self.get_statement(statement_id)
        if statement is None:
            raise StatementError(message="Statement not found", statement_id=statement_id)

        data = {}

        # Get all items that need data
        all_items = statement.get_all_items()

        # Build data dictionary
        for item in all_items:
            if isinstance(item, LineItem):
                node_id = item.node_id
                if self.graph.get_node(node_id) is not None:
                    # Get the values for all periods
                    values = {}
                    for period in self.graph.periods:
                        try:
                            value = self.graph.calculate(node_id, period)
                            values[period] = value
                        except Exception:
                            logger.warning(f"Error calculating {node_id} for {period}")

                    if values:
                        data[node_id] = values

        return data

    def format_statement(
        self,
        statement_id: str,
        format_type: str = "dataframe",
        **fmt_kwargs: dict[str, object],
    ) -> Union[pd.DataFrame, str]:
        """Format a statement with data from the graph.

        Args:
            statement_id: The ID of the statement to format
            format_type: The type of formatting to apply ('dataframe' or 'html')
            **fmt_kwargs: Additional arguments for the formatter

        Returns:
            Union[pd.DataFrame, str]: The formatted statement (DataFrame or HTML string)

        Raises:
            StatementError: If the statement ID is not registered
            ValueError: If the format type is not supported
        """
        # Retrieve the structure
        statement = self.get_statement(statement_id)
        if statement is None:
            raise StatementError(f"Statement {statement_id!r} not found")

        # Build raw data
        data_dict = self.build_data_dictionary(statement_id)

        # Format using the core StatementFormatter
        formatter = StatementFormatter(statement)
        if format_type == "dataframe":
            return formatter.generate_dataframe(data_dict, **fmt_kwargs)
        elif format_type == "html":
            return formatter.format_html(data_dict, **fmt_kwargs)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")

    def export_to_excel(self, statement_id: str, file_path: str, **kwargs: dict[str, Any]) -> None:
        """Export a statement to an Excel file.

        Args:
            statement_id: The ID of the statement to export
            file_path: Path to save the Excel file
            **kwargs: Additional arguments for the formatter

        Raises:
            StatementError: If the statement ID is not registered
            WriteError: If the export fails
        """
        return self.export_service.to_excel(statement_id, file_path, **kwargs)

    def export_to_json(
        self,
        statement_id: str,
        file_path: str,
        orient: str = "columns",
        **kwargs: dict[str, Any],
    ) -> None:
        """Export a statement to a JSON file.

        Args:
            statement_id: The ID of the statement to export
            file_path: Path to save the JSON file
            orient: JSON orientation format
            **kwargs: Additional arguments for the formatter

        Raises:
            StatementError: If the statement ID is not registered
            WriteError: If the export fails
        """
        return self.export_service.to_json(statement_id, file_path, orient=orient, **kwargs)

    def get_all_statement_ids(self) -> list[str]:
        """Get the IDs of all registered statements.

        Returns:
            List[str]: List of statement IDs
        """
        return list(self.statements.keys())

    def load_statements_from_directory(self, directory_path: str) -> list[str]:
        """Load all statement configurations from a directory.

        Args:
            directory_path: Path to the directory containing statement configurations

        Returns:
            List[str]: List of loaded statement IDs

        Raises:
            ConfigurationError: If the directory does not exist or is not a directory
        """
        loaded_ids = []
        path = Path(directory_path)

        if not path.exists() or not path.is_dir():
            raise ConfigurationError(
                message="Invalid directory path",
                config_path=directory_path,
                errors=[f"Path does not exist or is not a directory: {directory_path}"],
            )

        errors = []

        # Load all JSON and YAML files
        for file_path in path.glob("*.json"):
            try:
                statement = self.load_statement(str(file_path))
                loaded_ids.append(statement.id)
            except Exception as e:
                errors.append(f"Error loading {file_path}: {e!s}")
                logger.exception(f"Error loading statement from {file_path}")

        for file_path in path.glob("*.y*ml"):
            try:
                statement = self.load_statement(str(file_path))
                loaded_ids.append(statement.id)
            except Exception as e:
                errors.append(f"Error loading {file_path}: {e!s}")
                logger.exception(f"Error loading statement from {file_path}")

        if not loaded_ids and errors:
            # If no statements were loaded and there were errors, raise an exception
            raise ConfigurationError(
                message="Failed to load any statements from directory",
                config_path=directory_path,
                errors=errors,
            )

        logger.info(f"Loaded {len(loaded_ids)} statements from {directory_path}")
        return loaded_ids
