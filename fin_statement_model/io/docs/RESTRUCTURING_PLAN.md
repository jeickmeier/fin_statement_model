# IO Module Restructuring Plan

## Phase 1: Create New Directory Structure

```bash
# Create core directories
mkdir -p fin_statement_model/io/core
mkdir -p fin_statement_model/io/formats/{excel,csv,dataframe,dict,api,markdown}
mkdir -p fin_statement_model/io/specialized
mkdir -p fin_statement_model/io/docs

# Create __init__.py files
touch fin_statement_model/io/core/__init__.py
touch fin_statement_model/io/formats/__init__.py
touch fin_statement_model/io/formats/{excel,csv,dataframe,dict,api,markdown}/__init__.py
touch fin_statement_model/io/specialized/__init__.py
```

## Phase 2: Move Core Components

### 2.1 Core Module
```bash
# Move base classes and registry
mv fin_statement_model/io/base.py fin_statement_model/io/core/base.py
mv fin_statement_model/io/registry_base.py fin_statement_model/io/core/registry.py

# Extract mixins from base_implementations.py and utils.py
# Create fin_statement_model/io/core/mixins.py with:
# - FileBasedReader
# - ConfigurableReaderMixin
# - DataFrameBasedWriter
# - BatchProcessingMixin
# - ValueExtractionMixin
# - ValidationResultCollector
# - handle_read_errors decorator
# - handle_write_errors decorator
```

### 2.2 Update Imports in Core
- Update `registry.py` to import from `core.base`
- Merge registry functions from old `registry.py` into `core/registry.py`

## Phase 3: Move Format-Specific Implementations

### 3.1 Excel Format
```bash
mv fin_statement_model/io/readers/excel.py fin_statement_model/io/formats/excel/reader.py
mv fin_statement_model/io/writers/excel.py fin_statement_model/io/formats/excel/writer.py
```

### 3.2 CSV Format
```bash
mv fin_statement_model/io/readers/csv.py fin_statement_model/io/formats/csv/reader.py
```

### 3.3 DataFrame Format
```bash
mv fin_statement_model/io/readers/dataframe.py fin_statement_model/io/formats/dataframe/reader.py
mv fin_statement_model/io/writers/dataframe.py fin_statement_model/io/formats/dataframe/writer.py
```

### 3.4 Dict Format
```bash
mv fin_statement_model/io/readers/dict.py fin_statement_model/io/formats/dict/reader.py
mv fin_statement_model/io/writers/dict.py fin_statement_model/io/formats/dict/writer.py
```

### 3.5 API Formats
```bash
mv fin_statement_model/io/readers/fmp.py fin_statement_model/io/formats/api/fmp.py
```

### 3.6 Markdown Format
```bash
mv fin_statement_model/io/writers/markdown_writer.py fin_statement_model/io/formats/markdown/writer.py
```

## Phase 4: Move Specialized Components

```bash
# Move specialized IO operations
mv fin_statement_model/io/adjustments_excel.py fin_statement_model/io/specialized/adjustments.py
mv fin_statement_model/io/readers/graph_definition.py fin_statement_model/io/specialized/graph.py
mv fin_statement_model/io/writers/graph_definition.py fin_statement_model/io/specialized/graph.py  # Merge with reader
mv fin_statement_model/io/readers/cell_reader.py fin_statement_model/io/specialized/cells.py
mv fin_statement_model/io/writers/statement_writer.py fin_statement_model/io/specialized/statements.py
mv fin_statement_model/io/readers/statement_config_reader.py fin_statement_model/io/specialized/statements.py  # Merge
```

## Phase 5: Move Configuration

```bash
# Keep config where it is, just move mappings
mv fin_statement_model/io/readers/config/fmp_default_mappings.yaml fin_statement_model/io/config/mappings/
```

## Phase 6: Move Documentation

```bash
mv fin_statement_model/io/README*.md fin_statement_model/io/docs/
mv fin_statement_model/io/MIGRATION_GUIDE.md fin_statement_model/io/docs/
mv fin_statement_model/io/PHASE_*.md fin_statement_model/io/docs/archive/
```

## Phase 7: Update Imports

### 7.1 Update format implementations
All format readers/writers need to update their imports:
```python
# Old
from fin_statement_model.io.base import DataReader
from fin_statement_model.io.registry import register_reader

# New
from fin_statement_model.io.core.base import DataReader
from fin_statement_model.io.core.registry import register_reader
```

### 7.2 Update __init__.py files

#### formats/__init__.py
```python
# Import all formats to trigger registration
from . import excel, csv, dataframe, dict, api, markdown
```

#### formats/excel/__init__.py
```python
from .reader import ExcelReader
from .writer import ExcelWriter

__all__ = ['ExcelReader', 'ExcelWriter']
```

### 7.3 Update main __init__.py
```python
# Trigger all registrations
from . import formats, specialized

# Import core components
from .core.registry import get_reader, get_writer, list_readers, list_writers
from .exceptions import IOError, ReadError, WriteError, FormatNotSupportedError
from .validation import UnifiedNodeValidator

# Keep facade functions
from .core.facade import read_data, write_data  # Move these to core/facade.py
```

## Phase 8: Clean Up

1. Remove old directories:
   ```bash
   rm -rf fin_statement_model/io/readers/
   rm -rf fin_statement_model/io/writers/
   ```

2. Delete obsolete files:
   ```bash
   rm fin_statement_model/io/base_implementations.py  # After extracting mixins
   rm fin_statement_model/io/utils.py  # After extracting components
   rm fin_statement_model/io/registry.py  # After merging into core/registry.py
   ```

## Phase 9: Update Tests

All test imports need to be updated to reflect the new structure:
```python
# Old
from fin_statement_model.io.readers.excel import ExcelReader

# New
from fin_statement_model.io.formats.excel import ExcelReader
```

## Benefits After Restructuring

1. **Clearer mental model**: Developers can easily find what they're looking for
2. **Better encapsulation**: Each format is self-contained
3. **Easier testing**: Tests can mirror the new structure
4. **Simpler imports**: Public API remains clean while internals are organized
5. **Room to grow**: New formats and features have clear homes

## Backwards Compatibility

The public API (`read_data`, `write_data`, etc.) remains unchanged, so user code doesn't break. Only internal imports need updating. 