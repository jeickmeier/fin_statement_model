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
from fin_statement_model.core.errors import (
    StatementError,
    ConfigurationError,
    NodeError,
    CalculationError,
    CircularDependencyError,
)
from .structure import (
    StatementStructure,
    LineItem,
    CalculatedLineItem,
    SubtotalLineItem,
)
from .config.config import StatementConfig
from fin_statement_model.io.readers.statement_config_reader import read_statement_config_from_path
from fin_statement_model.io.exceptions import ReadError
from fin_statement_model.statements.formatter import StatementFormatter
from fin_statement_model.io.writers.statement_writer import (
    write_statement_to_excel, write_statement_to_json
)
from fin_statement_model.io.exceptions import WriteError

# Configure logging
logger = logging.getLogger(__name__)


class StatementManager:
    """Manages financial statement structures and their integration with the graph.

    This class handles loading statement configurations (using the IO layer),
    building statement structures, creating the necessary nodes in the graph,
    calculating values, formatting the results, and exporting.
    """

    def __init__(self, graph: Graph):
        """Initialize a statement manager.

        Args:
            graph: The graph to use for calculations
        """
        self.graph = graph
        self.statements: dict[str, StatementStructure] = {}
        self._input_values: dict[str, Any] = {}

    def load_statement(self, config_path: str) -> StatementStructure:
        """Load a statement configuration from a path and register it.

        Uses the IO layer to read the file and StatementConfig to build the structure.

        Args:
            config_path: Path to the statement configuration file.

        Returns:
            StatementStructure: The loaded and built statement structure.

        Raises:
            ConfigurationError: If reading, validating, or building the config fails.
            StatementError: If registering the statement fails.
        """
        logger.info(f"Loading statement configuration from {config_path}")
        try:
            # Step 1: Read raw config data using IO layer
            try:
                config_data = read_statement_config_from_path(config_path)
            except ReadError as e:
                logger.error(f"IO Error reading config file {config_path}: {e}")
                # Wrap IO read errors in ConfigurationError for consistent API
                raise ConfigurationError(message=f"Failed to read config: {e}", config_path=config_path) from e

            # Step 2: Build structure using StatementConfig (raises ConfigurationError on failure)
            cfg = StatementConfig(config_data=config_data)
            statement = cfg.build_statement_structure()

            # Step 3: Register the built statement
            self.register_statement(statement) # Raises StatementError on failure

        except ConfigurationError:
            # Re-raise ConfigurationError from reading or building
            raise
        except StatementError:
             # Re-raise StatementError from registration
             raise
        except Exception as e:
            # Catch any other unexpected errors during the process
            logger.exception(f"Unexpected error loading statement configuration from {config_path}")
            # Wrap in StatementError as it's a failure in the manager's load process
            raise StatementError(
                message=f"Unexpected error loading statement: {e}",
                statement_id=os.path.basename(config_path), # Use path basename as ID guess
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
        """Create calculation nodes in the graph for all calculated items in the statement.

        Uses the statement structure to determine dependencies and adds calculation nodes
        to the underlying graph.

        Args:
            statement_id: The ID of the statement to create calculations for.

        Returns:
            List[str]: List of created calculation node IDs.

        Raises:
            StatementError: If the statement ID is not found.
            CircularDependencyError: If a circular dependency is detected.
            NodeError: If dependencies cannot be satisfied.
            CalculationError: If there is an issue adding a calculation to the graph.
        """
        statement = self.get_statement(statement_id)
        if statement is None:
            raise StatementError(message="Statement not found", statement_id=statement_id)

        items = statement.get_calculation_items()

        if not items:
            return []

        processed: set[str] = set(self.graph.get_node_ids())
        processed.update(self._input_values.keys())

        created_nodes: list[str] = []
        remaining = items.copy()

        while remaining:
            progress = False
            eligible_items = []

            for item in remaining:
                deps_satisfied = all(
                    dep_id in processed
                    for dep_id in item.input_ids
                )
                if deps_satisfied:
                    eligible_items.append(item)

            if eligible_items:
                for item in eligible_items:
                    try:
                        if item.id not in self.graph.get_node_ids():
                            self._create_calculation_node(item)
                            created_nodes.append(item.id)
                        processed.add(item.id)
                        remaining.remove(item)
                        progress = True
                    except Exception as e:
                        logger.exception(f"Failed to create calculation node for {item.id}")
                        if isinstance(e, (NodeError, CalculationError, CircularDependencyError)):
                            raise
                        else:
                            raise CalculationError(
                                message=f"Unexpected error creating node {item.id}",
                                node_id=item.id
                            ) from e

            if not progress and remaining:
                cycle = self._detect_cycle(remaining)
                if cycle:
                    logger.error(f"Circular dependency detected: {cycle}")
                    raise CircularDependencyError(
                        message=f"Circular dependency detected in calculations: {cycle}",
                        cycle=cycle,
                    )
                else:
                    missing_deps = set()
                    for item in remaining:
                        missing_deps.update(
                            dep_id
                            for dep_id in item.input_ids
                            if dep_id not in processed
                        )
                    if missing_deps:
                        raise NodeError(
                            message=f"Missing dependencies for calculations: {missing_deps}",
                            node_id=f"(Multiple: {', '.join(it.id for it in remaining)})",
                        )
                    else:
                        logger.error(
                            f"Calculation stalled for items: {[it.id for it in remaining]}. "
                            f"No progress, no cycle, no missing dependencies in 'processed' set."
                        )
                        raise CalculationError(
                            message="Calculation stalled without clear cause.",
                            node_id=remaining[0].id,
                        )
        logger.info(f"Created/verified {len(created_nodes)} calculation nodes for statement '{statement_id}'")
        return created_nodes

    def _detect_cycle(self, items: list[Union[CalculatedLineItem, SubtotalLineItem]]) -> list[str]:
        """Detects a cycle in the calculation dependency graph (Integrated from CalculationService)."""
        if not items:
            return []

        item_ids = {item.id for item in items}
        graph_map = {item.id: {i for i in item.input_ids if i in item_ids} for item in items}

        visited = set()
        rec_stack = set()

        def dfs(node: str, path: list[str]) -> list[str]:
            if node in rec_stack:
                try:
                    start = path.index(node)
                    return path[start:]
                except ValueError:
                    logger.exception(
                        f"Internal error: Node {node} in rec_stack but not in path {path}"
                    )
                    return [node]
            if node in visited:
                return []

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for nbr in graph_map.get(node, set()):
                cycle = dfs(nbr, path)
                if cycle:
                    return cycle

            rec_stack.remove(node)
            path.pop()
            return []

        for nid in graph_map:
            if nid not in visited:
                cycle = dfs(nid, [])
                if cycle:
                    return cycle
        return []

    def _create_calculation_node(self, item: Union[CalculatedLineItem, SubtotalLineItem]) -> None:
        """Create a calculation node in the graph for a given calculation item (Integrated from CalculationService)."""
        calc_type = item.calculation_type
        inputs = item.input_ids

        try:
            if calc_type in ["addition", "subtraction", "multiplication", "division"]:
                self.graph.add_calculation(item.id, inputs, calc_type, **item.parameters)
            elif calc_type == "weighted_average":
                weights = item.parameters.get("weights")
                if not weights:
                    raise CalculationError(
                        message="Weights required for weighted_average calculation",
                        node_id=item.id,
                    )
                self.graph.add_calculation(item.id, inputs, "weighted_average", weights=weights)
            elif isinstance(item, SubtotalLineItem):
                self.graph.add_calculation(item.id, inputs, "addition", **item.parameters)
            else:
                raise CalculationError(
                    message=f"Unsupported calculation type: {calc_type}",
                    node_id=item.id,
                )
        except (NodeError, CalculationError, ValueError, TypeError) as e:
            logger.exception(f"Graph failed to add calculation for '{item.id}'")
            raise CalculationError(
                message=f"Graph failed to create calculation node for {item.id}",
                node_id=item.id,
                details={"original_error": str(e)},
            ) from e

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

        all_items = statement.get_all_items()

        for item in all_items:
            if isinstance(item, LineItem):
                node_id = item.node_id
                if self.graph.get_node(node_id) is not None:
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
        statement = self.get_statement(statement_id)
        if statement is None:
            raise StatementError(f"Statement {statement_id!r} not found")

        data_dict = self.build_data_dictionary(statement_id)

        formatter = StatementFormatter(statement)
        if format_type == "dataframe":
            return formatter.generate_dataframe(data_dict, **fmt_kwargs)
        elif format_type == "html":
            return formatter.format_html(data_dict, **fmt_kwargs)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")

    def export_to_excel(self, statement_id: str, file_path: str, **kwargs: Any) -> None:
        """Export a statement to an Excel file using the IO layer.

        Args:
            statement_id: The ID of the statement to export.
            file_path: Path to save the Excel file.
            **kwargs: Additional arguments passed to the formatter and writer.

        Raises:
            StatementError: If the statement ID is not registered.
            ValueError: If formatting fails.
            WriteError: If the IO writer fails.
        """
        try:
            statement_df = self.format_statement(statement_id, format_type="dataframe", **kwargs)
        except (StatementError, ValueError) as e:
            logger.exception(f"Failed to format statement {statement_id} for Excel export")
            raise

        try:
            write_statement_to_excel(statement_df, file_path, **kwargs)
            logger.info(f"Successfully exported statement '{statement_id}' to Excel: {file_path}")
        except WriteError as e:
            logger.exception(f"IO Error exporting statement '{statement_id}' to Excel")
            raise
        except Exception as e:
            logger.exception(f"Unexpected Error exporting statement '{statement_id}' to Excel")
            raise WriteError(
                message="Unexpected error during Excel export",
                target=file_path,
                format_type="excel",
                original_error=e
            ) from e

    def export_to_json(
        self,
        statement_id: str,
        file_path: str,
        orient: str = "columns",
        **kwargs: Any,
    ) -> None:
        """Export a statement to a JSON file using the IO layer.

        Args:
            statement_id: The ID of the statement to export.
            file_path: Path to save the JSON file.
            orient: JSON orientation format.
            **kwargs: Additional arguments passed to the formatter and writer.

        Raises:
            StatementError: If the statement ID is not registered.
            ValueError: If formatting fails.
            WriteError: If the IO writer fails.
        """
        try:
            statement_df = self.format_statement(statement_id, format_type="dataframe", **kwargs)
        except (StatementError, ValueError) as e:
            logger.exception(f"Failed to format statement {statement_id} for JSON export")
            raise

        try:
            write_statement_to_json(statement_df, file_path, orient=orient, **kwargs)
            logger.info(f"Successfully exported statement '{statement_id}' to JSON: {file_path}")
        except WriteError as e:
            logger.exception(f"IO Error exporting statement '{statement_id}' to JSON")
            raise
        except Exception as e:
            logger.exception(f"Unexpected Error exporting statement '{statement_id}' to JSON")
            raise WriteError(
                message="Unexpected error during JSON export",
                target=file_path,
                format_type="json",
                original_error=e
            ) from e

    def get_all_statement_ids(self) -> list[str]:
        """Get the IDs of all registered statements.

        Returns:
            List[str]: List of statement IDs
        """
        return list(self.statements.keys())

    def load_statements_from_directory(self, directory_path: str) -> list[str]:
        """Load all statement configurations from a directory.

        Args:
            directory_path: Path to the directory containing statement configs.

        Returns:
            List[str]: List of loaded statement IDs.

        Raises:
            ConfigurationError: If the directory path is invalid or if loading/
                                building any config fails.
        """
        loaded_ids = []
        path = Path(directory_path)
        errors = []

        if not path.exists() or not path.is_dir():
            raise ConfigurationError(
                message="Invalid directory path for loading statements",
                config_path=directory_path,
                errors=[f"Path does not exist or is not a directory: {directory_path}"],
            )

        config_files = list(path.glob("*.json")) + list(path.glob("*.y*ml"))

        if not config_files:
            logger.warning(f"No configuration files (.json, .yaml, .yml) found in directory: {directory_path}")
            return []

        for file_path in config_files:
            file_path_str = str(file_path)
            try:
                # Use the refactored load_statement logic for each file
                # load_statement handles reading, building, and registering
                statement = self.load_statement(file_path_str)
                loaded_ids.append(statement.id)
            except (ConfigurationError, StatementError) as e:
                # Catch errors from loading, building, or registering a single file
                errors.append(f"Error processing {file_path.name}: {e!s}")
                logger.error(f"Failed to load/register statement from {file_path_str}: {e}")
            except Exception as e:
                 # Catch unexpected errors for a single file
                 errors.append(f"Unexpected error processing {file_path.name}: {e!s}")
                 logger.exception(f"Unexpected error processing statement from {file_path_str}")

        # If specific configs failed but others succeeded, log errors but don't fail all
        if errors:
             logger.warning(f"Encountered {len(errors)} errors while loading statements from {directory_path}:\n - " + "\n - ".join(errors))

        # Raise error only if NO statements could be loaded AT ALL and there were errors
        if not loaded_ids and errors:
            raise ConfigurationError(
                message="Failed to load any valid statements from directory",
                config_path=directory_path,
                errors=errors,
            )

        logger.info(f"Loaded {len(loaded_ids)} statements from {directory_path}")
        return loaded_ids

    def set_input_values(self, values: dict[str, Any]) -> None:
        """Set input values to be considered during calculation dependency resolution.

        Args:
            values: Dictionary mapping node IDs to their values.
        """
        self._input_values = values
        logger.debug(f"Input values set for manager: {list(values.keys())}")
