"""Test real estate specific metrics."""

from fin_statement_model.core.metrics import metric_registry
from fin_statement_model.core.nodes import (
    FinancialStatementItemNode,
    FormulaCalculationNode,
)


class TestRealEstateMetrics:
    """Test real estate specific metrics."""

    def test_real_estate_metrics_loaded(self):
        """Test that real estate metrics are loaded correctly."""
        # Check that real estate metrics exist
        real_estate_metrics = [
            m
            for m in metric_registry.list_metrics()
            if "real_estate" in metric_registry.get(m).category
        ]

        assert len(real_estate_metrics) > 0, "No real estate metrics found"

        # Check for specific key metrics
        expected_metrics = [
            "net_operating_income",
            "funds_from_operations",
            "adjusted_funds_from_operations",
            "capitalization_rate",
            "occupancy_rate",
            "ffo_per_share",
            "affo_per_share",
        ]

        for metric in expected_metrics:
            assert metric in metric_registry, f"Expected metric {metric} not found"

    def test_noi_calculation(self):
        """Test Net Operating Income calculation."""
        # Create test nodes
        rental_income = FinancialStatementItemNode("rental_income", {"2023": 1000000})
        other_income = FinancialStatementItemNode("other_property_income", {"2023": 50000})
        operating_expenses = FinancialStatementItemNode(
            "property_operating_expenses", {"2023": 400000}
        )

        # Get NOI metric definition
        noi_metric = metric_registry.get("net_operating_income")

        # Create calculation node
        noi_node = FormulaCalculationNode(
            "noi_test",
            inputs={
                "rental_income": rental_income,
                "other_property_income": other_income,
                "property_operating_expenses": operating_expenses,
            },
            formula=noi_metric.formula,
        )

        # Test calculation
        result = noi_node.calculate("2023")
        expected = 1000000 + 50000 - 400000  # 650,000
        assert result == expected

    def test_ffo_calculation(self):
        """Test Funds From Operations calculation."""
        # Create test nodes
        net_income = FinancialStatementItemNode("net_income", {"2023": 500000})
        depreciation = FinancialStatementItemNode("depreciation_and_amortization", {"2023": 200000})
        gains = FinancialStatementItemNode("gains_on_property_sales", {"2023": 50000})

        # Get FFO metric definition
        ffo_metric = metric_registry.get("funds_from_operations")

        # Create calculation node
        ffo_node = FormulaCalculationNode(
            "ffo_test",
            inputs={
                "net_income": net_income,
                "depreciation_and_amortization": depreciation,
                "gains_on_property_sales": gains,
            },
            formula=ffo_metric.formula,
        )

        # Test calculation
        result = ffo_node.calculate("2023")
        expected = 500000 + 200000 - 50000  # 650,000
        assert result == expected

    def test_occupancy_rate_calculation(self):
        """Test Occupancy Rate calculation."""
        # Create test nodes
        occupied_sf = FinancialStatementItemNode("occupied_square_feet", {"2023": 90000})
        total_sf = FinancialStatementItemNode("total_rentable_square_feet", {"2023": 100000})

        # Get occupancy metric definition
        occupancy_metric = metric_registry.get("occupancy_rate")

        # Create calculation node
        occupancy_node = FormulaCalculationNode(
            "occupancy_test",
            inputs={
                "occupied_square_feet": occupied_sf,
                "total_rentable_square_feet": total_sf,
            },
            formula=occupancy_metric.formula,
        )

        # Test calculation
        result = occupancy_node.calculate("2023")
        expected = (90000 / 100000) * 100  # 90%
        assert result == expected

    def test_cap_rate_calculation(self):
        """Test Capitalization Rate calculation."""
        # Create test nodes
        noi = FinancialStatementItemNode("net_operating_income", {"2023": 650000})
        property_value = FinancialStatementItemNode("property_value", {"2023": 10000000})

        # Get cap rate metric definition
        cap_rate_metric = metric_registry.get("capitalization_rate")

        # Create calculation node
        cap_rate_node = FormulaCalculationNode(
            "cap_rate_test",
            inputs={"net_operating_income": noi, "property_value": property_value},
            formula=cap_rate_metric.formula,
        )

        # Test calculation
        result = cap_rate_node.calculate("2023")
        expected = (650000 / 10000000) * 100  # 6.5%
        assert result == expected

    def test_ffo_per_share_calculation(self):
        """Test FFO Per Share calculation."""
        # Create test nodes
        ffo = FinancialStatementItemNode("funds_from_operations", {"2023": 650000})
        shares = FinancialStatementItemNode("shares_outstanding", {"2023": 100000})

        # Get FFO per share metric definition
        ffo_ps_metric = metric_registry.get("ffo_per_share")

        # Create calculation node
        ffo_ps_node = FormulaCalculationNode(
            "ffo_ps_test",
            inputs={"funds_from_operations": ffo, "shares_outstanding": shares},
            formula=ffo_ps_metric.formula,
        )

        # Test calculation
        result = ffo_ps_node.calculate("2023")
        expected = 650000 / 100000  # $6.50 per share
        assert result == expected

    def test_metric_interpretations(self):
        """Test that real estate metrics have proper interpretation guidelines."""
        # Test metrics that should have interpretation guidelines
        metrics_with_interpretations = [
            "occupancy_rate",
            "capitalization_rate",
            "same_store_noi_growth",
            "dividend_coverage_ratio_(affo)",
        ]

        for metric_name in metrics_with_interpretations:
            metric = metric_registry.get(metric_name)
            assert metric.interpretation is not None, f"Metric {metric_name} missing interpretation"
            assert metric.interpretation.notes is not None, (
                f"Metric {metric_name} missing interpretation notes"
            )
