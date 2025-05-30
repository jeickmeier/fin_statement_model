# Financial Statement Model Error Hierarchy

This document describes the centralized error handling system for the `fin_statement_model` library.

## Base Exception

All exceptions in the library inherit from:

```python
FinancialModelError(Exception)
```

This ensures consistent error handling across the entire library.

## Core Error Classes

Located in `fin_statement_model.core.errors`:

### General Errors
- **`FinancialModelError`**: Base exception for all library errors
- **`ConfigurationError`**: Invalid configuration files or objects
- **`CalculationError`**: Errors during calculation operations
- **`NodeError`**: Issues related to graph nodes
- **`MissingInputError`**: Required calculation input is missing
- **`GraphError`**: Invalid graph structure or operations
- **`DataValidationError`**: Data validation failures
- **`CircularDependencyError`**: Circular dependency detected in calculations
- **`PeriodError`**: Invalid or missing periods
- **`StatementError`**: Issues related to financial statements
- **`StrategyError`**: Issues with calculation strategies
- **`TransformationError`**: Errors during data transformation
- **`MetricError`**: Issues with metric definitions or registry

## Package-Specific Error Classes

### Preprocessing Errors
Located in `fin_statement_model.preprocessing.errors`:

- **`PreprocessingError`**: Base for all preprocessing errors
- **`TransformerRegistrationError`**: Transformer registration issues
- **`TransformerConfigurationError`**: Invalid transformer configuration
- **`PeriodConversionError`**: Period conversion failures (inherits from `TransformationError`)
- **`NormalizationError`**: Normalization failures (inherits from `TransformationError`)
- **`TimeSeriesError`**: Time series transformation failures (inherits from `TransformationError`)

### Forecasting Errors
Located in `fin_statement_model.forecasting.errors`:

- **`ForecastingError`**: Base for all forecasting errors
- **`ForecastMethodError`**: Invalid or unsupported forecast methods
- **`ForecastConfigurationError`**: Invalid forecast configuration
- **`ForecastNodeError`**: Node-related forecast errors
- **`ForecastResultError`**: Forecast result access or manipulation errors

### IO Errors
Located in `fin_statement_model.io.exceptions`:

- **`IOError`**: Base for all I/O errors
- **`ReadError`**: Errors during data read/import operations
- **`WriteError`**: Errors during data write/export operations
- **`FormatNotSupportedError`**: Requested I/O format not supported

### Statement Errors
Located in `fin_statement_model.statements.errors`:

- **`StatementBuilderError`**: Errors during statement structure building (inherits from `StatementError`)
- **`StatementValidationError`**: Statement validation errors (inherits from `StatementError`)

Note: `StatementError` and `ConfigurationError` are imported from `core.errors` to avoid duplication.

### Extension Errors
Located in `fin_statement_model.extensions.llm.llm_client`:

- **`LLMClientError`**: Base for LLM client errors (inherits from `FinancialModelError`)
- **`LLMTimeoutError`**: LLM request timeout errors (inherits from `LLMClientError`)

## Usage Guidelines

1. **Always inherit from appropriate base classes**: New exceptions should inherit from the most specific relevant base class.

2. **Use structured error information**: Pass relevant context using the error class parameters (e.g., `node_id`, `period`, `details`).

3. **Avoid generic exceptions**: Replace `ValueError`, `TypeError`, etc. with appropriate custom exceptions.

4. **Import from the correct module**: 
   - Core errors from `fin_statement_model.core.errors`
   - Package-specific errors from their respective error modules

5. **Provide meaningful messages**: Include context about what operation failed and why.

## Example Usage

```python
from fin_statement_model.core.errors import CalculationError, NodeError
from fin_statement_model.preprocessing.errors import NormalizationError

# Raising an error with context
raise CalculationError(
    "Division by zero in profit margin calculation",
    node_id="profit_margin",
    period="2023-Q4",
    details={"revenue": 0, "net_income": 1000}
)

# Catching specific errors
try:
    result = normalizer.transform(data)
except NormalizationError as e:
    logger.error(f"Normalization failed: {e}")
    # Handle normalization-specific error
except FinancialModelError as e:
    logger.error(f"General library error: {e}")
    # Handle any library error
```

## Migration from Generic Exceptions

When updating code that uses generic exceptions:

```python
# OLD
raise ValueError("Invalid forecast method")

# NEW
from fin_statement_model.forecasting.errors import ForecastMethodError
raise ForecastMethodError(
    "Invalid forecast method",
    method=method_name,
    supported_methods=["linear", "exponential", "average"]
) 