# Banking Analysis with Node Name Validation

## Overview

The enhanced banking analysis example demonstrates how to integrate node name validators and context-aware validation into financial analysis workflows. This implementation showcases best practices for data quality assurance and standardization in banking financial analysis.

## Key Features

### 1. Node Name Validation
- **Automatic Standardization**: Converts alternate node names to standard forms
- **Validation Feedback**: Provides clear messages about validation results
- **Banking-Specific Names**: Handles common banking abbreviations and alternate names

### 2. Context-Aware Validation
- **Intelligent Recognition**: Understands relationships between nodes
- **Sub-node Detection**: Recognizes valid sub-nodes and segments
- **Formula Validation**: Validates calculation node dependencies

### 3. Data Quality Assurance
- **Completeness Checking**: Validates presence of required banking nodes
- **Quality Scoring**: Provides data completeness scores
- **Missing Data Detection**: Identifies gaps in required and recommended data

## Implementation Components

### Core Validation Functions

#### `validate_node_names_example()`
Demonstrates basic node name validation with common banking terms:
- Standard names (e.g., `total_loans`)
- Alternate names (e.g., `npl` → `non_performing_loans`)
- Abbreviations (e.g., `nii` → `net_interest_income`)
- Invalid names detection

#### `context_aware_validation_example()`
Shows advanced validation capabilities:
- Context-aware node recognition
- Sub-node validation (e.g., quarterly segments)
- Formula node validation with parent dependencies
- Calculation node validation

#### `create_validated_bank_data()`
Creates sample banking data using validated node names:
- Demonstrates real-world data import scenarios
- Shows automatic name standardization
- Provides validation feedback during data creation

#### `validate_data_completeness()`
Comprehensive data quality assessment:
- Checks for required banking nodes
- Identifies recommended but missing nodes
- Calculates completeness scores
- Provides actionable feedback

### Enhanced Analysis Workflow

The enhanced banking analysis follows this validation-integrated workflow:

1. **Node Name Validation**: Demonstrate basic validation capabilities
2. **Context-Aware Validation**: Show advanced validation features
3. **Validated Data Creation**: Create sample data with validation
4. **Data Completeness Check**: Assess data quality and completeness
5. **Banking Analysis**: Perform comprehensive financial analysis
6. **Validation-Enhanced Metrics**: Show how validation improves metric calculations

## Banking-Specific Validation Rules

### Standard Node Names
The validator recognizes these standard banking node names:
- `total_loans`
- `non_performing_loans`
- `allowance_for_loan_losses`
- `total_deposits`
- `net_interest_income`
- `provision_for_loan_losses`
- `tier_1_capital`
- `risk_weighted_assets`

### Common Alternate Names
The validator automatically standardizes these alternate names:
- `npl` → `non_performing_loans`
- `loan_loss_allowance` → `allowance_for_loan_losses`
- `deposits` → `total_deposits`
- `nii` → `net_interest_income`
- `rwa` → `total_risk_weighted_assets`
- `tier_1_capital` → `total_tier_1_capital`

### Required Banking Nodes
For comprehensive banking analysis, these nodes are required:
- `total_loans`
- `non_performing_loans`
- `allowance_for_loan_losses`
- `total_deposits`
- `total_equity`
- `net_interest_income`
- `non_interest_income`
- `non_interest_expense`
- `provision_for_loan_losses`
- `tier_1_capital`
- `risk_weighted_assets`

### Recommended Banking Nodes
These nodes enhance analysis quality:
- `high_quality_liquid_assets`
- `net_cash_outflows_30_days`
- `available_stable_funding`
- `required_stable_funding`
- `common_equity_tier_1_capital`
- `total_capital`

## Validation Benefits

### 1. Data Quality Assurance
- **Early Error Detection**: Identifies data issues before analysis
- **Consistent Naming**: Ensures standardized node names across datasets
- **Missing Data Alerts**: Highlights incomplete data sets

### 2. Improved Analysis Reliability
- **Standardized Inputs**: Ensures consistent metric calculations
- **Reduced Errors**: Minimizes calculation errors from naming inconsistencies
- **Better Debugging**: Provides clear error messages and validation feedback

### 3. Enhanced User Experience
- **Automatic Corrections**: Fixes common naming issues automatically
- **Clear Feedback**: Provides informative validation messages
- **Quality Scoring**: Gives users confidence in data completeness

## Usage Examples

### Basic Node Validation
```python
from fin_statement_model.io.validation import UnifiedNodeValidator

validator = UnifiedNodeValidator(auto_standardize=True)
result = validator.validate("npl")
# Result: result.standardized_name = "non_performing_loans"
#         result.is_valid = True
#         result.message = "Standardized 'npl' to 'non_performing_loans'"
```

### Context-Aware Validation
```python
from fin_statement_model.io.validation import UnifiedNodeValidator

validator = UnifiedNodeValidator(strict_mode=False, auto_standardize=True, enable_patterns=True)
result = validator.validate("revenue_q1", node_type="data")
# Recognizes as valid quarterly sub-node of revenue
# result.category = "subnode"
```

### Data Completeness Check
```python
validation_report = validate_data_completeness(bank_data)
completeness_score = validation_report["completeness_score"]
missing_required = validation_report["required_missing"]
```

## Integration with Banking Metrics

The validation system integrates seamlessly with banking metric calculations:

1. **Input Validation**: Validates metric input node names
2. **Automatic Standardization**: Converts alternate names to standard forms
3. **Error Prevention**: Prevents calculation errors from naming issues
4. **Quality Feedback**: Provides validation feedback during calculations

## Best Practices

### 1. Always Validate Input Data
- Run validation before performing analysis
- Check data completeness scores
- Address missing required nodes

### 2. Use Standardized Names
- Prefer standard node names in code
- Let the validator handle alternate names from external sources
- Document any custom naming conventions

### 3. Monitor Data Quality
- Track completeness scores over time
- Set minimum quality thresholds
- Implement data quality alerts

### 4. Leverage Validation Feedback
- Use validation messages for debugging
- Provide user-friendly error messages
- Log validation results for audit trails

## Conclusion

The enhanced banking analysis with validation demonstrates how to build robust, reliable financial analysis systems. By integrating validation at multiple levels, the system ensures data quality, reduces errors, and provides better user experiences while maintaining the flexibility to handle diverse data sources and naming conventions.

This implementation serves as a template for building production-ready financial analysis systems that prioritize data quality and reliability. 