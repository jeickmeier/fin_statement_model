# I/O Format Implementations

This package contains the concrete `DataReader` and `DataWriter` implementations for each data format supported by the I/O subsystem.

Each submodule is responsible for a single format and contains the logic for reading from and/or writing to that format.

## Available Formats

| Format Name | Module(s) | Handler(s) | Description |
|---|---|---|---|
| `csv` | `csv_reader.py` | `CsvReader` | Reads data from comma-separated value files in a "long" format. |
| `dataframe` | `dataframe_reader.py`, `dataframe_writer.py` | `DataFrameReader`, `DataFrameWriter` | Reads from and writes to in-memory `pandas.DataFrame` objects. |
| `dict` | `dict_reader.py`, `dict_writer.py` | `DictReader`, `DictWriter` | Reads from and writes to nested Python dictionaries. |
| `excel` | `excel_reader.py`, `excel_writer.py` | `ExcelReader`, `ExcelWriter` | Reads from and writes to Microsoft Excel (`.xlsx`) files. |
| `fmp` | `fmp_reader.py` | `FmpReader` | Fetches financial statement data from the Financial Modeling Prep API. |
| `markdown` | `markdown_writer.py` | `MarkdownWriter` | Renders a `StatementStructure` to a formatted Markdown table. |
| `graph_definition_dict` | `io.graph.definition_io` | `GraphDefinitionReader`, `GraphDefinitionWriter` | Serializes and deserializes the entire graph state. | 