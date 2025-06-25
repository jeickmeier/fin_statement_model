from __future__ import annotations

"""Thread-safety test for TemplateRegistry.index persistence."""

from pathlib import Path
import threading

from fin_statement_model.core.graph import Graph
from fin_statement_model.templates.registry import TemplateRegistry


def test_register_graph_concurrent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FSM_TEMPLATES_PATH", str(tmp_path))

    def _worker() -> None:
        g = Graph()
        TemplateRegistry.register_graph(g, name="concurrent.template")

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # After both threads registration, index should have 2 entries.
    assert len(TemplateRegistry.list()) == 2
