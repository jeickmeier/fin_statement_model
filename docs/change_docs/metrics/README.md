# Financial Metrics Implementation Plan

This directory contains the planning documents for implementing comprehensive credit and equity analysis metrics in the `fin_statement_model` package.

## Files in this Directory

### 📋 [core_metrics_todo.md](./core_metrics_todo.md)
The main TODO list containing:
- 74 standardized base nodes (balance sheet, income statement, cash flow)
- 96 financial metrics organized by category
- Formulas for each metric using standardized node names
- Implementation notes and priority phases

### 📊 [metrics_summary.md](./metrics_summary.md)
High-level summary including:
- Metric counts by category
- Key node dependencies and usage frequency
- Implementation complexity breakdown
- Cross-metric relationships and validation rules

### 📏 [node_naming_standards.md](./node_naming_standards.md)
Comprehensive naming conventions for:
- Balance sheet, income statement, and cash flow items
- Calculated and derived metrics
- Industry-specific considerations
- Examples of good vs. bad naming practices

## Standard Node Registry System

The library now includes a **Standard Node Registry** that defines and enforces common node names like `cash_and_equivalents`. This system ensures consistency across all financial models and enables metrics to work reliably.

### How It Works

1. **Standard Node Definitions**: Stored in `fin_statement_model/core/nodes/standard_nodes.yaml`
   - Each node has a standard name (e.g., `revenue`)
   - Alternate names are mapped to standard names (e.g., `sales` → `revenue`)
   - Includes metadata like category, description, and sign convention

2. **Registry API**: Access via `fin_statement_model.core.nodes.standard_node_registry`
   ```python
   from fin_statement_model.core.nodes import standard_node_registry
   
   # Check if a name is standard
   is_standard = standard_node_registry.is_standard_name("revenue")
   
   # Get the standard name for an alternate
   standard_name = standard_node_registry.get_standard_name("sales")  # Returns "revenue"
   
   # Validate a node name
   is_valid, message = standard_node_registry.validate_node_name("total_revenue")
   ```

3. **Node Name Validation**: Use the validator when importing data
   ```python
   from fin_statement_model.io.validation import UnifiedNodeValidator
   
   # Create a validator
   validator = UnifiedNodeValidator(
       strict_mode=False,        # Allow non-standard names with warnings
       auto_standardize=True,    # Convert alternates to standard names
       warn_on_non_standard=True # Log warnings for unrecognized names
   )
   
   # Validate and standardize a name
   result = validator.validate("sales")
   # result.standardized_name = "revenue"
   # result.is_valid = True
   # result.message = "Standardized 'sales' to 'revenue'"
   ```

4. **Sign Conventions**: The registry tracks whether values are typically positive or negative
   ```python
   sign = standard_node_registry.get_sign_convention("cost_of_goods_sold")
   # Returns: "negative"
   ```

### Benefits

- **Consistency**: All models use the same node names
- **Metrics Compatibility**: Metrics can rely on standard names existing
- **Alternate Name Support**: Common variations are automatically mapped
- **Validation**: Catch typos and inconsistencies during data import
- **Documentation**: Each standard node has a clear description

### Example Usage in Readers

```python
# In a CSV reader
from fin_statement_model.io.validation import UnifiedNodeValidator

validator = UnifiedNodeValidator(auto_standardize=True)

for row in csv_data:
    original_name = row['item_name']
    result = validator.validate(original_name)
    
    # Create node with standardized name
    node = FinancialStatementItemNode(name=result.standardized_name, values=values)
    graph.add_node(node)

# Get validation summary
summary = validator.get_validation_summary()
print(f"Standardized {summary['alternate_names']} alternate names")
print(f"Found {summary['unrecognized_names']} unrecognized names")
```

## Implementation Strategy

### Phase 1: Core Foundation (20 metrics)
Focus on the most essential metrics for basic financial analysis:
- Liquidity: Current Ratio, Quick Ratio
- Leverage: Debt-to-Equity, Debt-to-Assets
- Coverage: Interest Coverage, DSCR
- Profitability: Gross/Operating/Net Margins, ROE, ROA
- Valuation: P/E, EV/EBITDA

### Phase 2: Credit Analysis Focus (25 metrics)
Add credit-specific metrics critical for risk assessment:
- Net debt calculations
- Free cash flow metrics
- Altman Z-Score variants
- Advanced coverage ratios
- Early warning indicators

### Phase 3: Comprehensive Analysis (30 metrics)
Round out the metric library with:
- Efficiency metrics (turnover ratios)
- DuPont analysis components
- Per share calculations
- Growth metrics
- Cash flow quality indicators

### Phase 4: Advanced Features (21 metrics)
Sophisticated analysis tools:
- Industry-specific adjustments
- Complex credit scoring models
- Peer comparison frameworks
- Scenario testing capabilities

## Key Design Principles

1. **Standardization**: All metrics use consistent node naming from `node_naming_standards.md`
2. **Modularity**: Each metric is self-contained with clear inputs and outputs
3. **Error Handling**: Graceful handling of missing data and division by zero
4. **Documentation**: Every metric includes description and use case
5. **Testing**: Each metric should have test cases with known outputs

## Usage Example

Once implemented, analysts will be able to:

```python
from fin_statement_model import Graph
from fin_statement_model.metrics import calculate_credit_score

# Load financial data
graph = Graph()
graph.load_from_excel("company_financials.xlsx")

# Calculate key credit metrics
credit_metrics = graph.calculate_metrics([
    "current_ratio",
    "debt_to_equity",
    "interest_coverage",
    "altman_z_score",
    "free_cash_flow_to_debt"
])

# Generate credit assessment
credit_score = calculate_credit_score(graph)
```

## Next Steps

1. **Review and refine** the metric definitions in `core_metrics_todo.md`
2. **Create YAML definitions** for Phase 1 metrics in `fin_statement_model/core/metrics/builtin/`
3. **Implement base nodes** that don't already exist
4. **Add calculation strategies** for complex metrics
5. **Build testing framework** with real financial data
6. **Document each metric** with examples and interpretation guidelines

## Contributing

When adding new metrics:
1. Follow the naming standards in `node_naming_standards.md`
2. Add the metric to the appropriate category in `core_metrics_todo.md`
3. Update counts in `metrics_summary.md`
4. Include formula, inputs, and description
5. Consider edge cases and error handling
6. Add tests with realistic data

## Questions?

For questions about:
- Metric definitions → See formulas in `core_metrics_todo.md`
- Node naming → Refer to `node_naming_standards.md`
- Implementation priority → Check phases in `metrics_summary.md`
- Technical details → Review the fin_statement_model documentation 