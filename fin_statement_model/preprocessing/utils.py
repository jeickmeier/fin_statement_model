"""Utility helpers for the *preprocessing* layer.

This module currently hosts :func:`ensure_dataframe` which provides a
high-performance, opinionated helper for coercing input objects to
``pandas.DataFrame`` instances while preserving the original type
information (Series vs. DataFrame).

The function is deliberately kept *very* lightweight because it sits on the
hot-path for many transformer implementations.  In particular it contains a
fast-path that simply returns the original object **unmodified** when it is
already a ``pandas.DataFrame`` - avoiding an unnecessary and potentially
expensive copy.
"""

# PEP 563/PEP 649: Keep future imports directly below the module docstring.
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pandas as pd

from fin_statement_model.io import write_data

if TYPE_CHECKING:  # pragma: no cover - heavy imports for type checking only
    from fin_statement_model.core.graph import Graph
    from fin_statement_model.templates.models import PreprocessingSpec

__all__: list[str] = [
    "apply_pipeline_to_graph",
    "ensure_dataframe",
]


def ensure_dataframe(data: pd.DataFrame | pd.Series[Any]) -> tuple[pd.DataFrame, bool]:
    """Return ``(df, was_series)`` ensuring *data* is a DataFrame.

    Args:
        data: The input object which must be either a ``pandas.DataFrame`` or
            ``pandas.Series`` instance.

    Returns:
        Tuple[DataFrame, bool]:
            1. A ``pandas.DataFrame`` representation of *data*.
            2. ``True`` if the original *data* was a ``pandas.Series``; ``False``
               if it was already a ``DataFrame``.

    Raises:
        TypeError: If *data* is neither a ``DataFrame`` nor a ``Series``.
    """
    # Fast-path: already a DataFrame - *do not* create a copy
    if isinstance(data, pd.DataFrame):
        return data, False

    # Series → single-column DataFrame conversion
    if isinstance(data, pd.Series):
        return data.to_frame(), True

    raise TypeError("data must be a pandas DataFrame or Series")


def _df_from_graph(graph: Graph) -> pd.DataFrame:
    """Return a period-index DataFrame where columns are node names.

    Helper converts *graph* via IO writer and transposes so that the resulting
    DataFrame matches the conventional shape expected by most transformers
    (rows=time, columns=features).
    """
    df = cast("pd.DataFrame", write_data("dataframe", graph, target=None))  # nodes as index, periods as columns
    return df.T  # periods become index (rows), node names become columns


def apply_pipeline_to_graph(graph: Graph, spec: PreprocessingSpec, *, in_place: bool = True) -> Graph:
    """Execute *spec* pipeline on *graph* and update values in-place.

    The function converts *graph* to a DataFrame (period rows x node columns),
    applies the declared preprocessing pipeline via :class:`TransformationService`
    and writes all resulting values back into the graph.  New columns emitted by
    the pipeline are materialised as *FinancialStatementItem* nodes.

    Args:
        graph: Target graph instance to mutate.
        spec: PreprocessingSpec describing the ordered pipeline to apply.
        in_place: When ``False`` a deep clone of *graph* is first created and
            returned, leaving the original untouched.

    Returns:
        Graph: The graph instance that has been preprocessed (same object as
        *graph* when *in_place* is True).
    """
    if not in_place:
        graph = graph.clone(deep=True)

    # 1. Convert graph ➜ DataFrame ------------------------------------------
    df = _df_from_graph(graph)

    # 2. Build pipeline config list (list[dict[str, Any]]) -------------------
    pipeline_cfg: list[dict[str, Any]] = [{"name": step.name, **step.params} for step in spec.pipeline]

    # 3. Execute via TransformationService -----------------------------------
    from fin_statement_model.preprocessing.transformer_service import TransformationService

    svc = TransformationService()
    transformed_df = svc.apply_transformation_pipeline(df, pipeline_cfg)
    if not isinstance(transformed_df, pd.DataFrame):
        raise TypeError("Preprocessing pipeline must return a pandas DataFrame when applied to Graph data.")

    # 4. Write back into graph ----------------------------------------------
    periods = transformed_df.index.astype(str).tolist()
    # Ensure graph knows all periods
    graph.add_periods([p for p in periods if p not in graph.periods])

    for node_name in transformed_df.columns:
        series = transformed_df[node_name]
        values_dict: dict[str, float] = {str(period): float(val) for period, val in series.items() if pd.notna(val)}
        if node_name in graph.nodes:
            from fin_statement_model.core.nodes import FinancialStatementItemNode

            node_obj = graph.nodes[node_name]
            if isinstance(node_obj, FinancialStatementItemNode):
                graph.update_financial_statement_item(node_name, values_dict, replace_existing=False)
            else:
                # Skip calculation or other node types - preprocessing does not overwrite derived values.
                continue
        else:
            # Add new FS item node
            graph.add_financial_statement_item(node_name, values_dict)

    # Clear caches to account for mutated inputs
    graph.clear_all_caches()

    return graph
