# Configuration Subpackage

The `fin_statement_model.config` subpackage provides centralized, extensible configuration management for the entire library. It supports hierarchical loading, runtime overrides, environment variable integration, and a command-line interface for inspection and mutation.

## Basic Usage

### Accessing Configuration

```python
from fin_statement_model.config import get_config, cfg

# Get the full config object (Pydantic model)
config = get_config()
print(config.logging.level)  # e.g. 'WARNING'

# Get a single value by dotted path
level = cfg('logging.level')
print(level)  # 'WARNING'
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
print(get_config().forecasting.default_method)  # 'historical_growth'
```

### Type-Checked Access and Fallbacks

```python
from fin_statement_model.config import cfg, get_typed_config

timeout = cfg('api.api_timeout', default=30)  # fallback if not set
```

## Advanced Features

### Configuration Loading Order

1. **Defaults** (from Pydantic models)
2. **Project config file** (`.fsm_config.yaml` in cwd or parent dirs)
3. **User config file** (`fsm_config.yaml` in cwd or home dir)
4. **Environment variables** (prefixed with `FSM_`, e.g. `FSM_LOGGING_LEVEL`)
5. **Runtime overrides** (via `update_config()`)

Supported formats: YAML (`.yaml`, `.yml`) and JSON (`.json`).

### Environment Variable Parsing

- Environment variables are parsed to native types (bool, int, float, list, dict) when possible.
- Use double underscores (`__`) to denote nested config keys: `FSM_LOGGING__LEVEL=DEBUG` → `logging.level`.
- Legacy single underscore is also supported.

### Display Flags

Boolean display toggles are grouped under `config.display.flags`:

```python
from fin_statement_model.config import cfg

# Preferred (new)
include_notes = cfg('display.flags.include_notes_column')

# Legacy (still works)
include_notes = cfg('display.include_notes_column')
```

Available flags:

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

## Customization & Extending Configuration

### Adding New Configuration Options

1. **Define the field** in `fin_statement_model/config/models.py` (add to the relevant model).
2. **(Optional) Add validation** using `@field_validator`.
3. **Update documentation** (model docstring and this README).
4. **Access the new option** via `cfg('section.option')`.
5. **Override via environment**: `FSM_SECTION__OPTION=value`.
6. **Test**: Add/update tests under `tests/config`.

### Example: Adding a Feature Toggle

```python
class LoggingConfig(BaseModel):
    enable_new_feature: bool = Field(
        True, description="Enable the new experimental feature"
    )
```

## Command-Line Interface (CLI)

A Typer-based CLI is included for inspecting and mutating configuration from the terminal.

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

## Troubleshooting & FAQ

**Q: Why isn't my environment variable being picked up?**
- Ensure it is prefixed with `FSM_` and uses double underscores for nesting.
- Example: `FSM_API__FMP_API_KEY=yourkey` sets `api.fmp_api_key`.

**Q: How do I reset runtime overrides?**
- Use the CLI `reload` command or restart your Python process.

**Q: How do I add a new config option?**
- See the "Customization & Extending Configuration" section above.

**Q: Can I use JSON for config files?**
- Yes, `.json` files are supported alongside YAML.

**Q: How do I access deeply nested config values?**
- Use `cfg('section.subsection.option')` or `cfg(['section', 'subsection', 'option'])`.

For more, see the docstrings in each module or the API documentation. 