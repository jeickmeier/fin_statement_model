"""
Statement manager for Financial Statement Model.

This module provides a manager for handling statement structures and formatting
in the Financial Statement Model.
"""

import os
import logging
from typing import Dict, List, Any, Union, Optional
from pathlib import Path

from ..core.graph import Graph
from ..core.errors import (
    StatementError,
    ConfigurationError,
    NodeError,
    CalculationError,
    CircularDependencyError,
    ExportError,
)
from .statement_structure import (
    StatementStructure,
    LineItem,
    CalculatedLineItem,
    SubtotalLineItem,
)
from .statement_config import load_statement_config
from .statement_formatter import StatementFormatter

# Configure logging
logger = logging.getLogger(__name__)


class StatementManager:
    """
    Manages financial statement structures and their integration with the graph.

    This class handles loading statement configurations, creating the necessary
    nodes in the graph, calculating values, and formatting the results.
    """

    def __init__(self, graph: Graph):
        """
        Initialize a statement manager.

        Args:
            graph: The graph to use for calculations
        """
        self.graph = graph
        self.statements: Dict[str, StatementStructure] = {}
        self.formatters: Dict[str, StatementFormatter] = {}

    def load_statement(self, config_path: str) -> StatementStructure:
        """
        Load a statement configuration and register it with the manager.

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
            return statement
        except ConfigurationError:
            # Re-raise ConfigurationError directly
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error loading statement configuration from {config_path}: {e}"
            )
            raise StatementError(
                message="Failed to load statement configuration",
                statement_id=os.path.basename(config_path),
            ) from e

    def register_statement(self, statement: StatementStructure) -> None:
        """
        Register a statement structure with the manager.

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
            self.formatters[statement.id] = StatementFormatter(statement)
            logger.info(
                f"Registered statement '{statement.name}' with ID '{statement.id}'"
            )
        except Exception as e:
            if isinstance(e, StatementError):
                # Re-raise StatementError
                raise
            else:
                # Wrap other exceptions
                statement_id = getattr(statement, "id", "unknown")
                logger.error(f"Error registering statement '{statement_id}': {e}")
                raise StatementError(
                    message="Failed to register statement", statement_id=statement_id
                ) from e

    def get_statement(self, statement_id: str) -> Optional[StatementStructure]:
        """
        Get a registered statement by ID.

        Args:
            statement_id: The ID of the statement to get

        Returns:
            Optional[StatementStructure]: The statement structure, or None if not found
        """
        return self.statements.get(statement_id)

    def create_calculations(self, statement_id: str) -> List[str]:
        """
        Create calculation nodes in the graph for a statement.

        Args:
            statement_id: The ID of the statement to create calculations for

        Returns:
            List[str]: List of created calculation node IDs

        Raises:
            StatementError: If the statement ID is not registered
            CircularDependencyError: If a circular dependency is detected
            CalculationError: If a calculation cannot be created
        """
        statement = self.get_statement(statement_id)
        if statement is None:
            raise StatementError(
                message="Statement not found", statement_id=statement_id
            )

        created_nodes = []

        # Get all calculation items
        calc_items = statement.get_calculation_items()

        # Process in order of dependencies to ensure all inputs exist
        processed = set()

        # Helper to check if all dependencies are processed
        def deps_processed(item: Union[CalculatedLineItem, SubtotalLineItem]) -> bool:
            return all(dep_id in processed for dep_id in item.input_ids)

        try:
            # Process items until all are processed or no more can be processed
            while calc_items and len(processed) < len(calc_items):
                remaining = []
                progress_made = False

                for item in calc_items:
                    if deps_processed(item):
                        # Create calculation node
                        self._create_calculation_node(item)
                        processed.add(item.id)
                        created_nodes.append(item.id)
                        progress_made = True
                    else:
                        remaining.append(item)

                # If no progress was made, we have a circular dependency
                if not progress_made:
                    # Identify the cycle
                    cycle = self._detect_cycle(remaining)
                    logger.error(
                        f"Circular dependency detected in statement '{statement_id}': {cycle}"
                    )
                    raise CircularDependencyError(
                        message="Circular dependency detected in calculations",
                        cycle=cycle,
                    )

                calc_items = remaining

            logger.info(
                f"Created {len(created_nodes)} calculation nodes for statement '{statement_id}'"
            )
            return created_nodes

        except CircularDependencyError:
            # Re-raise CircularDependencyError
            raise
        except Exception as e:
            logger.error(
                f"Error creating calculations for statement '{statement_id}': {e}"
            )
            if isinstance(e, (NodeError, CalculationError)):
                # Re-raise node and calculation errors
                raise
            else:
                # Wrap other exceptions
                raise CalculationError(
                    message="Failed to create calculations",
                    details={"statement_id": statement_id},
                ) from e

    def _detect_cycle(
        self, items: List[Union[CalculatedLineItem, SubtotalLineItem]]
    ) -> List[str]:
        """
        Detect a cycle in the calculation dependencies.

        Args:
            items: List of items with unresolved dependencies

        Returns:
            List[str]: List of item IDs forming a cycle, or empty list if no cycle is found
        """
        # Build dependency graph
        graph = {item.id: set(item.input_ids) for item in items}

        # Find cycles using DFS
        visited = set()
        rec_stack = set()

        def dfs_cycle(node, path=None):
            if path is None:
                path = []

            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]

            if node in visited:
                return []  # pragma: no cover

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            # Check all dependencies
            for neighbor in graph.get(node, set()):
                if neighbor in graph:  # Only check neighbors that are in our graph
                    cycle = dfs_cycle(neighbor, path)
                    if cycle:
                        return cycle

            # Remove node from recursion stack and path
            rec_stack.remove(node)  # pragma: no cover
            path.pop()  # pragma: no cover
            return []  # pragma: no cover

        # Check each unvisited node
        for node in graph:
            if node not in visited:
                cycle = dfs_cycle(node)
                if cycle:
                    return cycle

        # No cycle found
        return []  # pragma: no cover

    def _create_calculation_node(
        self, item: Union[CalculatedLineItem, SubtotalLineItem]
    ) -> None:
        """
        Create a calculation node in the graph.

        Args:
            item: The calculation item to create a node for

        Raises:
            NodeError: If an input node does not exist
            CalculationError: If the calculation type is not supported
        """
        calc_type = item.calculation_type
        inputs = item.input_ids

        # Check if all inputs exist
        missing_inputs = []
        for input_id in inputs:
            if self.graph.get_node(input_id) is None:
                missing_inputs.append(input_id)

        if missing_inputs:
            raise NodeError(
                message=f"Input nodes not found for calculation '{item.id}': {', '.join(missing_inputs)}",
                node_id=item.id,
            )

        try:
            # Create the calculation node based on type
            if calc_type in ["addition", "subtraction", "multiplication", "division"]:
                # Standard calculation types
                self.graph.calculation_engine.add_calculation(
                    item.id, inputs, calc_type, **item.parameters
                )
            elif calc_type == "weighted_average":
                # Weighted average calculation
                weights = item.parameters.get("weights")
                self.graph.calculation_engine.add_calculation(
                    item.id, inputs, "weighted_average", weights=weights
                )
            elif calc_type == "custom_formula":
                # Custom formula calculation (not directly supported yet)
                raise CalculationError(
                    message="Custom formula calculations are not yet supported",
                    node_id=item.id,
                )
            else:
                raise CalculationError(
                    message=f"Unsupported calculation type: {calc_type}",
                    node_id=item.id,
                )
        except Exception as e:
            if isinstance(e, (NodeError, CalculationError)):
                # Re-raise node and calculation errors
                raise
            else:
                # Wrap other exceptions
                logger.error(f"Error creating calculation node '{item.id}': {e}")
                raise CalculationError(
                    message="Failed to create calculation node",
                    node_id=item.id,
                    details={"calculation_type": calc_type},
                ) from e

    def build_data_dictionary(self, statement_id: str) -> Dict[str, Dict[str, float]]:
        """
        Build a data dictionary for a statement from the graph.

        Args:
            statement_id: The ID of the statement to build data for

        Returns:
            Dict[str, Dict[str, float]]: Dictionary mapping node IDs to period values

        Raises:
            StatementError: If the statement ID is not registered
        """
        statement = self.get_statement(statement_id)
        if statement is None:
            raise StatementError(
                message="Statement not found", statement_id=statement_id
            )

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
                        except Exception as e:
                            logger.warning(
                                f"Error calculating {node_id} for {period}: {e}"
                            )

                    if values:
                        data[node_id] = values

        return data

    def format_statement(
        self, statement_id: str, format_type: str = "dataframe", **kwargs
    ) -> Any:
        """
        Format a statement with data from the graph.

        Args:
            statement_id: The ID of the statement to format
            format_type: The type of formatting to apply ('dataframe' or 'html')
            **kwargs: Additional arguments for the formatter

        Returns:
            Any: The formatted statement (DataFrame or HTML string)

        Raises:
            StatementError: If the statement ID is not registered
            ValueError: If the format type is not supported
        """
        statement = self.get_statement(statement_id)
        if statement is None:
            raise StatementError(
                message="Statement not found", statement_id=statement_id
            )

        formatter = self.formatters[statement_id]

        # Build data dictionary
        data = self.build_data_dictionary(statement_id)

        # Format based on type
        if format_type == "dataframe":
            return formatter.generate_dataframe(data, **kwargs)
        elif format_type == "html":
            return formatter.format_html(data, **kwargs)
        else:
            raise StatementError(
                message=f"Unsupported format type: {format_type}",
                statement_id=statement_id,
            )

    def export_to_excel(self, statement_id: str, file_path: str, **kwargs) -> None:
        """
        Export a statement to an Excel file.

        Args:
            statement_id: The ID of the statement to export
            file_path: Path to save the Excel file
            **kwargs: Additional arguments for the formatter

        Raises:
            StatementError: If the statement ID is not registered
            ExportError: If the export fails
        """
        try:
            df = self.format_statement(statement_id, format_type="dataframe", **kwargs)
            df.to_excel(file_path, index=False)
            logger.info(f"Exported statement '{statement_id}' to {file_path}")
        except Exception as e:
            if isinstance(e, StatementError):
                # Re-raise StatementError
                raise
            else:
                # Wrap the exception
                logger.error(
                    f"Error exporting statement '{statement_id}' to {file_path}: {e}"
                )
                raise ExportError(
                    message="Failed to export statement to Excel",
                    target=file_path,
                    format_type="excel",
                    original_error=e,
                ) from e

    def get_all_statement_ids(self) -> List[str]:
        """
        Get the IDs of all registered statements.

        Returns:
            List[str]: List of statement IDs
        """
        return list(self.statements.keys())

    def load_statements_from_directory(self, directory_path: str) -> List[str]:
        """
        Load all statement configurations from a directory.

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
                errors.append(f"Error loading {file_path}: {str(e)}")
                logger.error(f"Error loading statement from {file_path}: {e}")

        for file_path in path.glob("*.y*ml"):
            try:
                statement = self.load_statement(str(file_path))
                loaded_ids.append(statement.id)
            except Exception as e:
                errors.append(f"Error loading {file_path}: {str(e)}")
                logger.error(f"Error loading statement from {file_path}: {e}")

        if not loaded_ids and errors:
            # If no statements were loaded and there were errors, raise an exception
            raise ConfigurationError(
                message="Failed to load any statements from directory",
                config_path=directory_path,
                errors=errors,
            )

        logger.info(f"Loaded {len(loaded_ids)} statements from {directory_path}")
        return loaded_ids
