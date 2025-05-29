"""Example demonstrating the use of adjustments in the financial statement model."""

import logging

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.core.adjustments.models import AdjustmentType

# Configure logging for visibility
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- 1. Setup Graph and Nodes ---
logger.info("Setting up the graph and base data...")
graph = Graph()

# Prepare initial data
revenue_data = {"2023": 1000.0, "2024": 1200.0}
cogs_data = {"2023": 400.0, "2024": 500.0}

# Create nodes with initial data
revenue = FinancialStatementItemNode(name="Revenue", values=revenue_data)
cogs = FinancialStatementItemNode(name="COGS", values=cogs_data)

# Add nodes to the graph
graph.add_node(revenue)
graph.add_node(cogs)

# No need for set_node_value here, data is added via constructor

logger.info(f"Initial Revenue 2023: {graph.calculate('Revenue', '2023')}")
logger.info(f"Initial Revenue 2024: {graph.calculate('Revenue', '2024')}")

# --- 2. Additive Adjustment ---
logger.info("\n--- Applying Additive Adjustment ---")

adj_id_1 = graph.add_adjustment(
    node_name="Revenue",
    period="2023",
    value=50.0,
    adj_type=AdjustmentType.ADDITIVE,
    reason="Manual uplift based on late contract signing.",
    tags={"manual", "contract"},
    user="Analyst1",
)
logger.info(f"Added additive adjustment {adj_id_1} for Revenue 2023.")

# Get the value *with* adjustments applied (default behavior)
adjusted_revenue_2023 = graph.get_adjusted_value("Revenue", "2023")
logger.info(f"Adjusted Revenue 2023: {adjusted_revenue_2023}")

# Verify the adjustment was applied
adj_list_2023 = graph.get_adjustments("Revenue", "2023")
logger.info(f"Adjustments applied to Revenue 2023: {adj_list_2023}")

# Value for 2024 should be unaffected
adjusted_revenue_2024 = graph.get_adjusted_value("Revenue", "2024")
logger.info(f"Adjusted Revenue 2024 (should be unchanged): {adjusted_revenue_2024}")

# --- 3. Replacement Adjustment ---
logger.info("\n--- Applying Replacement Adjustment ---")

adj_id_2 = graph.add_adjustment(
    node_name="COGS",
    period="2024",
    value=555.0,
    adj_type=AdjustmentType.REPLACEMENT,
    reason="Revised COGS estimate based on new supplier quote.",
    tags={"estimate", "supplier"},
    user="Analyst2",
    priority=-10,  # Higher priority (lower number)
)
logger.info(f"Added replacement adjustment {adj_id_2} for COGS 2024.")

adjusted_cogs_2024 = graph.get_adjusted_value("COGS", "2024")
logger.info(f"Adjusted COGS 2024: {adjusted_cogs_2024}")

# Check adjustments for COGS 2024
adj_list_cogs_2024 = graph.get_adjustments("COGS", "2024")
logger.info(f"Adjustments applied to COGS 2024: {adj_list_cogs_2024}")


# --- 4. Listing All Adjustments ---
logger.info("\n--- Listing All Adjustments in the Graph ---")
all_adjustments = graph.list_all_adjustments()
logger.info(f"Total adjustments found: {len(all_adjustments)}")
for adj in all_adjustments:
    logger.info(
        f"  - {adj.id}: Node='{adj.node_name}', Period='{adj.period}', Type='{adj.type.name}', Value={adj.value}, Reason='{adj.reason}'"
    )

# --- 5. Removing an Adjustment ---
logger.info("\n--- Removing an Adjustment ---")
removed = graph.remove_adjustment(adj_id_1)
logger.info(f"Attempted to remove adjustment {adj_id_1}. Success: {removed}")

# Check Revenue 2023 value again
adjusted_revenue_2023_after_remove = graph.get_adjusted_value("Revenue", "2023")
logger.info(
    f"Adjusted Revenue 2023 after removal: {adjusted_revenue_2023_after_remove}"
)

# Verify it's gone
adj_list_2023_after_remove = graph.get_adjustments("Revenue", "2023")
logger.info(f"Adjustments for Revenue 2023 after removal: {adj_list_2023_after_remove}")


logger.info("\nExample complete.")
