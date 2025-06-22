# IO Package Refactor — Actionable Plan

> **Scope**: `fin_statement_model/io/*`
>
> Goal: simplify onboarding, remove legacy/dead code, tighten typing, and reduce duplication while keeping advanced power-user hooks intact.

---

## Legend

| Priority | Meaning |
|---|---|
| **P0** | Must-do before next release (breaking/bug-fix) |
| **P1** | Should-do soon (usability / tech-debt) |
| **P2** | Nice-to-have / stretch |

---

## Task List

### �� P0 – Critical

- [x] **Fix MRO inconsistency in `DataFrameReaderBase`**  
  Swap base-class order: `MappingAwareMixin` _before_ `ConfigurationMixin`.  
  _Files_: `io/core/dataframe_reader_base.py`

- [x] **Detach `AdjustmentsExcelReader` from `DataReader` hierarchy**  
  Create a slim `AdjustmentReaderBase` (or convert to plain function) that returns `(list[Adjustment], DataFrame)` to honour LSP.  
  Update `io.adjustments.__all__`, tests.  
  _Files_: `io/adjustments/excel_io.py`, tests

- [x] **ExcelReader header-row simplification**  
  Enforce exclusive args: `header_row` XOR `periods_row`. Remove branchy rename logic + warning.  
  Update docstring & config validation.  
  _Files_: `io/formats/excel_reader.py`, `io/config/models.py`

### 🟧 P1 – Important

- [x] **DRY writer parameter resolution**  
  Add `_resolve_write_params()` helper to `BaseTableWriter` and reuse in `DataFrameWriter` & `ExcelWriter`.  
  _Files_: `io/core/base_table_writer.py`, `io/formats/dataframe_writer.py`, `io/formats/excel_writer.py`

- [X] **Merge mix-ins where over-abstracted**  
  Combine `ConfigurationMixin` + `ValidationMixin` (shared context/summary logic).  
  Evaluate folding `ValueExtractionMixin` into `BaseTableWriter`.  
  _Files_: `io/core/mixins/*`, corresponding unit tests

- [x] **Enum for format types**  
  Autogenerate `IOFormat(Enum)` from registry keys at import time; use in config models instead of raw `Literal[...]`.  
  Deprecate string literals gradually.  
  _Files_: `io/core/registry.py`, `io/config/models.py`, docs

- [X] **Reduce public exports**  
  Trim `io.__all__` to façade functions & few key helpers. Document deep-import pattern for power users.  
  _Files_: `io/__init__.py`, docs

- [x] **Improve error passthrough**  
  In `handle_read_errors` / `handle_write_errors`, preserve original traceback via `raise ... from e` (already) **and** attach as `__cause__` if missing; optionally add `__traceback__` copy for richer logging.  
  _Files_: `io/core/mixins/error_handlers.py`

### 🟨 P2 – Nice-to-have

- [x] **Dead-code & TODO sweep**  
  Run `ruff --select F401,F841,B018` + `ruff --select TID252` (TODO). Delete or ticket leftovers (e.g., comments in `cells_io.py`).

- [x] **Refine typing of `source` / `target` in config models**  
  Use `Annotated` or generics to avoid `Any`.

### 📄 Documentation

- [ ] **Add `docs/io_quickstart.md`**  
  1-page guide: _"Read CSV → manipulate graph → write Excel"_.  
  Reference `IOFormat` enum once implemented.

---

## Deliverables Checklist

- [ ] All unit tests pass (`pytest -q`) & coverage ≥ 80 %
- [ ] `ruff`, `black`, `mypy --strict` clean
- [ ] Updated docs (README, quickstart, docstrings)

---

**ETA**: ~2–3 developer days for P0 + P1; P2 items can be parallel or later. 