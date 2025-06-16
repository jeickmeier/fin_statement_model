# Graph API Simplification – Refactor Plan (pre-alpha)

This document captures the **single-step refactor** that will replace the current `GraphFacade` + `impl.graph.Graph` split with a clean, minimal public surface.  Because the library is still *pre-alpha*, no deprecation shims or warnings are required – we can break API today.

---
## 1. Target file / class layout

```
fin_statement_model/
  core/
    graph/
      __init__.py           → exports only:  Graph, GraphInspector
      graph.py              → the **new** public class (moved + trimmed)
      inspect.py            → read-only helpers (`GraphInspector`)
      _admin.py             → low-level, opt-in helpers for power-users/tests
      engine/               → unchanged (calc engine, topology, etc.)
      services/             → unchanged (adjustment, metric, period, …)
```

*   The **sole public entry-point** is `Graph` in `graph.py`.
*   `GraphFacade` **and** the entire `api/` package are deleted.
*   All client code updates import lines to `from fin_statement_model.core.graph import Graph`.

---
## 2. Public API (≈ 16 callables)

Category | Method / property
---------|------------------
Structural | `add_item`, `add_periods`, `add_financial_statement_item`, `add_calculation`, `remove_node`, `replace_node`
Mutation / data | `set_value`, `update_financial_statement_item`
Calculation & adjustments | `calculate`, `add_adjustment`, `get_adjusted_value`, `was_adjusted`, **`list_all_adjustments`** (recently promoted)
Metrics | `add_metric`, `get_metric`, `get_available_metrics`
Introspection | `periods` (property), `nodes` (property)

Everything **not** listed above is either removed from the public surface, moved to `GraphInspector`, or placed in `_admin.py`.

---
## 3. Opt-in helpers

### 3.1 `graph.inspect` – read-only tools

```
class GraphInspector:
    def topological_sort(self) -> list[str]: ...
    def detect_cycles(self) -> list[list[str]]: ...
    def validate(self) -> list[str]: ...
    def get_dependency_graph(self) -> dict[str, list[str]]: ...
    def get_calculation_nodes(self) -> list[str]: ...
    def get_dependencies(self, node: str) -> list[str]: ...
    def get_direct_successors(self, node: str) -> list[str]: ...
    def get_direct_predecessors(self, node: str) -> list[str]: ...
    def breadth_first_search(...): ...
    def find_cycle_path(...): ...
```

Exposed once per `Graph` instance:

```python
self.inspect = GraphInspector(self)
```

### 3.2 `_admin` module – power-user write helpers

Accessible via explicit import (`from fin_statement_model.core.graph import _admin`) only.

* `merge_from(dst, src)`
* `add_node(graph, node_obj)`
* `would_create_cycle(graph, node_obj)`
* `clear_caches(graph)`

(Implementation: thin wrappers around the now-private methods on `Graph`.)

---
## 4. Step-by-step implementation guide

1. **Move & rename:**
   ```bash
   mv fin_statement_model/core/graph/impl/graph.py \
      fin_statement_model/core/graph/graph.py
   ```
   Rename the class inside the file to `Graph`.

2. **Trim surface:**
   * Prefix every non-public method with an underscore (`_`).
   * Remove unused legacy helpers.

3. **Extract inspectors:**
   * Create `inspect.py`; move all *read-only* helpers there.
   * Wire into `Graph.__init__` (`self.inspect = GraphInspector(self)`).

4. **Create admin helpers:**
   * New file `_admin.py`; copy `merge_from`, `add_node`, etc.

5. **Delete façade:**
   * Remove `core/graph/api/` package and all imports of `GraphFacade`.
   * Replace any call-sites with the new `Graph` import.

6. **Update exports:**
   * `core/graph/__init__.py`:
     ```python
     from .graph import Graph
     from .inspect import GraphInspector

     __all__ = ["Graph", "GraphInspector"]
     ```

7. **Tidy imports & tests:**
   * Run `ruff –e F401` to find unused imports.
   * Fix all references in tests/ and examples/.

8. **CI pass:**
   * `black . && ruff --fix . && mypy --strict . && pytest -q` – ensure ≥ 80 % coverage.

---
## 5. Expected developer ergonomics

```python
from fin_statement_model.core.graph import Graph

g = Graph(periods=["2024"])

g.add_financial_statement_item("revenue", {"2024": 120})

g.add_calculation("gross_profit", formula="revenue * 0.8")
assert g.calculate("gross_profit", "2024") == 96

# quick inventory
print(g.periods)   # ["2024"]
print(g.nodes)     # ["revenue", "gross_profit"]

# adjustments
adj_id = g.add_adjustment(
    node_name="revenue", period="2024", value=10, reason="audit", adj_type="manual"
)
print(g.list_all_adjustments())

# deep dive (opt-in)
print(g.inspect.topological_sort())
```

---
## 6. Net effect

* **Tiny** public surface – easy to document and maintain.
* Advanced functionality still available, but *only* when explicitly imported or accessed (`graph.inspect`, `_admin`).
* Zero legacy baggage or temporary shims.

---

End of plan – happy refactoring! 🎉 