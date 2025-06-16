import pathlib

import numpy as np
import pandas as pd
import pytest

from fin_statement_model.core.graph import GraphFacade as Graph
from fin_statement_model.core.metrics.interpretation import MetricInterpreter
from fin_statement_model.core.metrics.registry import MetricRegistry
from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode


@pytest.fixture(autouse=True)
def _add_doctest_namespace(doctest_namespace):  # pylint: disable=unused-argument
    """Populate doctest namespace with commonly used objects.

    This helper injects lightweight sample objects so that simple doctest examples
    referring to ``graph``, ``traverser``, ``registry`` or ``interpreter`` run
    without additional boilerplate inside each doc-string.  The objects are kept
    deliberately minimal to avoid heavy computation or external I/O.
    """

    # Basic graph with one revenue data node so ``FinancialStatementItemNode`` and
    # graph-related examples work straight out of the box.
    graph = Graph()
    revenue_node = graph.add_financial_statement_item("revenue", {"2023": 100.0})

    # Common helpers -----------------------------------------------------
    traverser = graph.traverser
    registry = MetricRegistry()

    # Minimal metric definition to satisfy interpreter examples
    from fin_statement_model.core.metrics.models import (
        MetricDefinition,
        MetricInterpretation,
    )

    dummy_metric_def = MetricDefinition(
        name="dummy",
        description="Dummy metric for doctest namespace",
        inputs=["revenue"],
        formula="revenue",
        tags=[],
        interpretation=MetricInterpretation(good_range=[1.0, 3.0]),
    )

    interpreter = MetricInterpreter(dummy_metric_def)

    # Inject into namespace
    doctest_namespace["pd"] = pd
    doctest_namespace["np"] = np
    doctest_namespace["graph"] = graph
    doctest_namespace["traverser"] = traverser
    doctest_namespace["registry"] = registry
    doctest_namespace["interpreter"] = interpreter
    doctest_namespace["FinancialStatementItemNode"] = FinancialStatementItemNode
    doctest_namespace["revenue"] = revenue_node
    # 'manipulator' is alias to graph itself for backwards-compat examples
    doctest_namespace["manipulator"] = graph
    # Helper nodes for doctest examples that refer to 'node' / 'updated_node'
    node = FinancialStatementItemNode("NewItem", {"2023": 50})
    updated_node = FinancialStatementItemNode("Revenue", {"2023": 200})
    doctest_namespace["node"] = node
    doctest_namespace["updated_node"] = updated_node

    # Ensure a 'Revenue' node exists in graph for replace/set examples
    revenue_existing = graph.get_node("Revenue")
    if revenue_existing is None:  # pragma: no cover – safety
        revenue_existing = graph.add_financial_statement_item(
            "Revenue", {"2023": 100.0}
        )

    # Add the generic 'node' object so add_node example has something to add
    graph.add_node(node)
    doctest_namespace["revenue_existing"] = revenue_existing

    for mid in [
        "current_ratio",
        "debt_equity_ratio",
        "gross_profit",
        "test",
        "another_metric",
    ]:
        registry.register_definition(
            MetricDefinition(
                name=mid,
                description=f"Dummy metric {mid}",
                inputs=["revenue"],
                formula="revenue",
                tags=[],
                interpretation=MetricInterpretation(good_range=[1.0, 3.0]),
            )
        )


# ---------------------------------------------------------------------------
# Skip doctest collection for complex / I-O heavy modules --------------------
# ---------------------------------------------------------------------------
_HEAVY_PATTERNS: tuple[str, ...] = (
    "fin_statement_model/core/metrics/",
    "fin_statement_model/preprocessing/",
    "fin_statement_model/forecasting/",
    "fin_statement_model/statements/",
    "fin_statement_model/config/",
    "fin_statement_model/core/graph/manipulator.py",
    "fin_statement_model/core/node_factory.py",
    "fin_statement_model/core/nodes/",
)


def pytest_ignore_collect(path: pathlib.Path, config):  # type: ignore[return-type]
    """Tell pytest to ignore doctest collection for heavy/complex files.

    Returning ``True`` instructs pytest to *ignore* the given path entirely at
    collection time. We leverage this to exclude modules whose doc-strings are
    either I/O heavy or highly sensitive to runtime state (e.g. forecasting,
    preprocessing DataFrame pretty-printing).
    """

    p_str = str(path)
    if p_str.endswith(".py") and any(pattern in p_str for pattern in _HEAVY_PATTERNS):
        # Skip both regular test discovery *and* doctest collection for the file
        return True
    return False
