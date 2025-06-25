### Product Requirements Document (v 0.2 — **updates in bold**)

**Feature Name:** Financial Statement **Template Registry & Engine (TRE)**
**Owner:** Finance‑Platform Core Team
**Stakeholders:** Deal‑Modelling teams (PE / LBO), Real‑Estate Lending, Corporate FP\&A, Data‑Engineering, QA
**Target Release:** v 0.4 (August 2025)

---

#### 1 · Problem / Opportunity

Modellers rebuild identical statement skeletons (e.g., 5‑year LBO, construction‑loan waterfall). This wastes time and diverges structures, breaking automation. The redesigned **TRE** must let users **register, version and instantiate templates that are stored natively as `Graph` bundles**, so that forecasting, adjustments, metrics and IO round‑trips (`read_data` / `write_data`) continue to “just work” .

> **Change vs v0.1:** Pydantic v2 models will be adopted for all new public data structures to align with IO config classes already using v2 .

---

#### 2 · Goals & Non‑Goals

|    | Goal                                                                                                             | Non‑Goal                                                 |
| -- | ---------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| G1 | Create, save, load and list **statement templates** programmatically or via CLI                                  | Provide a GUI                                            |
| G2 | Instantiation yields a fully‑wired **Graph** (nodes, edges, periods, forecasts, metrics)                         | Invent new node types                                    |
| G3 | Templates are **versioned & typed** (“lbo.v1”, “real\_estate\_lending.v2”) and stored locally; *no remote sync*  | Remote repository management                             |
| G4 | Leverage existing **IO facade** for import/export in all supported formats                                       | Support proprietary formats not already in IO            |
| G5 | Provide a **diff API** that detects **both structural and value deltas** between two template‑based graphs       | Visual diff viewer                                       |
| G6 | Adopt **Pydantic v2** for Template, Diff and Registry models to enable validation, schema export, IDE type‑hints | Switch the whole code‑base to another validation library |
| G7 | Registry is **pluggable** so external packages can ship templates                                                | Centralised cloud registry                               |

---

#### 3 · Design Decisions (answers to open questions)

1. **Partial application** is *not* required; an “income‑statement‑only” structure will be a separate template.
2. **Diff** must compare (a) topology (nodes, edges, metadata) and (b) numerical deltas per node‑period.
3. **Remote sync** is delegated to deployment tooling; TRE handles only the local store.
4. **Backwards compatibility** with prior template schema versions is not a 2025 requirement.
5. **Pydantic v2** is the modelling layer of choice (consistent with IO configs) .

---

#### 4 · Functional Requirements

|  ID   | Description                                                                                                                                                                    | Priority |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- |
| FR‑1  | `TemplateRegistry` **CRUD**: `list()`, `get()`, `instantiate()`, `register_graph()`, `register_file()`, `remove()`                                                             | Must     |
| FR‑2  | Templates stored as **TemplateBundle** (JSON) containing a `graph_definition_dict` exported through IO (`write_data(format_type="graph_definition_dict")`) plus `TemplateMeta` | Must     |
| FR‑3  | Instantiation deep‑copies Graph, generates new UUIDs, extends periods on demand, applies optional node renames                                                                 | Must     |
| FR‑4  | Semantic versioning `<name>.<major>.<minor>`; monotonic enforcement                                                                                                            | Must     |
| FR‑5  | `diff(template_a, template_b, *, include_values=True)` returns `DiffResult` capturing **structure & value** changes                                                            | Must     |
| FR‑6  | CLI: `fsm template ls`, `fsm template apply`, `fsm template diff`                                                                                                              | Should   |
| FR‑7  | Validation: GraphTraverser.validate(), Pydantic field validation, cycle detection                                                                                              | Must     |
| FR‑8  | Unit + integration tests incl. diff, IO round‑trips, adjustment propagation                                                                                                    | Must     |
| FR‑9  | Instantiate 2 000‑node template in < 250 ms on M‑series laptop                                                                                                                 | Should   |
| FR‑10 | Registry path configurable via `FSM_TEMPLATES_PATH`; uses atomic writes; **no remote operations**                                                                              | Must     |
| FR‑11 | Security: JSON only (no pickle/exec); file perms `600`; SHA‑256 checksum optional enterprise flag                                                                              | Must     |

---

#### 5 · Data Model *(Pydantic v2)*

```python
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class TemplateMeta(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    version: str  # e.g. "lbo.v2"
    category: str  # "lbo", "real_estate"
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: dict[str, str] = Field(default_factory=dict)

class TemplateBundle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    meta: TemplateMeta
    graph_dict: dict  # result of write_data(..., format_type="graph_definition_dict")
    checksum: str
```

A **registry index** (`~/.fin_statement_model/templates/index.json`) maps `name→path`.

> *Why Pydantic v2?* Aligns with IO config classes (e.g., `DataFrameReaderConfig`, `ExcelWriterConfig`) already migrated .

---

#### 6 · Public API Sketch

```python
from fin_statement_model.templates import TemplateRegistry

# List available
TemplateRegistry.list()                        # → ["lbo.standard_v1", "real_estate.lending_v2"]

# Instantiate with extra periods
g = TemplateRegistry.instantiate(
        "lbo.standard_v1", periods=["2024","2025","2026"]
    )

# Register new template from an existing Graph
TemplateRegistry.register_graph(
        graph=g, name="infra.ppp_v1",
        meta={"description": "PPP concession 25‑year model"}
    )

# Structural + value diff
diff = TemplateRegistry.diff("lbo.standard_v1", "lbo.standard_v2", include_values=True)
print(diff.structure.changed_nodes, diff.values.changed_cells)
```

Each call ultimately serialises / deserialises via the **IO facade** (`write_data`, `read_data`) so any format registered in IO automatically works . Node creation still goes through **NodeFactory**  ensuring compatibility with existing builder helpers.

---

#### 7 · Diff Semantics

* **Structure**

  * Added / removed nodes
  * Added / removed edges
  * Changed node metadata (e.g., formula)
* **Values**

  * Cell‑level delta: `Δ = GraphB.calculate(node, period) – GraphA.calculate(node, period)`
* API returns `DiffResult(BaseModel)` containing two sub‑objects: `structure: StructureDiff`, `values: ValuesDiff`.
* Helper `TemplateRegistry.diff(..., format="markdown")` pretty‑prints a summary table.

---

#### 8 · CLI UX

```
$ fsm template ls
NAME                     VERSION  CATEGORY       DESCRIPTION
lbo.standard             v1       lbo            Classic 5‑year buy‑out
real_estate.lending      v2       real_estate    Construction+term waterfall

$ fsm template apply lbo.standard@v1 --periods 2024:2028 --output model.fsm
✅ Template instantiated ➜ model.fsm (Graph JSON, 37 nodes)

$ fsm template diff lbo.standard@v1 lbo.standard@v2
Structural changes: +2 nodes, +1 calc edge
Value changes: 48 cells differ (max Δ = 0.5%)
```

---

#### 9 · Performance & Scalability

* Index kept in‑memory; templates lazily loaded.
* Graph instantiation uses `Graph.clone(deep=True)` (new helper) rather than node‑by‑node rebuild to minimise allocations.
* Benchmarks target 2 000 nodes / 20 periods instantiation < 250 ms.

---

#### 10 · Security & Compliance

* **No exec / pickle**; JSON only.
* Verify SHA‑256 on load; warn if checksum mismatch.
* Path resolved under `$FSM_TEMPLATES_PATH` (defaults to `~/.fin_statement_model/templates`).

---

#### 11 · Testing Strategy

1. **Unit**: Registry CRUD, versioning rules, diff algorithm edge cases.
2. **Integration**: Instantiate → forecast → IO export (Excel, CSV, DataFrame) → IO re‑import; values identical.
3. **Perf**: Continuous benchmark in CI gating (< 250 ms).
4. **Security**: Malformed JSON, path traversal attempts, checksum mismatch.
5. **Regression**: Ensure existing IO tests continue to pass untouched (template code must be additive).

---

#### 12 · Implementation Milestones

| Date        | Milestone                                                              |
| ----------- | ---------------------------------------------------------------------- |
| 15 Jul 2025 | Design sign‑off & schema freeze                                        |
| 01 Aug 2025 | `TemplateMeta`, `TemplateBundle` (Pydantic), file store implementation |
| 08 Aug 2025 | `TemplateRegistry` CRUD & CLI `ls / apply` commands                    |
| 15 Aug 2025 | `diff` engine (structure + value) with unit tests                      |
| 22 Aug 2025 | Performance tuning & checksum security                                 |
| 30 Aug 2025 | Beta release to internal modelling teams                               |
| 15 Sep 2025 | GA with docs + examples                                                |

---

#### 13 · Risks & Mitigations

| Risk                                             | Mitigation                                                               |
| ------------------------------------------------ | ------------------------------------------------------------------------ |
| Large template size slows disk I/O               | Compress JSON with `gzip`; lazy‑load until instantiate                   |
| Future breaking changes to `Graph` schema        | Clearly version TemplateBundle; migration script if needed later         |
| Diff algorithm complexity                        | Start with naïve approach; add optimisation only if perf budget exceeded |
| User confusion over template vs. raw graph files | CLI namespacing (`template apply`, `graph import`) and docs              |

---

#### 14 · References

* **NodeFactory** creation helpers&#x20;
* **IO Facade** (`read_data` / `write_data`)&#x20;
* **Pydantic v2 IO configs** establishing library‑wide precedent&#x20;
* Stub `list_available_builtin_configs` showing removed legacy template system (motivates new TRE)&#x20;

---

**Status:** *Draft v0.2 – ready for stakeholder review*
