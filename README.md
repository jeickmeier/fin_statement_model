# Fin Statement Model

A pre-alpha library for building and analyzing financial statement models using a node-based graph structure.

## Configuration

Use the centralized configuration system to manage library settings at runtime:

```python
from fin_statement_model.config import update_config, cfg

# Override display settings
update_config({
    "display": {"default_units": "EUR Thousands", "scale_factor": 0.001}
})

# Access a specific value
print(cfg("display.default_units"))  # → 'EUR Thousands'
```

For more detailed configuration options and loading order, see the `fin_statement_model.config` subpackage.
