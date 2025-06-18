# Configuration Subpackage

The `fin_statement_model.config` subpackage provides centralized configuration management for the library.
It includes:

- **Models** (`models.py`): Pydantic models defining all configuration options and defaults.
- **Manager** (`manager.py`): `ConfigManager` class to load and merge settings from defaults, project/user files, environment variables, and runtime overrides.
- **Helpers** (`helpers.py`): Utility functions (`cfg`, `get_typed_config`, `cfg_or_param`) for easy access to configuration values.

## Usage

### Retrieving Configuration

```python
from fin_statement_model.config import get_config

config = get_config()
print(config.logging.level)  # e.g. 'WARNING'
```

### Updating Configuration at Runtime

```python
from fin_statement_model.config import update_config, get_config

# Override forecasting defaults
update_config({
  'forecasting': {
    'default_method': 'historical_growth',
    'default_periods': 5,
  }
})
print(get_config().forecasting.default_method)
# 'historical_growth'
```

### Accessing Individual Values

```python
from fin_statement_model.config import cfg, get_typed_config

# Get with default fallback
db_host = cfg('database.host', default='localhost')
# Type-checked access
timeout = get_typed_config('api.api_timeout', int, default=30)
```

## Configuration Loading Order

1. **Defaults** defined in Pydantic models
2. **Project config file** (`.fsm_config.yaml`) in cwd or parent directories
3. **User config file** (`fsm_config.yaml`) in cwd or home directory
4. **Environment variables** prefixed with `FSM_` (e.g. `FSM_LOGGING_LEVEL`)
5. **Runtime overrides** via `update_config()`

Supported config file formats: YAML (`.yaml`, `.yml`) and JSON (`.json`).

Environment variables are no longer auto-consumed; use `update_config()` for overrides.

## Adding New Configuration Options

To introduce a new feature or default:

1. **Define the field**
   In `fin_statement_model/config/models.py`, locate the relevant model (e.g., `LoggingConfig`, `IOConfig`, or root `Config`) and add a new attribute:
   ```python
   class LoggingConfig(BaseModel):
       # New feature toggle
       enable_new_feature: bool = Field(
           True, description="Enable the new experimental feature"
       )
   ```

2. **Provide validation** (optional)
   If custom validation is needed, add a `@field_validator`:
   ```python
   @field_validator('enable_new_feature')
   def _validate_new_feature(cls, v: bool) -> bool:
       if not isinstance(v, bool):
           raise ValueError('enable_new_feature must be boolean')
       return v
   ```

3. **Update documentation**
   - Add descriptions/examples to the model docstring in `models.py`.
   - Update this README if necessary.

4. **Access the new option**
   ```python
   from fin_statement_model.config import cfg
   is_enabled = cfg('logging.enable_new_feature', default=False)
   ```

5. **Override via environment**
   Use `FSM_LOGGING_ENABLE_NEW_FEATURE=true` to override.

6. **Testing**
   Add or update tests under `tests/config` (if present) to verify behavior.

## Display Flags (0.2+)

Boolean display toggles are now grouped under `config.display.flags` instead of living directly on `display`.
Legacy attribute access is still supported via a thin shim, but **new code should prefer the nested path**:

```python
from fin_statement_model.config import cfg

# Old (still works)
include_notes = cfg('display.include_notes_column')

# New preferred form
include_notes = cfg('display.flags.include_notes_column')
```

Flags available:

| Flag | Purpose | Default |
|------|---------|---------|
| `apply_sign_conventions` | Show revenues positive, expenses negative, etc. | `True` |
| `include_empty_items` | Include items that have no data | `False` |
| `include_metadata_cols` | Add internal metadata columns to exported DataFrames | `False` |
| `add_is_adjusted_column` | Add `<period>_is_adjusted` boolean columns | `False` |
| `include_units_column` | Add `units` column with currency / units | `False` |
| `include_css_classes` | Append `css_class` column for HTML export | `False` |
| `include_notes_column` | Append `notes` column with note references | `False` |
| `apply_item_scaling` | Apply per-item scaling factors | `True` |
| `apply_item_formatting` | Use per-item number formats | `True` |
| `apply_contra_formatting` | Format contra items with parentheses/brackets | `True` |
| `add_contra_indicator_column` | Add `is_contra` indicator column | `False` |

## Command-Line Interface

A tiny Typer-based CLI is included for inspecting and mutating configuration at the terminal.
After installing the package you can invoke it via the module path or, if you enabled the
entry-point, the `fsm-config` shortcut.

```bash
# Show full config (YAML)
python -m fin_statement_model.config.cli show

# Show a single value
fsm-config show logging.level

# Update a value (JSON parsing is automatic)
fsm-config set forecasting.default_periods 10

# Persist current config to disk (defaults to ~/.fsm_config.yaml)
fsm-config save
``` 