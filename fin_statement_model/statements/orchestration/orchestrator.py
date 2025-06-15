"""Main orchestration for statement processing.

This module coordinates the workflow of building statements from in-memory
configurations, populating graphs, and generating DataFrames.
"""

import logging
from typing import Any, Optional

import pandas as pd

from fin_statement_model.core.errors import StatementError
from fin_statement_model.core.graph import Graph
from fin_statement_model.statements.formatting.formatter import StatementFormatter
from fin_statement_model.statements.orchestration.loader import (
    load_build_register_statements,
)
from fin_statement_model.statements.population.populator import (
    populate_graph_from_statement,
)
from fin_statement_model.statements.registry import StatementRegistry
from fin_statement_model.statements.structure.builder import StatementStructureBuilder

logger = logging.getLogger(__name__)

__all__ = ["create_statement_dataframe", "populate_graph"]


def populate_graph(registry: StatementRegistry, graph: Graph) -> list[tuple[str, str]]:
    """Populate the graph with nodes based on registered statements."""
    all_errors: list[tuple[str, str]] = []
    statements = registry.get_all_statements()
    if not statements:
        logger.warning("No statements registered to populate the graph.")
        return []

    for statement in statements:
        errors = populate_graph_from_statement(statement, graph)
        for item_id, msg in errors:
            all_errors.append((item_id, msg))

    if all_errors:
        logger.warning(f"Encountered {len(all_errors)} errors during graph population.")
    return all_errors


def create_statement_dataframe(
    graph: Graph,
    raw_configs: dict[str, dict[str, Any]],
    format_kwargs: Optional[dict[str, Any]] = None,
    enable_node_validation: Optional[bool] = None,
    node_validation_strict: Optional[bool] = None,
) -> dict[str, pd.DataFrame]:
    """Build statements from configurations, populate graph, and format DataFrames.

    Args:
        graph: Graph instance to populate.
        raw_configs: Mapping of statement IDs to configuration dicts.
        format_kwargs: Optional kwargs for formatter.
        enable_node_validation: If True, validate node IDs.
        node_validation_strict: If True, treat validation failures as errors.

    Returns:
        Mapping of statement IDs to pandas DataFrames.

    Raises:
        StatementError: If loading or formatting fails.
    """
    registry = StatementRegistry()
    enable_node_validation = (
        enable_node_validation if enable_node_validation is not None else False
    )
    node_validation_strict = (
        node_validation_strict if node_validation_strict is not None else False
    )
    builder = StatementStructureBuilder(
        enable_node_validation=enable_node_validation,
        node_validation_strict=node_validation_strict,
    )
    format_kwargs = format_kwargs or {}

    # Step 1: Load, build, register
    loaded_ids = load_build_register_statements(
        raw_configs,
        registry,
        builder,
        enable_node_validation=enable_node_validation,
        node_validation_strict=node_validation_strict,
    )
    if not loaded_ids:
        raise StatementError("No valid statements could be loaded.")

    # Step 2: Populate graph
    populate_graph(registry, graph)

    # Step 3: Format results
    results: dict[str, pd.DataFrame] = {}
    for stmt_id in loaded_ids:
        statement = registry.get(stmt_id)
        if statement is None:
            logger.error(f"Statement '{stmt_id}' not found in registry.")
            raise StatementError(f"Statement '{stmt_id}' not found in registry.")
        formatter = StatementFormatter(statement)
        if format_kwargs:
            context = formatter._prepare_formatting_context(**format_kwargs)
        else:
            # Use default project configuration
            context = formatter._prepare_formatting_context()

        df = formatter.generate_dataframe(graph, context=context)
        results[stmt_id] = df

    return results
