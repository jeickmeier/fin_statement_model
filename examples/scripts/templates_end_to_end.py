"""End-to-end demonstration of the Template Registry & Engine (TRE).

Run this module directly:

$ python -m examples.scripts.templates_end_to_end --verbose

The script will:
1. Install built-in templates from the packaged *JSON bundles* (if missing).
2. List available templates.
3. Instantiate *lbo.standard_v1* with extra periods.
4. Clone the graph, mutate one value and register it as *lbo.standard_v2*.
5. Show a structural & value diff between the two versions.
"""

from __future__ import annotations

import argparse
import logging

from fin_statement_model.templates import TemplateRegistry, install_builtin_templates
from fin_statement_model.core.graph import Graph
from fin_statement_model.io import write_data

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the end-to-end Template Registry demo."""
    parser = argparse.ArgumentParser(description="TRE end-to-end demo")
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)


    # 1· Ensure built-in templates are installed --------------------------------
    install_builtin_templates(force=True)

    # 2· List templates ----------------------------------------------------------
    logger.info("Available templates: %s", TemplateRegistry.list())

    # 3· Instantiate LBO template with extra periods ----------------------------
    g = TemplateRegistry.instantiate("lbo.standard_v1", periods=["2027"])
    logger.info("Instantiated graph with %d nodes and periods %s", len(g.nodes), g.periods)

    # Validate that the template instantiated into a proper Graph object ------
    if not isinstance(g, Graph):
        raise TypeError(f"TemplateRegistry.instantiate returned {type(g)}, expected Graph")

    validation_errors = g.traverser.validate()
    if validation_errors:
        logger.warning("Graph validation produced issues: %s", validation_errors)
    else:
        logger.info("Graph validation passed with no structural issues detected.")

    # Export graph data to a pandas DataFrame and display ----------------------
    df = write_data("dataframe", g, target=None)
    logger.info("Graph values as DataFrame:\n%s", df)

    # 4· Mutate & register as new version ---------------------------------------
    #g.manipulator.set_value("Revenue", "2027", 2000.0)

    try:
        new_id = TemplateRegistry.register_graph(g, name="lbo.standard", version="v2")
        logger.info("Registered mutated graph as %s", new_id)
    except ValueError:
        # Already present from a previous run - that's fine for demo purposes
        new_id = "lbo.standard_v2"
        logger.info("Template %s already exists - skipping registration", new_id)

    # 5· Diff versions -----------------------------------------------------------
    diff_result = TemplateRegistry.diff("lbo.standard_v1", "lbo.standard_v2", include_values=True)
    logger.info(
        "Diff summary: +%d nodes, %d value cells differ (max Δ = %s)",
        len(diff_result.structure.added_nodes),
        len(diff_result.values.changed_cells) if diff_result.values else 0,
        diff_result.values.max_delta if diff_result.values else "n/a",
    )


if __name__ == "__main__":
    main()
