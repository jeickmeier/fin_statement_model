# Adjustments Module

The **Adjustments** sub-package provides a concise API for recording discretionary
changes to node values, storing them in an in-memory manager, and applying or
summarising them during model execution.

Key building blocks:

| Object | Responsibility |
| ------ | -------------- |
| `Adjustment` | Immutable Pydantic model capturing a single change (value, type, tags, scenario, etc.). |
| `AdjustmentType` | Enum that defines _how_ an adjustment affects the base value. Built-ins: `ADDITIVE`, `MULTIPLICATIVE`, `REPLACEMENT`. |
| `AdjustmentManager` | Stores adjustments, exposes powerful filtering, and applies them to raw values. |
| `analytics` helpers | Convenience functions such as `summary` and `list_by_tag` for quick exploration. |

---

## Quick-start

```python
from fin_statement_model.core.adjustments import (
    Adjustment, AdjustmentManager, AdjustmentType, summary, list_by_tag
)

# 1. Create a few adjustments
adj1 = Adjustment(
    node_name="Revenue",
    period="2023-01",
    value= 25.0,
    type=AdjustmentType.ADDITIVE,
    tags={"Manual", "NonRecurring"},
    reason="One-off marketing campaign",
)

adj2 = Adjustment(
    node_name="Revenue",
    period="2023-01",
    value=1.05,  # 5 % uplift
    type=AdjustmentType.MULTIPLICATIVE,
    tags={"Scenario/Upside"},
    reason="Bullish scenario",
    scenario="upside",
)

# 2. Store them in a manager
mgr = AdjustmentManager()
for a in (adj1, adj2):
    mgr.add_adjustment(a)

# 3. Retrieve and apply
base = 100.0
adj_list = mgr.get_adjustments("Revenue", "2023-01")
new_value, applied = mgr.apply_adjustments(base, adj_list)
print(new_value)  # -> 131.25

# 4. Analytics helpers
print(summary(mgr))
print(list_by_tag(mgr, "NonRecurring"))
```

## Advanced filtering

`AdjustmentManager.get_filtered_adjustments` accepts flexible predicates:

* **AdjustmentFilter** – declarative include/exclude rules.
* **set[str]**        – shorthand for `include_tags`.
* **Callable**        – custom lambda or function.  
  The predicate may accept **one** (`adj`) or **two** (`adj, period`) positional
  parameters, enabling period-aware logic.

```python
# Period-aware callable predicate
def only_if_large(adj, period):
    return abs(adj.value) > 10 and period.startswith("2023")

filtered = mgr.get_filtered_adjustments(
    "Revenue", "2023-01", filter_input=only_if_large
)
```

## Adding a new `AdjustmentType`

If the three built-in combination rules are insufficient, you can extend the
system by creating a custom Enum member **and** teaching the manager how to
apply it.

```python
from enum import Enum, auto
from fin_statement_model.core.adjustments import AdjustmentType
from fin_statement_model.core.adjustments.manager import AdjustmentManager

class ExtendedAdjustmentType(AdjustmentType):
    LOGARITHMIC = "logarithmic"  # base + log(value) demo

# Monkey-patch the manager with the new behaviour
_original_apply_one = AdjustmentManager._apply_one

def _apply_one_with_log(self, base_value, adj):
    if adj.type == ExtendedAdjustmentType.LOGARITHMIC:
        import math
        return float(base_value + math.log(adj.value))
    return _original_apply_one(self, base_value, adj)

AdjustmentManager._apply_one = _apply_one_with_log  # patch once at start-up
```

> ℹ️  In future the library may expose an official plugin hook for registering
> new adjustment types without monkey-patching.  For now the above approach is
> sufficient in a pre-alpha environment.

---

## Testing your logic

```bash
pytest tests/adjustments  # all adjustment-related tests
```

All public APIs follow strict typing (`mypy --strict`) and linting (`ruff`).
Feel free to open an issue or PR if you find a corner case! 