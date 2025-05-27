# Realistic Banking Analysis Example

This example demonstrates a practical, production-ready approach to banking analysis using the financial statement model library. It's designed to be more concise and realistic compared to the step-by-step educational example.

## Key Features

### 1. Single-Step Data Loading and Validation
- Loads banking data from a realistic source (simulated DataFrame)
- Automatically validates and standardizes node names during loading
- Creates a complete graph in one streamlined operation
- Handles common banking field name variations automatically

### 2. Comprehensive Performance Analysis
- Analyzes **19 key banking metrics** across four categories:
  - **Asset Quality**: NPL ratio, allowance coverage, charge-off rates, provision coverage
  - **Capital Adequacy**: CET1, Tier 1, Total Capital, and Leverage ratios
  - **Liquidity**: LCR, loan-to-deposit ratios, liquid assets ratio
  - **Profitability**: ROA, ROE, NIM, efficiency ratio, fee income ratio

### 3. Regulatory Compliance Monitoring
- Tracks compliance with key regulatory requirements
- Compares current ratios to regulatory minimums
- Provides color-coded status indicators
- Includes buffer analysis above minimum requirements

### 4. Professional Reporting
- Visual indicators (🟢🟡🔴) for metric performance ratings
- Trend analysis with directional arrows (📈📉➡️) across 6 key metrics
- Executive summary with overall assessment and specific observations
- Detailed strengths and areas for attention identification
- Error handling with graceful degradation

### 5. Real-World Data Patterns
- Uses common banking field name variations (e.g., "npl" → "non_performing_loans")
- Handles non-standardized input data automatically
- Demonstrates typical banking data structure and relationships
- Includes 3 years of historical data for trend analysis

## Usage

```python
python examples/realistic_banking_analysis.py
```

## Example Output

```
REALISTIC BANKING ANALYSIS
Demonstrating practical banking data analysis workflow

============================================================
LOADING AND VALIDATING BANKING DATA
============================================================
Loading banking data from source...
Loaded 21 data points across 3 periods

Validating and standardizing node names...
Building graph with 3 periods...

Graph created successfully:
  Total nodes: 21
  Periods: ['2021', '2022', '2023']
  Standardized names: 3
  Alternate names converted: 13
  Unrecognized names: 5

============================================================
BANKING PERFORMANCE ANALYSIS - 2023
============================================================

=== Asset Quality ===
🟢 Non-Performing Loan Ratio: 1.00% (GOOD)
🟢 Allowance to Loans Ratio: 1.50% (GOOD)
🟢 Charge-Off Rate: 0.52% (GOOD)
🟢 Provision Coverage Ratio: 150.00% (EXCELLENT)

=== Capital Adequacy ===
🟢 Common Equity Tier 1 Ratio: 12.50% (EXCELLENT)
🟢 Tier 1 Capital Ratio: 13.12% (EXCELLENT)
🟢 Tier 1 Leverage Ratio: 8.40% (EXCELLENT)

=== Liquidity ===
🟢 Liquidity Coverage Ratio: 127.27% (GOOD)
🟢 Loan to Deposit Ratio: 86.67% (GOOD)
🟢 Deposits to Loans Ratio: 115.38% (EXCELLENT)
🟢 Liquid Assets Ratio: 22.67% (EXCELLENT)

=== Profitability ===
🟢 Net Interest Margin: 3.94% (GOOD)
🟢 Efficiency Ratio: 57.14% (GOOD)
🟢 Return on Assets (Banking): 1.47 (EXCELLENT)
🟢 Return on Equity (Banking): 15.17 (EXCELLENT)
🟢 Fee Income Ratio: 25.71% (GOOD)

============================================================
TREND ANALYSIS
============================================================
Metric                              2021       2022       2023       Trend     
---------------------------------------------------------------------------
Non-Performing Loan Ratio           1.00%      1.00%      1.00%      ➡️ FLAT   
Tier 1 Capital Ratio                13.10%     13.11%     13.12%     📈 UP      
Return on Assets (Banking)          1.31%      1.36%      1.47%      📈 UP      
Efficiency Ratio                    62.07%     60.32%     57.14%     📉 DOWN    
Net Interest Margin                 3.62%      3.71%      3.94%      📈 UP      
Liquidity Coverage Ratio            120.00%    123.81%    127.27%    📈 UP      

============================================================
REGULATORY COMPLIANCE SUMMARY
============================================================
Metric                         Current      Minimum      Status         
----------------------------------------------------------------------
Common Equity Tier 1 Ratio     12.50%       7.0%       🟢 Strong       
Tier 1 Capital Ratio           13.12%       8.5%       🟢 Strong       
Liquidity Coverage Ratio       127.27%       100.0%       🟢 Strong       
Tier 1 Leverage Ratio          8.40%       4.0%       🟢 Strong       

============================================================
EXECUTIVE SUMMARY
============================================================
Bank Performance Summary for 2023:
  • Asset Quality: NPL Ratio of 1.00%
  • Capital Strength: Tier 1 Ratio of 13.12%
  • Profitability: ROA of 1.47%, NIM of 3.94%
  • Efficiency: Cost-to-Income of 57.14%
  • Liquidity: LCR of 127.27%

Overall Assessment:
  🟢 Strong performance across key metrics

Key Observations:
  Strengths: Excellent asset quality, Strong capital position, Strong profitability, 
            Excellent operational efficiency, Strong liquidity position
```

## Comparison with Educational Example

| Aspect | Educational Example | Realistic Example |
|--------|-------------------|------------------|
| **Structure** | 6 separate steps | Single workflow |
| **Data Loading** | Manual node-by-node | Batch DataFrame processing |
| **Validation** | Separate validation step | Integrated during loading |
| **Metrics Coverage** | Basic metrics | 19 comprehensive metrics |
| **Regulatory Focus** | Limited | Dedicated compliance section |
| **Output** | Detailed explanations | Professional reporting |
| **Use Case** | Learning the library | Production analysis |
| **Code Length** | ~500 lines | ~450 lines |

## Adapting for Real Data Sources

To use this example with real data sources, modify the `load_banking_data()` function:

### Excel File
```python
def load_banking_data() -> pd.DataFrame:
    return pd.read_excel("banking_data.xlsx", sheet_name="metrics")
```

### CSV File
```python
def load_banking_data() -> pd.DataFrame:
    return pd.read_csv("banking_data.csv")
```

### Database
```python
def load_banking_data() -> pd.DataFrame:
    import sqlalchemy as sa
    engine = sa.create_engine("postgresql://user:pass@host/db")
    return pd.read_sql("SELECT * FROM banking_metrics", engine)
```

### API
```python
def load_banking_data() -> pd.DataFrame:
    import requests
    response = requests.get("https://api.bank.com/metrics")
    return pd.DataFrame(response.json())
```

## Expected Data Format

The input data should have this structure:

| metric_name | 2021 | 2022 | 2023 |
|-------------|------|------|------|
| gross_loans | 45000000000 | 48000000000 | 52000000000 |
| npl | 450000000 | 480000000 | 520000000 |
| deposits | 52000000000 | 56000000000 | 60000000000 |
| ... | ... | ... | ... |

The library will automatically:
- Validate and standardize metric names using the node registry
- Handle common banking terminology variations (e.g., "npl" → "non_performing_loans")
- Create appropriate graph nodes with proper relationships
- Calculate all available banking metrics with error handling

## Banking Metrics Included

### Asset Quality (4 metrics)
- Non-Performing Loan Ratio
- Allowance to Loans Ratio  
- Charge-Off Rate
- Provision Coverage Ratio

### Capital Adequacy (4 metrics)
- Common Equity Tier 1 Ratio
- Tier 1 Capital Ratio
- Total Capital Ratio
- Tier 1 Leverage Ratio

### Liquidity (4 metrics)
- Liquidity Coverage Ratio
- Loan to Deposit Ratio
- Deposits to Loans Ratio
- Liquid Assets Ratio

### Profitability (5 metrics)
- Net Interest Margin
- Efficiency Ratio
- Return on Assets (Banking)
- Return on Equity (Banking)
- Fee Income Ratio

### Regulatory Compliance (4 key ratios)
- CET1 Ratio vs. 7.0% minimum
- Tier 1 Ratio vs. 8.5% minimum
- LCR vs. 100% minimum
- Leverage Ratio vs. 4.0% minimum

## Benefits

1. **Efficiency**: Single function call loads and validates all data
2. **Robustness**: Handles non-standard field names automatically
3. **Comprehensive**: Covers all major banking analysis areas with 19+ metrics
4. **Professional**: Production-ready output with visual indicators
5. **Regulatory Focus**: Dedicated compliance monitoring and reporting
6. **Extensible**: Easy to adapt for different data sources and additional metrics
7. **Maintainable**: Clean, focused code structure with clear separation of concerns
8. **Actionable**: Provides specific strengths and areas for attention

This example represents how the library would typically be used in a real banking analysis workflow, providing both efficiency and professional-quality results suitable for regulatory reporting, management dashboards, and stakeholder presentations. 