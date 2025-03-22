# Financial Statement Model

A powerful library for building and analyzing financial statement data models, creating calculation graphs, and generating reports.

## Description

The Financial Statement Model is a Python library that provides tools for working with financial data. It allows you to:

- Build structured financial statement models with relationships between items
- Create calculation graphs for financial metrics and ratios
- Import data from various sources (APIs, Excel, CSV)
- Perform forecasting with different methods
- Transform and analyze financial data with specialized tools
- Generate reports and export data in various formats

The library uses a node-based graph structure to represent financial statement items and calculations, making it easy to model complex financial relationships.

## Architecture

The Financial Statement Model has been refactored to follow the Single Responsibility Principle, with specialized components for different aspects of functionality:

### Core Components:
- **Graph**: The underlying data structure representing nodes and relationships
- **DataManager**: Handles adding and managing financial statement item data
- **CalculationEngine**: Manages calculations and formula execution
- **NodeFactory**: Creates different types of nodes (financial items, calculations, forecasts, metrics)

### I/O Components:
- **ImportManager**: Manages importing data from external sources
- **ExportManager**: Handles exporting data to various formats

### Statement Components:
- **StatementManager**: Manages financial statement structures and formats
- **StatementStructure**: Represents the hierarchical structure of financial statements
- **StatementConfig**: Loads and validates statement configurations from files
- **StatementFormatter**: Formats financial statement data in different outputs (DataFrame, HTML)

### Transformation Components:
- **TransformationService**: High-level service for applying data transformations
- **DataTransformer**: Base class for all data transformers
- **CompositeTransformer**: Combines multiple transformers into pipelines
- **TransformerFactory**: Creates and manages transformer instances
- **Specialized Transformers**: Financial-specific transformers for normalization, time series analysis, etc.

### Calculation Components:
- **CalculationStrategy**: Abstract base class for all calculation strategies
- **Concrete Strategies**: Various calculation algorithms (addition, subtraction, weighted average, etc.)
- **StrategyCalculationNode**: Node that uses strategies for calculations
- **CalculationStrategyRegistry**: Central registry for managing calculation strategies

### Adapter Pattern Implementation:
- **DataSourceAdapter**: Abstract base class for all data source adapters
- **FileDataSourceAdapter**: Base class for file-based adapters
- **APIDataSourceAdapter**: Base class for API-based adapters
- **AdapterFactory**: Creates and manages adapter instances
- **AdapterRegistry**: Maintains a global registry of adapter instances for efficient reuse

### Concrete Adapters:
- **FMPAdapter**: Adapter for the Financial Modeling Prep API
- **ExcelAdapter**: Adapter for importing from Excel files
- **CSVAdapter**: Adapter for importing from CSV files
- **DataFrameAdapter**: Adapter for importing from pandas DataFrames

## Example Usage

```python
from fin_statement_model.financial_statement import FinancialStatementGraph

# Create a financial statement graph
fsg = FinancialStatementGraph(periods=['FY2020', 'FY2021', 'FY2022'])

# Add financial statement items
fsg.add_financial_statement_item("revenue", {'FY2020': 100000, 'FY2021': 120000, 'FY2022': 150000})
fsg.add_financial_statement_item("cost_of_goods_sold", {'FY2020': 60000, 'FY2021': 70000, 'FY2022': 85000})

# Add calculations with different strategies
fsg.add_calculation("gross_profit", ["revenue", "cost_of_goods_sold"], "subtraction")

# Use weighted average for a key metric
fsg.add_calculation("weighted_revenue", ["revenue"], "weighted_average", 
                   weights=[0.2, 0.3, 0.5])  # Weights for FY2020, FY2021, FY2022

# Create a forecast
fsg.create_forecast(['FY2023', 'FY2024'], {'revenue': 0.15, 'cost_of_goods_sold': 0.12}, 'simple')

# Import data from an API
fsg.import_from_api('FMP', 'AAPL', 'FY', 5, 'income_statement', api_key='your_api_key')

# Load a statement configuration
income_statement = fsg.load_statement_config('config/income_statement.json')
balance_sheet = fsg.load_statement_config('config/balance_sheet.json')

# Generate formatted statements from configurations
income_df = fsg.format_statement('income_statement')
balance_df = fsg.format_statement('balance_sheet')

# Export formatted statements to Excel
fsg.export_statement_to_excel('income_statement', 'income_statement.xlsx')

# Transform data
normalized_df = fsg.normalize_data('percent_of', 'revenue')
growth_df = fsg.analyze_time_series('yoy')
formatted_df = fsg.format_statement('income_statement')

# Apply a transformation pipeline
config = [
    {'name': 'period_conversion', 'conversion_type': 'quarterly_to_annual'},
    {'name': 'normalization', 'normalization_type': 'percent_of', 'reference': 'revenue'}
]
transformed_df = fsg.apply_transformations(config)

# Change calculation strategy at runtime
fsg._calculation_engine.change_calculation_strategy(
    "gross_profit", "weighted_average", weights=[0.7, 0.3]
)

# Export to Excel
fsg.export_to_excel('financial_model.xlsx')
```

## Design Patterns

The Financial Statement Model applies several design patterns:

1. **Single Responsibility Principle**: Each component has a specific, focused responsibility
2. **Facade Pattern**: `FinancialStatementGraph` provides a simple interface to the complex system
3. **Strategy Pattern**: 
   - Different calculation algorithms are encapsulated in strategy classes
   - Strategies can be selected at runtime and changed dynamically
   - New strategies can be added without modifying existing code
   - Strategy-based calculations are decoupled from the node infrastructure
4. **Factory Pattern**: 
   - `AdapterFactory` creates the appropriate adapter instances
   - `NodeFactory` centralizes the creation of different node types
   - `TransformerFactory` manages transformation strategies
5. **Adapter Pattern**: Standardized interface for different data sources through the adapter hierarchy
6. **Registry Pattern**: 
   - `AdapterRegistry` provides a cache for adapter instances
   - `CalculationStrategyRegistry` manages calculation strategies
7. **Composite Pattern**: `CompositeTransformer` allows combining transformers into pipelines
8. **Configuration-Driven Development**:
   - Financial statement structures are defined through configuration
   - Allows for customization without code changes
   - Supports different accounting standards and reporting formats

## Error Handling

The Financial Statement Model includes comprehensive error handling through a custom exceptions hierarchy. These exceptions provide more precise error reporting and better error messages throughout the codebase.

### Custom Exceptions

The model implements a hierarchy of custom exceptions:

- `FinancialModelError`: Base exception for all errors in the model
  - `ConfigurationError`: For errors in configuration files or objects
  - `CalculationError`: For errors during calculation operations
  - `NodeError`: For errors related to graph nodes
  - `GraphError`: For errors in the graph structure or operations
  - `DataValidationError`: For data validation errors
  - `ImportError`: For errors during data import operations
  - `ExportError`: For errors during data export operations
  - `CircularDependencyError`: For circular dependency detection in calculations
  - `PeriodError`: For errors related to periods
  - `StatementError`: For errors related to financial statements
  - `StrategyError`: For errors related to calculation strategies
  - `TransformationError`: For errors during data transformation

### Benefits

- **More descriptive errors**: Each exception includes detailed information about what went wrong
- **Context-rich messages**: Errors include relevant context such as node IDs, periods, etc.
- **Better error handling**: Code can catch specific exception types to handle errors appropriately
- **Improved debugging**: Detailed error messages make it easier to diagnose and fix problems
- **Original exception preservation**: Original exceptions are preserved as the cause of the custom exception

### Example Usage

```python
try:
    # Try to calculate a value
    result = graph.calculate('net_income', '2023-Q1')
except CircularDependencyError as e:
    # Handle circular dependency
    print(f"Circular dependency detected: {e.cycle}")
except NodeError as e:
    # Handle node errors
    print(f"Node error for {e.node_id}: {e.message}")
except CalculationError as e:
    # Handle calculation errors
    print(f"Calculation error: {e.message}")
    if e.period:
        print(f"Period: {e.period}")
    if e.details:
        print(f"Details: {e.details}")
```

### Error Handling Locations

The model implements consistent error handling across all components:

- Configuration loading and validation
- Graph operations (adding/removing nodes, setting values)
- Calculation execution
- Statement structure validation
- Data import/export operations
- Strategy pattern implementation

## Project Structure

```
fin_statement_model/
├── core/
│   ├── data_manager.py
│   ├── calculation_engine.py
│   ├── node_factory.py
│   ├── graph.py
│   ├── nodes.py
│   ├── financial_statement.py
├── importers/
│   ├── adapter_base.py
│   ├── adapter_factory.py  
│   ├── adapter_registry.py
│   ├── fmp.py
│   ├── excel_adapter.py
├── transformations/
│   ├── base_transformer.py
│   ├── transformer_factory.py
│   ├── financial_transformers.py
│   ├── transformation_service.py
├── calculations/
│   ├── calculation_strategy.py
│   ├── strategy_registry.py
├── statements/
│   ├── statement_structure.py
│   ├── statement_config.py
│   ├── statement_formatter.py
│   ├── statement_manager.py
├── config/
│   ├── examples/
│   │   ├── income_statement.json
│   │   ├── balance_sheet.json
│   │   ├── cash_flow.json
├── io/
│   ├── import_manager.py
│   ├── export_manager.py
```

## Benefits of Config-Driven Statement Structure

The config-driven statement structure provides several advantages:

1. **Customizable Structure**: Financial statement structures can be defined and customized through configuration files
2. **Reduced Code Changes**: New statement types or changes to existing statements can be made without modifying code
3. **Support for Multiple Formats**: Different accounting standards (GAAP, IFRS) and reporting formats can be supported through configuration
4. **Separation of Structure and Logic**: Statement structure is separated from calculation logic
5. **Hierarchical Organization**: Sections and line items can be organized in a hierarchical structure
6. **Automated Calculations**: Calculated items and subtotals are automatically generated based on configuration
7. **Consistent Formatting**: Statement formatting is consistent across different statement types
8. **Enhanced Maintainability**: Changes to statement structures are isolated to configuration files

## Benefits of the Adapter Pattern Implementation

The Adapter Pattern infrastructure implementation provides several benefits:

1. **Consistent Interface**: All data sources implement the same interface, making them interchangeable
2. **Simplified Integration**: New data sources can be easily added by implementing the appropriate adapter interface
3. **Separation of Concerns**: Data fetching, connection handling, and data mapping are separated from the core functionality
4. **Enhanced Testability**: Adapters can be mocked for testing purposes
5. **Better Error Handling**: Each adapter can handle source-specific errors and provide standardized error messages
6. **Efficient Resource Management**: The registry pattern allows reuse of adapter instances, reducing overhead
7. **Centralized Configuration**: Adapter configurations are managed centrally by the factory

## Benefits of the Factory Pattern for Node Creation

The Factory Pattern for node creation provides several advantages:

1. **Centralized Creation Logic**: All node creation is standardized and managed in one place
2. **Improved Extensibility**: New node types can be easily added by extending the factory
3. **Consistent Initialization**: Node creation includes validation and proper initialization
4. **Reduced Coupling**: Client code depends on the factory interface, not specific node implementations
5. **Enhanced Testability**: Factory methods can be mocked for unit testing
6. **Simplified Client Code**: Complex creation logic is encapsulated, making client code cleaner
7. **Type Safety**: Factory methods return properly typed objects with appropriate validations

## Benefits of Data Processing and Transformation Separation

Separating data processing from data transformation provides several benefits:

1. **Clear Separation of Concerns**: Processing focuses on handling raw data operations, while transformation focuses on converting data between formats and applying business rules
2. **Improved Maintainability**: Each component has a clear purpose, making the code easier to understand and maintain
3. **Enhanced Flexibility**: Transformations can be composed and reused in different contexts
4. **Testability**: Transformers can be tested independently of data processing logic
5. **Extensibility**: New transformation types can be added without modifying existing code
6. **Configurable Pipelines**: Transformation pipelines can be built from reusable components
7. **Domain-Specific Transformations**: Specialized transformers can implement financial-specific logic

## Benefits of the Strategy Pattern for Calculations

Implementing the Strategy Pattern for calculations provides several advantages:

1. **Algorithm Encapsulation**: Each calculation algorithm is encapsulated in its own strategy class
2. **Runtime Flexibility**: Calculation strategies can be selected and changed at runtime
3. **Improved Extensibility**: New calculation strategies can be added without modifying existing code
4. **Reduced Complexity**: Each strategy has a single, focused responsibility
5. **Enhanced Configurability**: Strategies can be configured with custom parameters
6. **Simplified Testing**: Strategies can be tested independently of the node structure
7. **Better Organization**: Related algorithms are grouped together rather than scattered throughout the codebase
8. **Centralized Registry**: The strategy registry provides a central location for managing and accessing strategies
