"""Real Estate Investment Trust (REIT) Analysis Example.

This example demonstrates using specialized real estate metrics and calculations
for analyzing REIT financial performance.
"""

import logging
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import ItemNode, MetricNode
from fin_statement_model.core.metrics import metric_registry

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_reit_financial_model():
    """Create a financial model for a REIT with specialized metrics."""
    graph = Graph()
    
    # === Income Statement Items ===
    income_items = {
        # Revenue
        "rental_income": {"2022": 50000000, "2023": 55000000},
        "property_management_fees": {"2022": 2500000, "2023": 2750000},
        "other_income": {"2022": 1000000, "2023": 1200000},
        
        # Operating Expenses
        "property_operating_expenses": {"2022": 18000000, "2023": 20000000},
        "property_management_expenses": {"2022": 3500000, "2023": 3850000},
        "general_admin_expenses": {"2022": 4000000, "2023": 4400000},
        "depreciation_expense": {"2022": 12000000, "2023": 13200000},
        
        # Other
        "interest_expense": {"2022": 8000000, "2023": 8500000},
        "gain_on_property_sales": {"2022": 2000000, "2023": 1500000},
    }
    
    # === Balance Sheet Items ===
    balance_sheet_items = {
        # Assets
        "investment_properties": {"2022": 600000000, "2023": 650000000},
        "accumulated_depreciation": {"2022": -120000000, "2023": -133200000},
        "cash": {"2022": 15000000, "2023": 18000000},
        "accounts_receivable": {"2022": 3000000, "2023": 3500000},
        
        # Liabilities
        "mortgages_payable": {"2022": 350000000, "2023": 380000000},
        "bonds_payable": {"2022": 50000000, "2023": 50000000},
        "accounts_payable": {"2022": 2000000, "2023": 2200000},
        
        # Equity
        "common_shares": {"2022": 100000000, "2023": 100000000},
        "preferred_shares": {"2022": 25000000, "2023": 25000000},
        "retained_earnings": {"2022": 70000000, "2023": 77300000},
        
        # Share count for per-share metrics
        "shares_outstanding": {"2022": 10000000, "2023": 10000000},
    }
    
    # === Cash Flow Items ===
    cash_flow_items = {
        "capital_expenditures": {"2022": 45000000, "2023": 50000000},
        "property_acquisitions": {"2022": 30000000, "2023": 35000000},
        "dividends_paid": {"2022": 22000000, "2023": 24000000},
    }
    
    # Add all items to graph
    for name, values in {**income_items, **balance_sheet_items, **cash_flow_items}.items():
        node = ItemNode(name)
        for period, value in values.items():
            node.set_value(period, value)
        graph.add_node(node)
    
    # === Add REIT-Specific Metrics ===
    
    # Net Operating Income (NOI)
    noi = MetricNode(
        name="net_operating_income",
        metric_id="net_operating_income",
        inputs={
            "rental_income": "rental_income",
            "property_management_fees": "property_management_fees",
            "other_income": "other_income",
            "property_operating_expenses": "property_operating_expenses",
        }
    )
    graph.add_node(noi)
    
    # Funds From Operations (FFO)
    ffo = MetricNode(
        name="funds_from_operations",
        metric_id="funds_from_operations",
        inputs={
            "net_income": "net_income",  # Would need to calculate this
            "depreciation_expense": "depreciation_expense",
            "gain_on_property_sales": "gain_on_property_sales",
        }
    )
    graph.add_node(ffo)
    
    # FFO per Share
    ffo_per_share = MetricNode(
        name="ffo_per_share",
        metric_id="ffo_per_share",
        inputs={
            "funds_from_operations": "funds_from_operations",
            "shares_outstanding": "shares_outstanding",
        }
    )
    graph.add_node(ffo_per_share)
    
    # Cap Rate
    cap_rate = MetricNode(
        name="capitalization_rate",
        metric_id="capitalization_rate",
        inputs={
            "net_operating_income": "net_operating_income",
            "investment_properties": "investment_properties",
        }
    )
    graph.add_node(cap_rate)
    
    # Debt Service Coverage Ratio
    dscr = MetricNode(
        name="debt_service_coverage_ratio",
        metric_id="debt_service_coverage_ratio",
        inputs={
            "net_operating_income": "net_operating_income",
            "interest_expense": "interest_expense",
        }
    )
    graph.add_node(dscr)
    
    return graph


def analyze_reit_performance(graph, period="2023"):
    """Analyze REIT performance using specialized metrics."""
    logger.info("=== REIT Analysis Example ===\n")
    
    # Calculate key REIT metrics
    metrics_to_calculate = [
        ("net_operating_income", "Net Operating Income"),
        ("funds_from_operations", "Funds From Operations (FFO)"),
        ("ffo_per_share", "FFO per Share"),
        ("capitalization_rate", "Cap Rate"),
        ("debt_service_coverage_ratio", "Debt Service Coverage Ratio"),
    ]
    
    logger.info("Key REIT Metrics for 2023:")
    logger.info("-" * 40)
    
    for metric_id, display_name in metrics_to_calculate:
        try:
            value = graph.calculate(metric_id, period)
            
            # Get metric definition for interpretation
            metric_def = metric_registry.get_metric(metric_id)
            
            # Format based on metric type
            if metric_id in ["net_operating_income", "funds_from_operations"]:
                logger.info(f"{display_name}: ${value:,.0f}")
            elif metric_id == "capitalization_rate":
                # Cap rate is typically shown as percentage
                logger.info(f"{display_name}: {value:.1f}%")
                
                # Provide interpretation
                if hasattr(metric_def, 'interpret'):
                    interpretation = metric_def.interpret(value)
                    logger.info(f"  → {interpretation['interpretation_message']}")
            elif metric_id == "ffo_per_share":
                logger.info(f"{display_name}: ${value:.2f}")
            elif metric_id == "debt_service_coverage_ratio":
                logger.info(f"{display_name}: {value:.1f}x")
                
                # Provide interpretation
                if hasattr(metric_def, 'interpret'):
                    interpretation = metric_def.interpret(value)
                    logger.info(f"  → {interpretation['interpretation_message']}")
            else:
                logger.info(f"{display_name}: {value:.2f}")
                
        except Exception as e:
            logger.error(f"Could not calculate {display_name}: {e}")
        logger.info("")
    
    # Growth analysis
    logger.info("Growth Analysis:")
    logger.info("-" * 40)
    
    try:
        # NOI growth
        noi_2022 = graph.calculate("net_operating_income", "2022")
        noi_2023 = graph.calculate("net_operating_income", "2023")
        noi_growth = ((noi_2023 - noi_2022) / noi_2022) * 100
        logger.info(f"NOI Growth (2022-2023): {noi_growth:.1f}%")
        
        # FFO growth
        ffo_2022 = graph.calculate("funds_from_operations", "2022")
        ffo_2023 = graph.calculate("funds_from_operations", "2023")
        ffo_growth = ((ffo_2023 - ffo_2022) / ffo_2022) * 100
        logger.info(f"FFO Growth (2022-2023): {ffo_growth:.1f}%")
    except Exception as e:
        logger.error(f"Could not calculate growth metrics: {e}")
    
    logger.info("\n=== Analysis Complete ===")


def main():
    """Run the REIT analysis example."""
    # Create the REIT financial model
    graph = create_reit_financial_model()
    
    # Analyze performance
    analyze_reit_performance(graph)


if __name__ == "__main__":
    main()
