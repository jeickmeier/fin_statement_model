# Simple Banking Graph Analysis Example

This example demonstrates the core graph functionality of the financial statement model library with a focus on banking analysis. It provides a simplified, educational introduction to graph-based financial modeling.

## What This Example Shows

The example walks through 6 clear steps:

1. **Node Name Validation** - Demonstrates how to validate and standardize banking data node names
2. **Graph Building** - Shows how to create a graph with data nodes and calculation nodes
3. **Automatic Calculations** - Illustrates how the graph automatically calculates dependent values
4. **Structure Analysis** - Analyzes the graph structure and node relationships
5. **Banking Metrics** - Calculates standard banking metrics and compares approaches
6. **Graph Traversal** - Demonstrates dependency analysis and calculation flow

## Key Features Demonstrated

- **Node Name Validation**: Standardizes raw data names (e.g., "npl" → "non_performing_loans")
- **Graph Structure**: Creates a network of interconnected financial data and calculations
- **Automatic Propagation**: Changes to base data automatically update all dependent calculations
- **Banking Metrics**: Calculates standard banking ratios with interpretations
- **Dependency Tracking**: Shows how calculations depend on other nodes
- **Error Handling**: Demonstrates robust error handling for graph operations

## Sample Output

The example creates a banking graph with:
- **8 data nodes**: Core banking data (loans, deposits, capital, etc.)
- **5 calculation nodes**: Derived metrics (net loans, ratios, etc.)
- **3 time periods**: 2021, 2022, 2023
- **Banking metrics**: NPL ratio, Tier 1 capital ratio, loan-to-deposit ratio

### Example Calculations (2023):
- Net Loans: $51,220,000,000
- Loan-to-Deposit Ratio: 85.37%
- NPL Ratio: 1.00% (Good)
- Tier 1 Capital Ratio: 13.12% (Excellent)

## How to Run

```bash
cd /path/to/fin_statement_model
python examples/simple_banking_graph_example.py
```

## Educational Value

This example is designed to be:
- **Easy to Follow**: Clear step-by-step progression
- **Well Documented**: Extensive comments and explanations
- **Practical**: Uses realistic banking data and metrics
- **Comprehensive**: Covers all major graph functionality
- **Error-Safe**: Includes proper error handling

## Comparison with Complex Example

Unlike the comprehensive banking analysis example (`banking_analysis_example.py`), this simplified version:
- Focuses on graph concepts rather than exhaustive banking analysis
- Uses fewer nodes and simpler calculations
- Provides clearer educational progression
- Emphasizes core functionality over comprehensive coverage

## Next Steps

After understanding this example, you can:
1. Explore the comprehensive banking analysis example
2. Create your own industry-specific graph models
3. Add more complex calculation nodes
4. Integrate with real data sources
5. Build forecasting models on top of the graph structure

## Key Takeaways

1. **Node name validation ensures data consistency**
2. **Graph automatically calculates dependent values**
3. **Relationships between nodes are clearly defined**
4. **Banking metrics provide business insights**
5. **Graph traversal reveals calculation dependencies**
6. **Structure validation prevents calculation errors** 