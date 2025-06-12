# Graph Responsibilities Inventory

*Revision: yyyy-mm-dd*

This document lists all private attributes and public methods currently defined on `fin_statement_model.core.graph.Graph` **before** the service-extraction refactor.  Each item is bucketed by its future owner so we can track extraction progress.

---

## Private Attributes

| Attribute | Purpose | Target Owner |
|-----------|---------|--------------|
| `_nodes` | Central registry of all nodes in the graph | Graph (shared) |
| `_periods` | Ordered list of period labels managed by the graph | **PeriodService** |
| `_cache` | Two-level calculation cache `node → period → float` | **CalculationEngine** |
| `_node_factory` | Factory for creating all Node instances | NodeFactory (already isolated) |
| `manipulator` | Structural mutation helper API | GraphManipulator (already isolated) |
| `traverser` | Read-only traversal/validation helper API | GraphTraverser (already isolated) |
| `adjustment_manager` | Stores & applies discretionary adjustments | **AdjustmentService** |

---

## Public & Dunder Methods

The table below shows every callable exposed by `Graph` and the bucket/service that will ultimately own the logic.  Ordering follows their appearance in the source file (≈1 – 1577).

| Method | Bucket | Future Owner |
|--------|--------|--------------|
| `nodes` (property) | data access | Graph |
| `periods` (property) | period mgmt | **PeriodService** |
| `add_periods` | period mgmt | **PeriodService** |
| `add_calculation` | calculation | **CalculationEngine** |
| `add_metric` | calculation | **CalculationEngine** |
| `add_custom_calculation` | calculation | **CalculationEngine** |
| `ensure_signed_nodes` | calculation helper | **CalculationEngine** |
| `change_calculation_method` | calculation | **CalculationEngine** |
| `get_metric` | calculation/query | **CalculationEngine** |
| `get_available_metrics` | calculation/query | **CalculationEngine** |
| `get_metric_info` | calculation/query | **CalculationEngine** |
| `get_adjusted_value` | adjustments | **AdjustmentService** |
| `calculate` | calculation | **CalculationEngine** |
| `recalculate_all` | calculation | **CalculationEngine** |
| `clear_all_caches` | cache mgmt | **CalculationEngine** |
| `clear_calculation_cache` | cache mgmt | **CalculationEngine** |
| `clear` | reset helper | Graph (delegates) |
| `add_financial_statement_item` | factory | NodeFactory |
| `update_financial_statement_item` | factory | NodeFactory |
| `get_financial_statement_items` | query | Graph |
| `__repr__` | util | Graph |
| `has_cycle` | traversal | GraphTraverser |
| `get_node` | query | Graph |
| `add_node` | factory | NodeFactory |
| `remove_node` | factory | NodeFactory |
| `replace_node` | factory | NodeFactory |
| `has_node` | query | Graph |
| `set_value` | factory | NodeFactory |
| `topological_sort` | traversal | GraphTraverser |
| `get_calculation_nodes` | traversal | GraphTraverser |
| `get_dependencies` | traversal | GraphTraverser |
| `get_dependency_graph` | traversal | GraphTraverser |
| `detect_cycles` | traversal | GraphTraverser |
| `validate` | traversal | GraphTraverser |
| `breadth_first_search` | traversal | GraphTraverser |
| `get_direct_successors` | traversal | GraphTraverser |
| `get_direct_predecessors` | traversal | GraphTraverser |
| `merge_from` | merge utility | Graph |
| `add_adjustment` | adjustments | **AdjustmentService** |
| `remove_adjustment` | adjustments | **AdjustmentService** |
| `get_adjustments` | adjustments | **AdjustmentService** |
| `list_all_adjustments` | adjustments | **AdjustmentService** |
| `was_adjusted` | adjustments | **AdjustmentService** |

---

### Responsibility Buckets Summary

| Bucket | Future Service/Class | Methods & Attributes (see tables above) |
|--------|----------------------|-----------------------------------------|
| Period Management | **PeriodService** | `_periods`, `periods`, `add_periods` |
| Cache & Calculation | **CalculationEngine** | `_cache`, `calculate`, `recalculate_all`, `clear_all_caches`, `clear_calculation_cache`, `add_calculation`, `add_metric`, `add_custom_calculation`, `ensure_signed_nodes`, `change_calculation_method`, metric getters |
| Adjustments | **AdjustmentService** | `adjustment_manager`, `get_adjusted_value`, `add_adjustment`, `remove_adjustment`, `get_adjustments`, `list_all_adjustments`, `was_adjusted` |
| Factory / Node Creation | NodeFactory (existing) | `_node_factory`, `add_financial_statement_item`, `update_financial_statement_item`, `add_node`, `remove_node`, `replace_node`, `set_value` |
| Traversal & Validation | GraphTraverser / GraphManipulator | `topological_sort`, `detect_cycles`, `has_cycle`, `get_dependencies`, `get_dependency_graph`, `breadth_first_search`, `get_direct_*`, `validate`, `get_calculation_nodes` |
| Other / Utility | Graph | `nodes`, `get_node`, `get_financial_statement_items`, `__repr__`, `clear`, `merge_from`, `has_node` |

---

## Next Steps

*Step 1.2 –* Generate stubs for `CalculationEngine`, `AdjustmentService`, `PeriodService` under `core/graph/services/` so they compile independently of `Graph`.

> **Status:** Step 1.1 complete ✅ 