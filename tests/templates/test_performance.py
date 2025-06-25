import concurrent.futures
import time
from statistics import median

import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.templates.registry import TemplateRegistry


@pytest.mark.perf
def test_instantiate_performance(tmp_path, monkeypatch):
    """Instantiate 500-node graph concurrently and ensure p95 ≤ 2 s."""
    monkeypatch.setenv("FSM_TEMPLATES_PATH", str(tmp_path))

    # Build large graph -----------------------------------------------------------------------
    periods = [str(year) for year in range(2020, 2025)]
    big_graph = Graph(periods=periods)
    for idx in range(500):
        big_graph.add_financial_statement_item(f"Node_{idx}", {periods[0]: float(idx)})

    template_id = TemplateRegistry.register_graph(big_graph, name="perf.test", version="v1")

    # Warm-up (JIT, caches, etc.)
    TemplateRegistry.instantiate(template_id)

    # Concurrent benchmark --------------------------------------------------------------------
    def _inst_once() -> float:
        start = time.perf_counter()
        TemplateRegistry.instantiate(template_id)
        return time.perf_counter() - start

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        durations = list(executor.map(lambda _: _inst_once(), range(50)))

    durations.sort()
    p95 = durations[int(0.95 * len(durations)) - 1]

    # Log median for debugging (non-assert)
    median_dur = median(durations)
    print(f"Instantiate median={median_dur * 1000:.1f} ms  p95={p95 * 1000:.1f} ms", flush=True)

    assert p95 <= 2.0  # seconds 