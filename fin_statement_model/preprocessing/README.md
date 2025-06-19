# Preprocessing Module

The **`preprocessing`** module of **`fin_statement_model`** provides tools to clean, normalize, transform, and format financial data before loading into the core graph engine or forecasting layer.

## Table of Contents
- [Basic Usage](#basic-usage)
- [Core Features](#core-features)
- [Advanced Features](#advanced-features)
- [Best Practices](#best-practices)
- [Extending the Module](#extending-the-module)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Troubleshooting](#troubleshooting)

## Basic Usage

Get started quickly with the high-level `TransformationService` API:

```python
from fin_statement_model.preprocessing import TransformationService
import pandas as pd

# Sample quarterly financial data
df = pd.DataFrame({
    'revenue': [1000, 1100, 1200, 1300],
    'cogs': [600, 650, 700, 750],
    'opex': [200, 220, 240, 260]
}, index=pd.date_range('2023-03-31', periods=4, freq='Q'))

service = TransformationService()

# 1. Express everything as % of revenue
normalized = service.normalize_data(
    df,
    normalization_type='percent_of',
    reference='revenue'
)
print(normalized)
#             revenue  cogs  opex
# 2023-03-31   100.0  60.0  20.0
# 2023-06-30   100.0  59.1  20.0
# 2023-09-30   100.0  58.3  20.0
# 2023-12-31   100.0  57.7  20.0

# 2. Calculate quarter-over-quarter growth
qoq = service.transform_time_series(
    df, transformation_type='qoq', periods=1
)
print(qoq[['revenue_qoq', 'cogs_qoq']])
#             revenue_qoq  cogs_qoq
# 2023-03-31         NaN       NaN
# 2023-06-30        10.0      8.33
# 2023-09-30         9.1      7.69
# 2023-12-31         8.3      7.14

# 3. Convert to annual totals
annual = service.convert_periods(
    df, conversion_type='quarterly_to_annual', aggregation='sum'
)
print(annual)
#       revenue  cogs  opex
# 2023    4600  2700   920
```

## Core Features

The module provides these essential components:

- **TransformationService**: High-level API for common operations:
  - `normalize_data()` – Normalize using various strategies
  - `transform_time_series()` – Time-based transformations
  - `convert_periods()` – Period aggregation/conversion
  - `format_statement()` – Statement-specific formatting

- **Built-in Transformers**:
  - `NormalizationTransformer`: Percent-of, min-max, z-score, scaling
  - `TimeSeriesTransformer`: Growth rates, moving averages, YoY/QoQ
  - `PeriodConversionTransformer`: Period aggregation and TTM
  - `StatementFormattingTransformer`: Statement-specific formatting

## Advanced Features

### 1. Custom Transformation Pipelines

Chain multiple transformations together:

```python
# Pipeline: Scale to millions → Calculate YoY growth → Convert to annual
pipeline_config = [
    {
        'name': 'normalization',
        'normalization_type': 'scale_by',
        'scale_factor': 1e-6
    },
    {
        'name': 'time_series',
        'transformation_type': 'yoy',
        'periods': 4
    },
    {
        'name': 'period_conversion',
        'conversion_type': 'quarterly_to_annual',
        'aggregation': 'mean'  # Average the YoY rates
    }
]

result = service.apply_transformation_pipeline(df, pipeline_config)
```

### 2. Custom Normalization Methods

Register your own normalization functions:

```python
from typing import Callable
import pandas as pd

def log_normalize(df: pd.DataFrame, transformer: 'NormalizationTransformer') -> pd.DataFrame:
    """Apply log normalization to all columns."""
    result = df.copy()
    for col in df.columns:
        result[col] = np.log(df[col])
    return result

# Register the custom method
NormalizationTransformer.register_custom_method('log', log_normalize)

# Use it through the service
normalized = service.normalize_data(df, normalization_type='log')
```

### 3. Composite Transformers

Create reusable transformation combinations:

```python
from fin_statement_model.preprocessing import CompositeTransformer

# Create individual transformers
normalizer = TransformerFactory.create_transformer(
    'normalization',
    normalization_type='percent_of',
    reference='revenue'
)
time_series = TransformerFactory.create_transformer(
    'time_series',
    transformation_type='yoy',
    periods=4
)

# Combine them
pipeline = CompositeTransformer([normalizer, time_series])
result = pipeline.execute(df)
```

## Best Practices

1. **Data Quality**:
   - Always validate index types (DatetimeIndex for time series)
   - Handle missing values before transformation
   - Check for zero/negative values when using percent/log transforms

2. **Performance**:
   - Use CompositeTransformer for multiple operations (avoids copies)
   - Pre-filter columns to minimize unnecessary transformations
   - Consider chunking for very large datasets

3. **Configuration**:
   - Use Pydantic config models for type safety
   - Store common configurations in YAML/JSON
   - Validate all parameters before transformation

## Extending the Module

### Add a New Normalization Method

1. **Define the method** in `NormalizationType`:
    ```python
    class NormalizationType(Enum):
        ...
        NEW_METHOD = 'new_method'
    ```
2. **Implement logic** in `_normalize_dataframe`:
    ```python
    if self.normalization_type == NormalizationType.NEW_METHOD.value:
        # Your normalization algorithm here
    ```

### Add a New Period Conversion

1. **Extend enum** in `ConversionType`:
    ```python
    class ConversionType(Enum):
        ...
        NEW_CONVERSION = 'new_conversion'
    ```
2. **Handle conversion** in `_convert_periods`:
    ```python
    elif self.conversion_type == ConversionType.NEW_CONVERSION.value:
        # Your conversion logic
    ```

### Add a New Time Series Transform

1. **Update enum** in `TransformationType`:
    ```python
    class TransformationType(Enum):
        ...
        NEW_TRANSFORM = 'new_transform'
    ```
2. **Implement** in `_transform_dataframe`:
    ```python
    elif self.transformation_type == 'new_transform':
        # Your transform logic
    ```

## Configuration

Use type-safe Pydantic models for configuration:

```python
from fin_statement_model.preprocessing.config import NormalizationConfig

# Create config
config = NormalizationConfig(
    normalization_type='scale_by',
    scale_factor=1e-6
)

# Use with transformer
transformer = TransformerFactory.create_transformer(
    'normalization',
    config=config
)
```

## Error Handling

All errors inherit from `FinancialModelError`:

- **PreprocessingError**: Base for all preprocessing errors
- **TransformerRegistrationError**: Registration issues
- **TransformerConfigurationError**: Invalid configuration
- **NormalizationError**: Normalization failures
- **PeriodConversionError**: Period conversion issues
- **TimeSeriesError**: Time series transformation errors

Example error handling:

```python
from fin_statement_model.preprocessing.errors import NormalizationError

try:
    normalized = service.normalize_data(
        df,
        normalization_type='percent_of',
        reference='non_existent_column'
    )
except NormalizationError as e:
    print(f"Normalization failed: {e}")
    # Handle error appropriately
```

## Troubleshooting

Common issues and solutions:

1. **"Invalid index for time series transformation"**
   - Ensure DataFrame has DatetimeIndex
   - Convert string dates: `df.index = pd.to_datetime(df.index)`

2. **"Reference column not found"**
   - Check column names are exact matches
   - Verify reference column exists in DataFrame

3. **"Period conversion failed"**
   - Confirm input data frequency matches conversion type
   - Check for missing periods in time series

4. **"NaN values in output"**
   - Check for division by zero in percent_of normalization
   - Verify sufficient periods for rolling calculations
   - Handle missing values before transformation

5. **"Transformer registration failed"**
   - Ensure unique transformer names
   - Verify transformer class inherits from DataTransformer