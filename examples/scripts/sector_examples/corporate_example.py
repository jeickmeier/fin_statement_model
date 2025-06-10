"""This example demonstrates using the detailed test_statement.yaml configuration.

It includes:
- Loading the complex statement configuration.
- Populating a graph with corresponding sample data.
- Generating the statement DataFrame based on the config.

NEW FEATURES ADDED:
- Node name validation and normalization using UnifiedNodeValidator
- Automatic standardization of alternate node names (e.g., 'cash' -> 'cash_and_equivalents')
- Recognition of sub-node patterns (e.g., 'revenue_q1', 'revenue_2024')
- Formula node pattern detection (e.g., 'gross_margin', 'debt_ratio')
- Comprehensive validation reporting with suggestions for improvement
- Context-aware validation that understands node relationships and dependencies

The validators help ensure:
1. Consistency across financial models
2. Proper metric functionality (metrics expect standard node names)
3. Better code maintainability and readability
4. Helpful suggestions for non-standard names
"""

import logging
import sys
import yaml
from pathlib import Path
import pandas as pd
from fin_statement_model.core.errors import FinancialModelError

from fin_statement_model.io import read_data, write_data
from fin_statement_model.statements import create_statement_dataframe
from fin_statement_model.forecasting.forecaster import StatementForecaster

# Import unified validator
from fin_statement_model.io.validation import UnifiedNodeValidator
from fin_statement_model.core.nodes import standard_node_registry

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- 1. Setup ---

# Hardcoded paths (as modified by user)
SCRIPT_DIR = Path(__file__).parent
md_output_path = SCRIPT_DIR / "output" / "test_statement.md"
TEST_CONFIG_PATH = SCRIPT_DIR.parent / "configs" / "test_statement.yaml"

# --- 2. Sample Data ---

# Sample historical data matching node_ids in test_statement.yaml
# Note: The keys must match the 'node_id' or 'metric_id'/'inputs' references
historical_data = {
    # Node ID: { Period: Value }
    # Add a 2021 data point for better historical average calculations
    "cash_and_equivalents": {"2021": 90.0, "2022": 100.0, "2023": 120.0},
    "accounts_receivable": {"2021": 180.0, "2022": 200.0, "2023": 250.0},
    "property_plant_equipment": {"2021": 480.0, "2022": 500.0, "2023": 550.0},
    "accounts_payable": {"2021": 140.0, "2022": 150.0, "2023": 180.0},
    "total_debt": {"2021": 290.0, "2022": 300.0, "2023": 320.0},
    "common_stock": {"2021": 100.0, "2022": 100.0, "2023": 100.0},
    "retained_earnings": {"2021": 80.0, "2022": 100.0, "2023": 125.0},
    "revenue": {"2021": 900.0, "2022": 1000.0, "2023": 1200.0},
    "cost_of_goods_sold": {"2021": -350.0, "2022": -400.0, "2023": -500.0},
    "operating_expenses": {"2021": 280.0, "2022": 300.0, "2023": 350.0},
    "operating_income": {
        "2021": 270.0,
        "2022": 300.0,
        "2023": 350.0,
    },  # Calculated: gross_profit - operating_expenses
    "interest_expense": {"2021": 15.0, "2022": 18.0, "2023": 20.0},
    "income_tax": {"2021": 45.0, "2022": 55.0, "2023": 65.0},
    "dividends": {"2021": 20.0, "2022": 25.0, "2023": 30.0},
}

# --- 2b. Node Name Validation and Normalization ---

logger.info("Validating and normalizing node names...")

# Demo only: direct use of UnifiedNodeValidator; production code should use StatementConfig/StatementStructureBuilder for validation
# Create unified validator for demo
validator = UnifiedNodeValidator(
    standard_node_registry,
    strict_mode=False,  # Allow alternate names
    auto_standardize=True,  # Automatically convert to standard names
    warn_on_non_standard=True,  # Warn about non-standard names
    enable_patterns=True,  # Enable pattern recognition for sub-nodes and formulas
)

# Demonstrate validation with some non-standard names
logger.info("\n=== DEMONSTRATION: Validating various node name patterns ===")

demo_names = [
    "cash",  # Alternate name
    "ar",  # Alternate name for accounts_receivable
    "revenue_q1",  # Sub-node pattern (quarterly)
    "revenue_2024",  # Sub-node pattern (annual)
    "revenue_north_america",  # Sub-node pattern (geographic)
    "gross_margin",  # Formula pattern
    "debt_ratio",  # Formula pattern
    "custom_metric_xyz",  # Unrecognized name
    "sales",  # Alternate for revenue
    "cogs",  # Alternate for cost_of_goods_sold
]

logger.info(f"Demo names to validate: {demo_names}")

for demo_name in demo_names:
    result = validator.validate(demo_name)
    logger.info(
        f"  '{demo_name}' -> '{result.standardized_name}' [{result.category}] ({result.message})"
    )

    if result.suggestions:
        logger.info(
            f"    Suggestions: {result.suggestions[:2]}"
        )  # Show first 2 suggestions
    logger.info("")

logger.info("=== END DEMONSTRATION ===\n")

# Validate and normalize historical data node names
original_node_names = list(historical_data.keys())
logger.info(f"Original node names: {original_node_names}")

# Use unified validator
validation_results = validator.validate_batch(original_node_names)

# Create normalized historical data
normalized_historical_data = {}
name_changes = []

for original_name, result in validation_results.items():
    if result.standardized_name != original_name:
        name_changes.append((original_name, result.standardized_name))
        logger.info(
            f"  Normalized: '{original_name}' -> '{result.standardized_name}' ({result.message})"
        )
    else:
        logger.info(f"  Validated: '{original_name}' - {result.message}")

    # Copy data with standardized name
    normalized_historical_data[result.standardized_name] = historical_data[
        original_name
    ]

# Show validation summary
logger.info("\nValidation Summary:")
logger.info(f"  Total nodes validated: {len(validation_results)}")
valid_count = sum(1 for r in validation_results.values() if r.is_valid)
logger.info(f"  Valid nodes: {valid_count}")
logger.info(f"  Invalid nodes: {len(validation_results) - valid_count}")

# Count by category
categories = {}
for result in validation_results.values():
    categories[result.category] = categories.get(result.category, 0) + 1

for category, count in categories.items():
    logger.info(f"  {category}: {count}")

# Show unrecognized names with suggestions
unrecognized = [
    name
    for name, result in validation_results.items()
    if result.category in ["custom", "invalid"]
]
if unrecognized:
    logger.info(f"\nUnrecognized node names: {unrecognized}")
    for name in unrecognized:
        if validation_results[name].suggestions:
            logger.info(
                f"  Suggestions for '{name}': {validation_results[name].suggestions}"
            )

# Update historical_data to use normalized names
historical_data = normalized_historical_data

# Also normalize forecast_configs keys to match
logger.info("\nNormalizing forecast configuration keys...")
normalized_forecast_configs = {}
for original_name, config in {
    "cash_and_equivalents": {"method": "simple", "config": 0.05},  # 5% growth
    "accounts_receivable": {
        "method": "curve",
        "config": [0.08, 0.06, 0.05, 0.04, 0.03],  # Slowing growth over 5 years
    },  # Slowing growth
    "property_plant_equipment": {"method": "simple", "config": 0.02},  # 2% growth
    "accounts_payable": {
        "method": "curve",
        "config": [0.04, 0.03, 0.03, 0.02, 0.02],
    },  # Declining curve
    "total_debt": {"method": "simple", "config": 0.0},  # Assume flat debt
    "common_stock": {
        "method": "simple",
        "config": 0.0,
    },  # Assume flat common stock
    "retained_earnings": {
        "method": "simple",
        "config": 0.0,
    },  # Usually calculated, but forecast base if needed
    "dividends": {
        "method": "historical_growth",
        "config": None,
    },  # Grow based on historical trend
    "revenue": {
        "method": "curve",
        "config": [0.10, 0.09, 0.08, 0.07, 0.06],
    },  # Declining revenue growth
    "cost_of_goods_sold": {
        "method": "historical_growth",
        "config": None,
    },  # COGS based on historical growth
    "operating_expenses": {
        "method": "statistical",
        "config": {
            "distribution": "normal",
            "params": {"mean": 0.03, "std": 0.015},  # Normal dist around 3% mean
        },
    },  # Statistical forecast with normal distribution
    "operating_income": {
        "method": "historical_growth",
        "config": None,
    },  # Operating income based on historical growth
    "interest_expense": {
        "method": "historical_growth",
        "config": None,
    },  # Interest expense based on historical growth
    "income_tax": {
        "method": "historical_growth",
        "config": None,
    },  # Tax expense based on historical growth
}.items():
    # Validate and normalize forecast config keys
    result = validator.validate(original_name)
    normalized_forecast_configs[result.standardized_name] = config
    if result.standardized_name != original_name:
        logger.info(
            f"  Forecast config: '{original_name}' -> '{result.standardized_name}'"
        )

forecast_configs = normalized_forecast_configs

logger.info(f"\nFinal normalized node names: {sorted(historical_data.keys())}")

# --- 3. Graph Creation and Initial Data Loading ---

# Restore try-except block
try:
    logger.info("\nCreating graph and loading initial data...")
    graph = read_data(format_type="dict", source=historical_data)
    logger.info(f"Graph created with initial periods: {graph.periods}")
except FinancialModelError:
    logger.exception("Error creating graph or loading initial data", file=sys.stderr)
    sys.exit(1)

# --- 3c. Post-Graph Node Validation ---

logger.info("\nValidating graph nodes with unified validator...")

# Get all nodes from the graph
graph_nodes = list(graph.nodes.values())
logger.info(f"Graph contains {len(graph_nodes)} nodes")

# Validate each node in the graph
node_validation_results = {}
for node in graph_nodes:
    # Determine node type and parent nodes for context-aware validation
    node_type = "data"  # Default to data node
    parent_nodes = None

    if hasattr(node, "inputs") and node.inputs:
        node_type = "calculation"
        # Extract parent node names
        if isinstance(node.inputs, dict):
            parent_nodes = list(node.inputs.keys())
        elif isinstance(node.inputs, list):
            parent_nodes = [n.name for n in node.inputs if hasattr(n, "name")]

    result = validator.validate(
        node.name, node_type=node_type, parent_nodes=parent_nodes
    )
    node_validation_results[node.name] = result

# Display categorized results
categories_in_graph = {}
for node_name, result in node_validation_results.items():
    category = result.category
    if category not in categories_in_graph:
        categories_in_graph[category] = []
    categories_in_graph[category].append(
        {
            "name": node_name,
            "message": result.message,
            "standardized": result.standardized_name,
        }
    )

for category, nodes in categories_in_graph.items():
    if nodes:  # Only show categories that have nodes
        logger.info(f"\n{category.upper()} nodes ({len(nodes)}):")
        for node_info in nodes:
            logger.info(f"  - {node_info['name']}: {node_info['message']}")

# Show any naming improvement suggestions
logger.info("\nNaming improvement suggestions:")
suggestions_found = False
for node_name, result in node_validation_results.items():
    if result.suggestions:
        suggestions_found = True
        logger.info(f"  {node_name}: {result.suggestions}")

if not suggestions_found:
    logger.info(
        "  All node names are using standard conventions - no improvements needed!"
    )

# --- 3b. Forecasting Setup ---
logger.info("Setting up forecasting...")

historical_periods = sorted(list(graph.periods))
forecast_periods = [
    "2024",
    "2025",
    "2026",
    "2027",
    "2028",
]  # Hardcoded as per user changes
all_periods = sorted(historical_periods + forecast_periods)

logger.info(f"Historical periods: {historical_periods}")
logger.info(f"Forecast periods: {forecast_periods}")

# Use the StatementForecaster
# Restore try-except block
forecaster = StatementForecaster(
    fsg=graph
)  # fsg likely stands for financial statement graph
logger.info(f"Applying forecasts for periods: {forecast_periods}")

# Apply the forecasts using the defined configs
forecaster.create_forecast(
    forecast_periods=forecast_periods,
    node_configs=forecast_configs,
    historical_periods=historical_periods,
)

# --- 4. Statement Generation ---

# Load corporate statement config from YAML into memory
raw_config = yaml.safe_load(Path(TEST_CONFIG_PATH).read_text(encoding="utf-8"))
stmt_id = raw_config.get("id", "test_statement")
raw_configs = {stmt_id: raw_config}

# Generate the statement DataFrame
df_map = create_statement_dataframe(
    graph=graph,
    raw_configs=raw_configs,
    format_kwargs={
        "should_apply_signs": True,
        "number_format": ",.1f",
    },
)
statement_df = df_map[stmt_id]

with pd.option_context(
    "display.max_rows", None, "display.max_columns", None, "display.width", 1000
):
    logger.info(statement_df.to_string(index=False))

# Write output data
write_data(
    format_type="markdown",
    graph=graph,
    target=str(md_output_path),
    raw_configs=raw_configs,
    historical_periods=historical_periods,
    forecast_configs=forecast_configs,
)
