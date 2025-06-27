# noqa: test file
import tempfile

import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.templates.backends import FileSystemStorageBackend, InMemoryStorageBackend
from fin_statement_model.templates.registry import TemplateRegistry

# Backends under test -------------------------------------------------------------------------
BACKENDS_UNDER_TEST = [
    InMemoryStorageBackend(),
    FileSystemStorageBackend(),
]


def _build_sample_graph() -> Graph:
    """Return a minimal graph suitable for backend contract tests."""
    g = Graph(periods=["2024", "2025"])
    g.add_financial_statement_item("Revenue", {"2024": 100.0, "2025": 110.0})
    g.add_financial_statement_item("COGS", {"2024": 40.0, "2025": 44.0})
    g.add_calculation(
        name="GrossProfit",
        input_names=["Revenue", "COGS"],
        operation_type="formula",
        formula="input_0 - input_1",
        formula_variable_names=["input_0", "input_1"],
    )
    return g


@pytest.mark.BACKEND_TEST_MATRIX
@pytest.mark.parametrize("backend", BACKENDS_UNDER_TEST)
def test_register_get_list_delete_cycle(monkeypatch, backend):
    """Core CRUD behaviour must be consistent across all backends."""
    # Isolate filesystem backend to a temp directory to avoid side-effects
    if isinstance(backend, FileSystemStorageBackend):
        tmpdir = tempfile.mkdtemp()
        monkeypatch.setenv("FSM_TEMPLATES_PATH", tmpdir)

    # Configure backend
    TemplateRegistry.configure_backend(backend)

    graph = _build_sample_graph()

    template_id = TemplateRegistry.register_graph(graph, name="contract.test")
    assert template_id in TemplateRegistry.list()

    bundle = TemplateRegistry.get(template_id)
    assert bundle.meta.name == "contract.test"

    # Instantiate and verify calculation result remains correct
    instantiated = TemplateRegistry.instantiate(template_id)
    assert instantiated.calculate("GrossProfit", "2024") == pytest.approx(60.0)

    # Delete and confirm removal
    TemplateRegistry.delete(template_id)
    assert template_id not in TemplateRegistry.list()