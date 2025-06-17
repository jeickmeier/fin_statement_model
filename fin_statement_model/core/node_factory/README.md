# Node Factory for fin_statement_model.core

The `node_factory` module provides a flexible, registry-driven system for creating, deserializing, and extending financial statement nodes, calculation nodes, and forecast nodes in the `fin_statement_model` library. It enables both simple and advanced workflows for building financial statement graphs, custom calculations, and forecast logic.

## Features
- **Registry-driven node creation**: Easily instantiate standard and custom nodes using builder functions.
- **Deserialization**: Reconstruct node graphs from serialized dictionaries.
- **Custom calculation nodes**: Wrap Python callables as calculation nodes for rapid prototyping.
- **Extensible registries**: Register new node types, calculation strategies, and forecast types via decorators.
- **Modular, lightweight imports**: Avoids heavy dependencies until needed.

---

## Basic Usage

### Creating a Financial Statement Item Node
```python
from fin_statement_model.core.node_factory import NodeFactory

node = NodeFactory.create_financial_statement_item('Revenue', {'2022': 100.0, '2023': 120.0})
print(node.name)  # Output: Revenue
```

### Creating a Calculation Node
```python
from fin_statement_model.core.node_factory import NodeFactory
# Assume n1, n2 are Node instances
node = NodeFactory.create_calculation_node(
    name='GrossProfit',
    inputs=[n1, n2],
    calculation_type='addition'
)
print(node.name)  # Output: GrossProfit
```

### Creating a Forecast Node
```python
from fin_statement_model.core.node_factory import NodeFactory
# Assume n1 is a Node instance
node = NodeFactory.create_forecast_node(
    forecast_type='simple',
    input_node=n1,
    base_period='2022',
    forecast_periods=['2023', '2024'],
    growth_params={'rate': 0.05}
)
print(node.name)  # Typically inherits from input_node
```

### Deserializing a Node from a Dictionary
```python
from fin_statement_model.core.node_factory import NodeFactory
# dct: dict representing a serialized node, ctx: context dict of existing nodes
node = NodeFactory.create_from_dict(dct, ctx)
print(node.name)
```

---

## Advanced Features

### Custom Calculation Nodes from Python Callables
```python
from fin_statement_model.core.node_factory import NodeFactory

def my_formula(a, b):
    return a + b
# Assume n1, n2 are Node instances
node = NodeFactory._create_custom_node_from_callable(
    name='CustomSum',
    inputs=[n1, n2],
    formula=my_formula
)
print(node.name)  # Output: CustomSum
```

### Registering New Calculation Types
```python
from fin_statement_model.core.node_factory.registries import calc_alias

@calc_alias('my_custom_calc')
class MyCustomCalculation:
    ...  # Implement calculation logic
```

### Registering New Node Types
```python
from fin_statement_model.core.node_factory.registries import node_type

@node_type('my_special_node')
class MySpecialNode:
    ...  # Implement node logic
```

### Registering New Forecast Types
```python
from fin_statement_model.core.node_factory.registries import forecast_type

@forecast_type('my_forecast')
class MyForecastNode:
    ...  # Implement forecast logic
```

---

## API Reference

### NodeFactory (class)
- `create_financial_statement_item(name, values)`
- `create_calculation_node(name, inputs, calculation_type, ...)`
- `create_forecast_node(forecast_type, input_node, base_period, forecast_periods, ...)`
- `create_from_dict(data, ctx=None, context=None)`
- `_create_custom_node_from_callable(name, inputs, formula, description=None)`

### Registries
- `CalculationAliasRegistry`, `NodeTypeRegistry`, `ForecastTypeRegistry`
- Decorators: `calc_alias`, `node_type`, `forecast_type`

---

## Extending the Node Factory
- Register new node/calculation/forecast types using the provided decorators.
- Custom nodes and calculations are automatically available to the builder and deserializer functions after registration.

---

## Notes
- All builder and registry functions are designed for extensibility and modularity.
- The node factory is the recommended entry point for all node creation and deserialization tasks in `fin_statement_model`. 