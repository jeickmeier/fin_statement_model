import json
from pathlib import Path

import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.templates.registry import TemplateRegistry


@pytest.fixture()
def simple_graph() -> Graph:
    """Return a minimal graph fixture used by security tests."""
    g = Graph(periods=["2024"])
    g.add_financial_statement_item("Revenue", {"2024": 100.0})
    return g


@pytest.mark.security
def test_checksum_tamper_detection(simple_graph, tmp_path, monkeypatch):
    """Registry must raise if a bundle is modified after registration."""
    # Isolate registry under temporary directory
    monkeypatch.setenv("FSM_TEMPLATES_PATH", str(tmp_path))

    template_id = TemplateRegistry.register_graph(simple_graph, name="tamper.test", version="v1")

    # Locate bundle file via internal index
    rel = TemplateRegistry._load_index()[template_id]
    bundle_path: Path = TemplateRegistry._registry_root() / rel

    # Corrupt graph_dict to break checksum ----------------------------------------------------
    with bundle_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    data["graph_dict"]["tampered"] = True  # intentional corruption

    with bundle_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh)

    # Expect checksum validation failure on access
    with pytest.raises(ValueError):
        TemplateRegistry.get(template_id)


@pytest.mark.security
def test_index_path_traversal_rejected(simple_graph, tmp_path, monkeypatch):
    """Registry must reject bundle paths attempting directory traversal."""
    monkeypatch.setenv("FSM_TEMPLATES_PATH", str(tmp_path))

    template_id = TemplateRegistry.register_graph(simple_graph, name="traversal.test", version="v1")

    # Inject malicious relative path into index -----------------------------------------------
    index_path = TemplateRegistry._index_path()
    with index_path.open("r", encoding="utf-8") as fh:
        index = json.load(fh)

    index[template_id] = "../outside/bundle.json"  # malicious entry

    with index_path.open("w", encoding="utf-8") as fh:
        json.dump(index, fh)

    # Access should fail due to path validation helper
    with pytest.raises(ValueError):
        TemplateRegistry.get(template_id) 