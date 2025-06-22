# I/O Subsystem (`fin_statement_model.io`)

This package provides a unified, extensible interface for reading and writing financial model data from and to various formats. It is built around a registry-based architecture that allows for easy addition of new data sources and targets.

The primary entry points for all I/O operations are the facade functions `read_data` and `write_data`.

## Key Features

- **Unified API**: Simple `read_data` and `write_data` functions for all supported formats.
- **Extensible**: New readers and writers can be added by subclassing `DataReader`/`DataWriter` and registering them with a decorator.
- **Configuration-driven**: Uses Pydantic models for type-safe and validated configuration of I/O handlers.
- **Multiple Formats**: Out-of-the-box support for common formats like Excel, CSV, dictionaries, and the Financial Modeling Prep (FMP) API.

## Basic Usage

The easiest way to use the I/O system is through the `read_data` and `write_data` facade functions.

### Reading Data

To read data, specify the `format_type`, the `source`, and any necessary configuration.

**Example: Reading from an Excel file**

```python
from fin_statement_model.io import read_data

# Assumes 'my_data.xlsx' has items in the first column and periods in the first row.
graph = read_data(
    format_type="excel",
    source="path/to/my_data.xlsx",
    config={"sheet_name": "Q3-Data"}
)
```

**Example: Reading from the FMP API**

```python
from fin_statement_model.io import read_data

# Fetch Apple's annual income statement
graph = read_data(
    format_type="fmp",
    source="AAPL",
    config={
        "statement_type": "income_statement",
        "api_key": "YOUR_FMP_API_KEY",
        "limit": 5,
    }
)
```

### Writing Data

To write data, provide the `format_type`, the `graph` object, and a `target`.

**Example: Writing to an Excel file**

```python
from fin_statement_model.io import write_data
from fin_statement_model.core import Graph

# Assume 'graph' is a populated Graph object
write_data(
    format_type="excel",
    graph=graph,
    target="path/to/output.xlsx",
    config={"sheet_name": "Exported Data"}
)
```

**Example: Exporting to a dictionary**

```python
from fin_statement_model.io import write_data
from fin_statement_model.core import Graph

# Assume 'graph' is a populated Graph object
data_dict = write_data(
    format_type="dict",
    graph=graph,
    target=None  # Target is ignored for in-memory writers
)
```

## Supported Formats

| Format | Reader (`read_data`) | Writer (`write_data`) | Description |
|---|---|---|---|
| `excel` | ✓ | ✓ | Reads/writes "wide" format data from/to `.xlsx` files. |
| `csv` | ✓ | ✗ | Reads "long" format data from `.csv` files. |
| `dict` | ✓ | ✓ | Reads/writes from/to a nested Python dictionary. |
| `dataframe`| ✓ | ✓ | Reads/writes from/to a `pandas.DataFrame`. |
| `fmp` | ✓ | ✗ | Fetches data from the Financial Modeling Prep API. |
| `markdown` | ✗ | ✓ | Renders a financial statement to a Markdown table. |
| `graph_definition_dict` | ✓ | ✓ | Serializes/deserializes the entire graph structure. |

## Package Structure

The `io` package is organized into several sub-packages:

- **`core/`**: Contains the foundational components: base classes (`DataReader`, `DataWriter`), the handler registry, and shared mixins for configuration, validation, and error handling.
- **`formats/`**: Provides the concrete reader and writer implementations for each specific data format.
- **`config/`**: Defines the Pydantic configuration models for all I/O handlers.
- **`adjustments/`**: Contains specialized functions and models for importing/exporting `Adjustment` objects.
- **`graph/`**: Provides helpers for serializing and deserializing the entire `Graph` definition.
- **`statements/`**: Contains utilities for I/O operations related to structured financial statements.

## Extensibility: Adding a New Reader

The registry system makes it easy to add support for new formats. To add a new reader:

1.  **Create a Configuration Model**: Define a Pydantic `BaseModel` in `fin_statement_model/io/config/models.py` for your reader's options.
2.  **Implement the Reader Class**: Create a new class that inherits from `DataReader` (or a more specific base like `DataFrameReaderBase`) in `fin_statement_model/io/formats/`.
3.  **Implement the `read` method**: This method contains the logic for reading the data and returning a `Graph` object.
4.  **Register the Reader**: Add the `@register_reader` decorator to your class, specifying the format name and the configuration schema.

**Example Skeleton:**

```python
# In fin_statement_model/io/formats/my_format_reader.py
from fin_statement_model.io.core import DataReader
from fin_statement_model.io.core.registry import register_reader
from fin_statement_model.io.config.models import MyFormatReaderConfig # Your new config model
from fin_statement_model.core.graph import Graph
from typing import Any

@register_reader("my_format", schema=MyFormatReaderConfig)
class MyFormatReader(DataReader):
    def __init__(self, cfg: MyFormatReaderConfig):
        self.cfg = cfg

    def read(self, source: Any, **kwargs: Any) -> Graph:
        # ... your reading logic here ...
        graph = Graph(periods=[...])
        # ... populate graph ...
        return graph
``` 