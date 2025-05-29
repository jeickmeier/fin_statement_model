# Logging Guidelines for fin_statement_model

This document provides comprehensive guidelines for implementing consistent logging throughout the fin_statement_model library.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Logging Configuration](#logging-configuration)
3. [Best Practices](#best-practices)
4. [Log Levels](#log-levels)
5. [Common Patterns](#common-patterns)
6. [Performance Considerations](#performance-considerations)
7. [Troubleshooting](#troubleshooting)

## Quick Start

### Basic Usage in a Module

Every module should follow this pattern:

```python
import logging

# Always use __name__ for the logger name
logger = logging.getLogger(__name__)

class MyClass:
    def my_method(self):
        logger.info("Starting my_method execution")
        try:
            result = self._do_something()
            logger.debug(f"Operation completed with result: {result}")
            return result
        except Exception as e:
            logger.exception("Failed to execute my_method")
            raise
```

### Enabling Logging in Applications

For applications using the library:

```python
from fin_statement_model import logging_config

# Basic setup - logs WARNING and above to console
logging_config.setup_logging()

# Detailed setup with INFO level and file output
logging_config.setup_logging(
    level="INFO",
    detailed=True,
    log_to_file="fin_model.log"
)

# Using environment variables
# Set FSM_LOG_LEVEL=DEBUG and FSM_LOG_FORMAT for custom configuration
```

## Logging Configuration

### Environment Variables

- `FSM_LOG_LEVEL`: Sets the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `FSM_LOG_FORMAT`: Sets custom log format string

### Programmatic Configuration

```python
from fin_statement_model import logging_config

# Standard configuration
logging_config.setup_logging(level="INFO")

# Detailed configuration with file output
logging_config.setup_logging(
    level="DEBUG",
    detailed=True,  # Includes file/line/function info
    log_to_file="app.log",
    format_string="%(asctime)s - %(name)s - %(message)s"
)
```

## Best Practices

### 1. Logger Naming

Always use `__name__` for logger names:

```python
# ✅ Correct
logger = logging.getLogger(__name__)

# ❌ Incorrect
logger = logging.getLogger("my_custom_logger")
logger = logging.getLogger("fin_statement_model.my_module")
```

### 2. Contextual Messages

Include relevant context in log messages:

```python
# ✅ Good - provides context
logger.info(f"Loaded {len(metrics)} metrics from {filepath}")
logger.error(f"Failed to calculate node '{node_name}' for period '{period}': {error}")

# ❌ Bad - lacks context
logger.info("Metrics loaded")
logger.error("Calculation failed")
```

### 3. Exception Logging

Use `logger.exception()` in except blocks to capture stack traces:

```python
try:
    result = risky_operation()
except ValidationError as e:
    # For expected errors, log at appropriate level
    logger.warning(f"Validation failed: {e}")
    raise
except Exception:
    # For unexpected errors, use exception() to capture stack trace
    logger.exception("Unexpected error in risky_operation")
    raise
```

### 4. Structured Logging

For complex data, use structured formats:

```python
# Log complex objects in a readable way
logger.debug(
    "Graph state: nodes=%d, edges=%d, periods=%s",
    len(graph.nodes),
    len(graph.edges),
    graph.get_periods()
)

# For debugging, format data structures nicely
import json
logger.debug(f"Configuration: {json.dumps(config, indent=2)}")
```

## Log Levels

### DEBUG
Detailed information for diagnosing problems. Not shown in production.

```python
logger.debug(f"Entering calculation for node {node.name}, inputs: {inputs}")
logger.debug(f"Cache hit for key: {cache_key}")
```

### INFO
General informational messages about normal operation.

```python
logger.info(f"Successfully loaded {count} financial statements")
logger.info(f"Forecast completed for {len(nodes)} nodes")
```

### WARNING
Something unexpected happened but the application is still working.

```python
logger.warning(f"Missing data for period {period}, using default value")
logger.warning(f"Deprecated method called: {method_name}")
```

### ERROR
A serious problem occurred, the current operation cannot proceed.

```python
logger.error(f"Failed to connect to data source: {source_name}")
logger.error(f"Invalid calculation formula: {formula}")
```

### CRITICAL
A very serious error occurred, the program may be unable to continue.

```python
logger.critical("Database connection lost, cannot continue")
logger.critical(f"Core configuration file missing: {config_file}")
```

## Common Patterns

### Module Initialization

```python
import logging

logger = logging.getLogger(__name__)

class FinancialCalculator:
    def __init__(self, config):
        logger.info(f"Initializing {self.__class__.__name__} with config: {config}")
        self.config = config
```

### Method Entry/Exit (for debugging)

```python
def complex_calculation(self, data):
    logger.debug(f"Entering complex_calculation with {len(data)} data points")
    try:
        result = self._process_data(data)
        logger.debug(f"Exiting complex_calculation with result type: {type(result)}")
        return result
    except Exception:
        logger.exception("Failed in complex_calculation")
        raise
```

### Progress Tracking

```python
def process_large_dataset(self, items):
    total = len(items)
    logger.info(f"Starting to process {total} items")
    
    for i, item in enumerate(items):
        if i % 100 == 0 and i > 0:
            logger.info(f"Progress: {i}/{total} items processed ({i/total*100:.1f}%)")
        
        self._process_item(item)
    
    logger.info(f"Completed processing all {total} items")
```

### Conditional Warnings

```python
def validate_data(self, data):
    issues = []
    
    if data.get("revenue", 0) < 0:
        issues.append("Negative revenue detected")
    
    if not data.get("period"):
        issues.append("Missing period information")
    
    if issues:
        logger.warning(f"Data validation issues: {', '.join(issues)}")
    
    return len(issues) == 0
```

## Performance Considerations

### 1. Lazy Evaluation

For expensive operations, check if the log level is enabled:

```python
# ✅ Good - expensive operation only runs if DEBUG is enabled
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Graph structure: {expensive_graph_analysis()}")

# ❌ Bad - expensive operation always runs
logger.debug(f"Graph structure: {expensive_graph_analysis()}")
```

### 2. String Formatting

Use lazy formatting with % formatting or f-strings appropriately:

```python
# ✅ Good - formatting only happens if message is logged
logger.debug("Processing node %s with value %s", node_name, value)

# Also fine for simple cases
logger.info(f"Loaded {count} items")

# ❌ Avoid format() for log messages
logger.debug("Processing {}".format(expensive_operation()))
```

### 3. Bulk Operations

For operations in tight loops, consider batching log messages:

```python
errors = []
for item in large_list:
    try:
        process(item)
    except Exception as e:
        errors.append(f"{item}: {e}")

if errors:
    logger.error(f"Failed to process {len(errors)} items: {errors[:5]}")  # Show first 5
```

## Troubleshooting

### No Log Output

If you're not seeing expected log output:

1. Check if logging is configured:
   ```python
   from fin_statement_model import logging_config
   logging_config.setup_logging(level="DEBUG")
   ```

2. Verify logger hierarchy:
   ```python
   # Check effective level
   print(logger.getEffectiveLevel())
   
   # Check handlers
   print(logger.handlers)
   ```

3. Ensure logger name is correct:
   ```python
   # Should start with 'fin_statement_model'
   print(logger.name)
   ```

### Too Much Output

To reduce noise from specific modules:

```python
# Reduce verbosity of specific loggers
logging.getLogger("fin_statement_model.io.formats").setLevel(logging.WARNING)
logging.getLogger("fin_statement_model.core.graph.traverser").setLevel(logging.WARNING)
```

### Testing with Logging

For unit tests, you can capture log output:

```python
import logging
from unittest import TestCase

class TestWithLogging(TestCase):
    def test_log_output(self):
        with self.assertLogs('fin_statement_model.my_module', level='INFO') as cm:
            my_function()
        
        self.assertIn('Expected log message', cm.output[0])
```

## Summary

Consistent logging is crucial for debugging, monitoring, and maintaining the fin_statement_model library. By following these guidelines:

1. Always use `logger = logging.getLogger(__name__)`
2. Choose appropriate log levels
3. Include context in messages
4. Use `logger.exception()` for unexpected errors
5. Consider performance implications
6. Configure logging appropriately for your use case

Remember: Good logging makes debugging easier and helps users understand what the library is doing. 