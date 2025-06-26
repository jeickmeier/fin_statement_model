# Statement Templates – Template Registry & Engine (TRE)

> *Introduced in v0.4-beta – July 2025*

Financial-statement **templates** let you save a fully-wired calculation graph (nodes, edges, periods, metrics, adjustments) and instantiate it later – either programmatically or from the command-line – in a single line of code.

> Built-in templates are shipped as self-contained JSON *bundle* files inside the library and are automatically discovered by `install_builtin_templates()` - no network calls or hard-coded builders involved.

Why bother? Templates turn hours of repetitive model scaffolding into seconds, ensure naming conventions remain intact and enable structural *diffs* between versions. They are the foundation for collaborative modelling workflows.

---

## Quick-start (3 minutes)

```pycon
>>> from fin_statement_model.templates import TemplateRegistry
>>> from fin_statement_model.templates.builtin import install_builtin_templates
>>> install_builtin_templates()  # idempotent helper
✅ Installed 2 built-in templates.

>>> TemplateRegistry.list()
['lbo.standard_v1', 'real_estate.lending_v2']

>>> g = TemplateRegistry.instantiate('lbo.standard_v1', periods=["2024", "2025", "2026"])
>>> g.calculate("NetIncome", "2025")
123.4

>>> diff = TemplateRegistry.diff('lbo.standard_v1', 'lbo.standard_v2', include_values=True)
>>> diff.structure.changed_nodes
{'InterestExpense': 'formula'}
>>> diff.values.max_delta
0.005
```

---

## CLI cheatsheet

| Task | Command |
|------|---------|
| List available templates | `fsm template ls` |
| Instantiate template | `fsm template apply lbo.standard_v1 --periods 2024:2028 --output model.fsm` |
| Show structural & value diff | `fsm template diff lbo.standard_v1 lbo.standard_v2` |

The CLI mirrors the Python API and respects the `FSM_TEMPLATES_PATH` environment variable when reading/writing from the local registry.

---

## Internals in 60 seconds

```mermaid
flowchart TD
    subgraph Registry folder
        direction TB
        A[index.json] --> B[bundle.json]
    end
    B --> C[IO facade `read_data()`] --> D(Graph)
    D -->|clone| E(Graph copy)
    style A fill:#f9f,stroke:#333,stroke-width:1px
```

1. Each **TemplateBundle** (`bundle.json`) is a frozen Pydantic v2 object containing metadata, a graph-definition dictionary and a SHA-256 checksum.
2. The registry index (`index.json`) maps *template-id* (`lbo.standard_v1`) to the bundle path.
3. `instantiate()` re-hydrates the graph via the IO facade, then performs a *deep clone* to avoid shared caches.

---

## Authoring your own template

```python
from fin_statement_model.core.graph import Graph
from fin_statement_model.templates import TemplateRegistry

# 1· build or load your Graph (see core_basic_usage.py)
g = Graph(periods=["2023", "2024"])
# … add nodes, calculations, adjustments …

# 2· register it
TemplateRegistry.register_graph(
    graph=g,
    name="infra.ppp",
    meta={"category": "infrastructure", "description": "PPP concession 25-year model"},
)
```

The call persists a *bundle.json* under `~/.fin_statement_model/templates/store/infra/ppp/v1/`. Subsequent calls with the same *name* but no explicit **version** will auto-increment (`v2`, `v3`, …).

---

## Versioning rules

* Semantic suffix `_<vX>` where `X ∈ ℕ⁺` is enforced by the registry.
* Duplicate (`name + version`) raises `ValueError`.
* `TemplateRegistry._resolve_next_version()` picks the highest existing `v<N>` and bumps by +1.

---

## Diff semantics

`TemplateRegistry.diff()` wraps two helpers:

* **compare_structure** → added / removed / changed nodes
* **compare_values** → per-cell Δ between two graphs (optional)

The result is an immutable `DiffResult` model you can pretty-print or serialise.

---

## FAQ & troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `ValueError: Checksum does not match` | Bundle file edited manually | Re-register template or delete bundle path |
| `No common periods to compare` | `diff(include_values=True)` but graphs share no periods | Specify `periods=` argument |
| `Template 'xyz' not found` | Registry index corrupt | Remove `index.json` and reinstall templates |

---

*Last updated: {{ git_commit_hash }}* 