# Preprocessing Module

The **`preprocessing`** module of **`fin_statement_model`** provides tools to clean, normalize, transform, and format financial data before loading into the core graph engine or forecasting layer.

## Features

- **DataTransformer** interface and **CompositeTransformer** for building transformation pipelines.
- **TransformerFactory** for discovering, registering, and instantiating transformers by name.
- **TransformationService** offering high-level methods:
  - `normalize_data` – apply normalization strategies (percent, min-max, z-score, scale).
  - `transform_time_series` – compute growth rates, moving averages, CAGR, YoY, QoQ.
  - `convert_periods` – aggregate or convert reporting periods (quarterly→annual, TTM).
  - `format_statement` – apply statement-specific formatting (subtotals, sign conventions).
  - `create_transformation_pipeline` & `apply_transformation_pipeline` – build and execute custom pipelines.
- Built-in transformers:
  - **NormalizationTransformer**
  - **TimeSeriesTransformer**
  - **PeriodConversionTransformer**
  - **StatementFormattingTransformer**
- Pydantic config models:
  - `NormalizationConfig`, `TimeSeriesConfig`, `PeriodConversionConfig`, `StatementFormattingConfig`
- Preprocessing exceptions:
  - `PreprocessingError`, `TransformerRegistrationError`, `TransformerConfigurationError`,
    `NormalizationError`, `PeriodConversionError`, `TimeSeriesError`

## Basic Usage

```python
from fin_statement_model.preprocessing import TransformationService
import pandas as pd

# Sample DataFrame
df = pd.DataFrame({
    'revenue': [1000, 1100, 1200],
    'cogs': [600, 650, 700]
}, index=['2021', '2022', '2023'])

service = TransformationService()

# 1. Normalize as percentage of revenue
normalized = service.normalize_data(
    df,
    normalization_type='percent_of',
    reference='revenue'
)

# 2. Compute year-over-year growth
yoy = service.transform_time_series(
    df, transformation_type='yoy', periods=1
)

# 3. Aggregate quarterly data to annual totals
# (Assume df.index is quarterly dates)
annual = service.convert_periods(
    df, conversion_type='quarterly_to_annual', aggregation='sum'
)

# 4. Format income statement
formatted = service.format_statement(
    df, statement_type='income_statement', add_subtotals=True
)

# 5. Custom pipeline: min-max → 1-period growth
pipeline_config = [
    {'name': 'normalization', 'normalization_type': 'minmax'},
    {'name': 'time_series', 'transformation_type': 'growth_rate', 'periods': 1},
]
result = service.apply_transformation_pipeline(df, pipeline_config)
```

## Extending Preprocessing

### Add a New Normalization Method

1. **Define the method** in `NormalizationType` (in `config.py`):
    ```python
    class NormalizationType(Enum):
        ...
        NEW_METHOD = 'new_method'
    ```
2. **Implement logic** in `normalization.py` inside `_normalize_dataframe`:
    ```python
    if self.normalization_type == NormalizationType.NEW_METHOD.value:
        # Your normalization algorithm here
    ```
3. **Use transformer** via `TransformationService` or `TransformerFactory` with name `'normalization'`.

### Add a New Period Conversion Type

1. **Extend enum** in `ConversionType` (in `config.py`):
    ```python
    class ConversionType(Enum):
        ...
        NEW_CONVERSION = 'new_conversion'
    ```
2. **Handle conversion** in `period_conversion.py` within `_convert_periods`:
    ```python
    elif self.conversion_type == ConversionType.NEW_CONVERSION.value:
        # Your aggregation or conversion logic
    ```
3. **Call** via `service.convert_periods(df, 'new_conversion', aggregation='...')`.

### Add a New Time Series Transformation

1. **Update enum** in `TransformationType` (in `config.py`):
    ```python
    class TransformationType(Enum):
        ...
        NEW_TRANSFORM = 'new_transform'
    ```
2. **Validate** in `TimeSeriesTransformer.__init__` and **implement** in `_transform_dataframe`:
    ```python
    elif self.transformation_type == 'new_transform':
        # Your transform logic, e.g., df['value_new'] = ...
    ```
3. **Invoke** with `service.transform_time_series(df, 'new_transform', ...)`.

## Configuration Models

You can provide `NormalizationConfig`, `TimeSeriesConfig`, `PeriodConversionConfig`, or `StatementFormattingConfig` to transformers directly:

```python
from fin_statement_model.preprocessing.config import NormalizationConfig
config = NormalizationConfig(normalization_type='scale_by', scale_factor=1e-6)
transformer = TransformerFactory.create_transformer('normalization', config=config)
```

## Exceptions

All preprocessing errors inherit from `FinancialModelError`:

- **PreprocessingError** – base class for all.
- **TransformerRegistrationError** – duplicate or invalid registration.
- **TransformerConfigurationError** – missing or invalid params.
- **NormalizationError** – errors during normalization.
- **PeriodConversionError** – errors converting periods.
- **TimeSeriesError** – errors in time series transforms.