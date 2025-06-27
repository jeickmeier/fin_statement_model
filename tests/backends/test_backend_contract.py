# noqa: test file
import uuid

import pytest
import importlib

from fin_statement_model.core.graph import Graph
from fin_statement_model.templates.backends import JsonFileStorageBackend
from fin_statement_model.templates.registry import TemplateRegistry

# Backends under test -------------------------------------------------------------------------

def _json_file_backend(tmp_path_factory):
    temp_file = tmp_path_factory.mktemp("fsm") / "templates.json"
    return JsonFileStorageBackend(temp_file)


# Only include S3 backend when boto3 + moto available
def _s3_backend():
    try:
        importlib.import_module("boto3")
        importlib.import_module("moto")
    except ModuleNotFoundError:
        return None
    from fin_statement_model.templates.backends import S3StorageBackend  # local import to avoid linter

    # Use random bucket name – the moto context will create it on demand
    return S3StorageBackend(bucket=f"fsm-test-{uuid.uuid4()}")


def pytest_generate_tests(metafunc):
    if "backend" in metafunc.fixturenames:
        tmp_path_factory = metafunc.config._tmp_path_factory  # noqa: SLF001 – pytest internals
        cases = [_json_file_backend(tmp_path_factory)]
        s3 = _s3_backend()
        if s3 is not None:  # type: ignore[arg-type]
            cases.append(s3)  # type: ignore[arg-type]
        metafunc.parametrize("backend", cases)


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