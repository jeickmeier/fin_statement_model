# Data Fetcher Extraction Summary

## Overview
We successfully extracted the data fetching logic from the formatter into a dedicated `DataFetcher` class, improving separation of concerns, testability, and reusability.

## What Was Done

### 1. Created DataFetcher Class (`data_fetcher.py`)

#### Core Components:
- **DataFetcher**: Main class that encapsulates data fetching logic
- **NodeData**: Dataclass representing data for a single node across periods
- **FetchResult**: Result object containing fetched data and any errors

#### Key Features:
- Centralized ID resolution using IDResolver
- Comprehensive error handling with ErrorCollector
- Support for adjustment filters
- Separate method for checking adjustment status
- Rich error context for debugging

### 2. Refactored Formatter

#### Before:
- 100+ line `_fetch_data_from_graph` function embedded in formatter module
- Mixed concerns: data fetching and formatting in same file
- Difficult to test data fetching independently
- Error handling mixed with formatting logic

#### After:
- Clean separation: DataFetcher handles all data retrieval
- Formatter focuses solely on presentation logic
- Easy to mock DataFetcher for testing
- Consistent error handling using Result types

## Benefits Achieved

### 1. **Single Responsibility**
- DataFetcher: Retrieves data from graph
- Formatter: Formats data for display
- Clear separation of concerns

### 2. **Improved Testability**
```python
# Easy to test data fetching independently
def test_fetch_with_missing_nodes():
    fetcher = DataFetcher(statement, graph)
    result = fetcher.fetch_all_data()
    assert len(result.missing_nodes) == 2
    assert result.errors.has_warnings()
```

### 3. **Better Error Handling**
```python
# Rich error information
fetch_result = data_fetcher.fetch_all_data()
if fetch_result.errors.has_errors():
    fetch_result.errors.log_all()
    # Handle errors appropriately
```

### 4. **Reusability**
- DataFetcher can be used by other components
- Not tied to formatting concerns
- Can fetch data for analysis, export, etc.

### 5. **Performance Optimization**
- Centralized node resolution avoids duplicate lookups
- Batch adjustment checking reduces graph queries
- Clear separation enables future caching strategies

## Code Structure

### DataFetcher Methods:
```python
class DataFetcher:
    def __init__(self, statement: StatementStructure, graph: Graph)
    
    def fetch_all_data(
        adjustment_filter: Optional[AdjustmentFilterInput] = None,
        include_missing: bool = False,
    ) -> FetchResult
    
    def check_adjustments(
        node_ids: list[str],
        periods: list[str],
        adjustment_filter: Optional[AdjustmentFilterInput] = None,
    ) -> dict[str, dict[str, bool]]
```

### Integration Example:
```python
# In formatter
data_fetcher = DataFetcher(self.statement, graph)
fetch_result = data_fetcher.fetch_all_data(
    adjustment_filter=adjustment_filter,
    include_missing=include_empty_items,
)

# Log any issues
if fetch_result.errors.has_warnings():
    fetch_result.errors.log_all()

# Use the data
data = fetch_result.data
```

## Error Handling

The DataFetcher provides comprehensive error handling:

1. **Missing Periods**: Error if graph has no periods defined
2. **Unresolvable Items**: Warning for items that can't be resolved to nodes
3. **Missing Nodes**: Warning for nodes not found in graph
4. **Calculation Errors**: Warning for failed calculations
5. **Filter Errors**: Warning for invalid adjustment filters
6. **Unexpected Errors**: Error level for unexpected exceptions

All errors include:
- Error code for programmatic handling
- Human-readable message
- Context information
- Source identification
- Appropriate severity level

## Testing Improvements

With the extraction complete, we can now:
1. Test data fetching logic independently
2. Mock DataFetcher in formatter tests
3. Test error scenarios without complex setup
4. Verify adjustment checking separately
5. Test performance optimizations in isolation

## Next Steps

1. Add comprehensive unit tests for DataFetcher
2. Consider caching strategies for repeated fetches
3. Add metrics/logging for fetch performance
4. Consider async fetching for large statements
5. Add support for partial data fetching (specific items/periods)

This refactoring demonstrates the value of extracting focused components from complex classes, making the codebase more maintainable and testable. 