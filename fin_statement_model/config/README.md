# Configuration Subpackage

The `fin_statement_model.config` subpackage provides centralized, extensible configuration management for the entire library. It supports hierarchical loading from files and environment variables, runtime overrides, and a simple, safe API for accessing values.

## File Structure

The package is organised into five *core* modules plus a dedicated **`subconfigs/`** package:

- **`models.py`**: A lightweight aggregator that imports and re-exports all sub-config models from `subconfigs` and defines the root `Config` container.
- **`subconfigs/`**: Contains one Pydantic module per logical configuration section (`APIConfig`, `DisplayConfig`, `ForecastingConfig`, `IOConfig`, `LoggingConfig`, `MetricsConfig`, `PreprocessingConfig`, `StatementsConfig`, `ValidationConfig`). Add or modify options here.
- **`access.py`**: Provides the primary user-facing helpers for *reading* configuration (`cfg`, `cfg_or_param`) and parsing environment variables.
- **`loader.py`**: Implements the pure, stateless logic for discovering and merging configuration from all sources (defaults, files, environment).
- **`store.py`**: Manages the thread-safe, in-memory singleton that holds the live configuration. It provides the `get_config()` and `update_config()` helpers for mutation.
- **`logging_hook.py`**: A small utility to re-apply logging settings whenever the configuration is changed.

## Basic Usage

The public API is exposed directly from `fin_statement_model.config`.

### Accessing Configuration

The recommended way to read configuration is with the `cfg` helper.

```python
from fin_statement_model.config import cfg

# Get a single value by dotted path, with a fallback default
timeout = cfg('api.api_timeout', default=30)
print(timeout)  # 30

# Access a nested model
flags = cfg('display.flags')
print(flags.include_notes_column) # False
```

For cases where you need the full, typed configuration object:

```python
from fin_statement_model.config import get_config

# Get the full config object (a Pydantic model)
config = get_config()
print(config.logging.level)  # e.g. 'WARNING'
```

### Updating Configuration at Runtime

Use `update_config()` to merge in new values. This invalidates the old configuration and causes it to be reloaded on the next access, applying all override rules correctly.

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

## Advanced Features

### Configuration Loading Order

Configuration is loaded in a layered hierarchy, where each subsequent layer can override the previous ones. The order of precedence is:

1.  **Defaults**: Hardcoded defaults defined in the Pydantic models under `config/subconfigs` (and re-exported via `models.py`).
2.  **Project Config File**: From `.fsm_config.yaml` found in the current working directory or any parent directory.
3.  **User Config File**: From `fsm_config.yaml` found in the current working directory or `~/.fsm_config.yaml`.
4.  **.env File**: Environment variables loaded from the first `.env` file found in the current directory or parents.
5.  **Environment Variables**: Live environment variables prefixed with `FSM_`.
6.  **Runtime Overrides**: Values passed programmatically to `update_config()`.

Supported file formats are YAML (`.yaml`, `.yml`) and JSON (`.json`).

### Environment Variable Parsing

-   Environment variables are automatically parsed to native Python types (bool, int, float, lists, dicts) where possible.
-   Use double underscores (`__`) to denote nested config keys: `FSM_LOGGING__LEVEL=DEBUG` sets `logging.level`.
-   The legacy single underscore separator is also supported as a fallback.

### Display Flags

Boolean toggles for display and formatting are grouped under `config.display.flags` for clarity.

```python
from fin_statement_model.config import cfg

# Access a flag via its full path
include_notes = cfg('display.flags.include_notes_column')

# The legacy path still works for convenience
include_notes_legacy = cfg('display.include_notes_column')

assert include_notes == include_notes_legacy
```

A full list of flags can be found in the `DisplayFlags` model located in `fin_statement_model/config/subconfigs/display_config.py`.

## Customization & Extending Configuration

### Adding a New Config Option

1.  **Define the field**: Open the appropriate sub-config module inside `fin_statement_model/config/subconfigs/` (e.g., `api_config.py`) and add the field to the relevant Pydantic model. Provide a type, a `Field` with a default value, and a description.
2.  **(Optional) Add validation**: Use Pydantic's `@field_validator` decorator within the model to add custom validation logic.
3.  **Update documentation**: Add a row to the relevant table in this README and update the model's docstring.
4.  **Access the new option**: Use `cfg('section.new_option_name')`.
5.  **Override via environment**: Set an environment variable like `FSM_SECTION__NEW_OPTION_NAME=value`.
6.  **Test**: Add or update tests under `tests/config` to cover the new option.

## Troubleshooting & FAQ

**Q: Why isn't my environment variable being picked up?**
A: Ensure it's prefixed with `FSM_` and uses double underscores for nesting (e.g., `FSM_API__FMP_API_KEY=yourkey`). Also, check that a value for the same key isn't being set in a runtime override via `update_config()`, which has higher precedence.

**Q: How do I reset runtime overrides?**
A: Restart the Python process. The configuration is held in-memory for the life of the process.

**Q: Can I use JSON for config files?**
A: Yes, `.json` files are supported alongside `.yaml` and `.yml`.

**Q: How do I access deeply nested config values?**
A: Use dotted-path strings: `cfg('section.subsection.option')`.

For more details, see the docstrings in the respective modules (`models.py`, the files under `subconfigs/`, `access.py`, etc.). 