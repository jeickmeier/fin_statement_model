# Adjustments Module

The **Adjustments** sub-package provides a concise API for recording discretionary
changes to node values, storing them in an in-memory manager, and applying or
summarising them during model execution. It supports advanced filtering, analytics,
and extensibility for custom adjustment types.

Key building blocks:

| Object | Responsibility |
| ------ | -------------- |
| `Adjustment` | Immutable Pydantic model capturing a single change (value, type, tags, scenario, etc.). |
| `AdjustmentType` | Enum that defines _how_ an adjustment affects the base value. Built-ins: `ADDITIVE`, `MULTIPLICATIVE`, `REPLACEMENT`. |
| `AdjustmentManager` | Stores adjustments, exposes powerful filtering, and applies them to raw values. |
| `analytics` helpers | Convenience functions such as `summary` and `list_by_tag` for quick exploration. |

---

## Basic Usage

```python
from fin_statement_model.core.adjustments import (
    Adjustment, AdjustmentManager, AdjustmentType, summary, list_by_tag
)

# 1. Create adjustments
adj1 = Adjustment(
    node_name="Revenue",
    period="2023-01",
    value=25.0,
    type=AdjustmentType.ADDITIVE,
    tags={"Manual", "NonRecurring"},
    reason="One-off marketing campaign",
)
adj2 = Adjustment(
    node_name="Revenue",
    period="2023-01",
    value=1.05,  # 5% uplift
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
```

## Analytics Helpers

Summarize and analyze adjustments using built-in analytics functions:

```python
from fin_statement_model.core.adjustments.analytics import summary, list_by_tag

df = summary(mgr)
print(df)

# List adjustments by tag prefix
nonrecurring = list_by_tag(mgr, "NonRecurring")
print(nonrecurring)
```

## Advanced Filtering

`AdjustmentManager.get_filtered_adjustments` accepts flexible predicates:

* **AdjustmentFilter** – declarative include/exclude rules.
* **set[str]**        – shorthand for `include_tags`.
* **Callable**        – custom lambda or function.  
  The predicate may accept **one** (`adj`) or **two** (`adj, period`) positional
  parameters, enabling period-aware logic.

```python
from fin_statement_model.core.adjustments.models import AdjustmentFilter

def only_if_large(adj, period):
    return abs(adj.value) > 10 and period.startswith("2023")

filtered = mgr.get_filtered_adjustments(
    "Revenue", "2023-01", filter_input=only_if_large
)
```

## Extending Adjustment Types

If the three built-in combination rules are insufficient, you can extend the
system by creating a custom Enum member **and** teaching the manager how to
apply it.

```python
from enum import Enum
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

## Testing

Run all adjustment-related tests:

```bash
pytest tests/core/adjustments
```

All public APIs follow strict typing (`mypy --strict`) and linting (`ruff`).
Feel free to open an issue or PR if you find a corner case! 

## Reference: Doctest Examples

### Creating and Using Adjustments

```python
>>> from fin_statement_model.core.adjustments.models import Adjustment, AdjustmentType
>>> adj = Adjustment(node_name='Revenue', period='2023-01', value=100.0, reason='Manual update')
>>> adj.type == AdjustmentType.ADDITIVE
True
```

### AdjustmentManager Usage

```python
>>> from fin_statement_model.core.adjustments.models import Adjustment
>>> from fin_statement_model.core.adjustments.manager import AdjustmentManager
>>> mgr = AdjustmentManager()
>>> adj = Adjustment(node_name='A', period='2023', value=10.0, reason='Manual')
>>> mgr.add_adjustment(adj)
>>> mgr.get_adjustments('A', '2023')[0].value == 10.0
True
>>> base = 100.0
>>> new_value, applied = mgr.apply_adjustments(base, mgr.get_adjustments('A', '2023'))
>>> new_value == 110.0
True
```

### Analytics Helpers

```python
>>> from fin_statement_model.core.adjustments.analytics import summary, list_by_tag
>>> from fin_statement_model.core.adjustments.manager import AdjustmentManager
>>> from fin_statement_model.core.adjustments.models import Adjustment
>>> mgr = AdjustmentManager()
>>> adj = Adjustment(node_name='A', period='2023', value=2.0, reason='r', tags={'X'})
>>> mgr.add_adjustment(adj)
>>> df = summary(mgr)
>>> df.loc[('2023', 'A'), 'sum_value'] == 2.0
True
>>> result = list_by_tag(mgr, 'X')
>>> result[0].node_name == 'A'
True
``` 