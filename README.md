# Fin Statement Model
[![CI](https://github.com/jeickmeier/fin_statement_model/actions/workflows/ci.yml/badge.svg)](https://github.com/jeickmeier/fin_statement_model/actions/workflows/ci.yml)

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

## Logging Configuration

The library provides a centralized logging configuration system for consistent and flexible logging across all components. Use the `fin_statement_model.logging_config` module to control log levels, formats, and output destinations.

### Basic Usage

By default, the library attaches a `NullHandler` to avoid warnings if you do not configure logging. To enable logging output, call `setup_logging()` at application startup:

```python
from fin_statement_model import logging_config

logging_config.setup_logging(level="INFO")
```

### Advanced Usage

You can customize the log format, write logs to a file, or enable detailed output:

```python
from fin_statement_model import logging_config

logging_config.setup_logging(
    level="DEBUG",  # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format_string="%(asctime)s %(levelname)s %(message)s",  # Custom format
    log_file_path="fin_model.log",  # Write logs to a file
    detailed=True  # Use detailed format with file/line info
)
```

#### Environment Variables
- `FSM_LOG_LEVEL`: Set the default log level (e.g., `DEBUG`, `INFO`).
- `FSM_LOG_FORMAT`: Set a custom log format string.

See the `fin_statement_model/logging_config.py` docstrings for more details and best practices.
