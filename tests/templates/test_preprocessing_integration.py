"""Tests for template-level preprocessing integration."""

import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.templates.models import PreprocessingSpec, PreprocessingStep
from fin_statement_model.templates.registry import TemplateRegistry


def _build_simple_graph() -> Graph:
    g = Graph(periods=["2024"])
    _ = g.add_financial_statement_item("Revenue", {"2024": 1000.0})
    _ = g.add_financial_statement_item("COGS", {"2024": 400.0})
    return g


@pytest.mark.parametrize("scale", [0.01, 0.1])
def test_preprocessing_pipeline_scale(scale: float) -> None:
    """Template instantiation should apply preprocessing pipeline."""
    graph = _build_simple_graph()

    preprocessing_spec = PreprocessingSpec(
        pipeline=[
            PreprocessingStep(
                name="normalization",
                params={"normalization_type": "scale_by", "scale_factor": scale},
            )
        ]
    )

    template_id = TemplateRegistry.register_graph(
        graph.clone(deep=True),
        name="unit.preprocess",
        version="v1",
        preprocessing=preprocessing_spec,
    )

    try:
        instantiated = TemplateRegistry.instantiate(template_id)
    finally:
        # Cleanup registry state to avoid side effects for other tests
        TemplateRegistry.delete(template_id)

    rev = instantiated.calculate("Revenue", "2024")
    cogs = instantiated.calculate("COGS", "2024")

    assert rev == pytest.approx(1000.0 * scale)  # noqa: S101
    assert cogs == pytest.approx(400.0 * scale)  # noqa: S101
