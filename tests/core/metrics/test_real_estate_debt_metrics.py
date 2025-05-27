"""Test real estate debt specific metrics."""

from fin_statement_model.core.metrics import metric_registry
from fin_statement_model.core.nodes import (
    FinancialStatementItemNode,
    FormulaCalculationNode,
)


class TestRealEstateDebtMetrics:
    """Test real estate debt specific metrics."""

    def test_real_estate_debt_metrics_loaded(self):
        """Test that real estate debt metrics are loaded correctly."""
        # Check that real estate debt metrics exist
        debt_metrics = [
            m
            for m in metric_registry.list_metrics()
            if "real_estate_debt" in metric_registry.get(m).category
        ]

        assert len(debt_metrics) > 0, "No real estate debt metrics found"

        # Check for specific key debt metrics
        expected_metrics = [
            "loan_to_value_ratio",
            "debt_service_coverage_ratio_(real_estate)",
            "interest_coverage_ratio_(real_estate)",
            "unencumbered_asset_ratio",
            "fixed_rate_debt_percentage",
            "weighted_average_interest_rate",
            "debt_maturity_profile",
            "construction_loan_to_cost_ratio",
            "debt_yield",
        ]

        for metric in expected_metrics:
            assert metric in metric_registry, f"Expected debt metric {metric} not found"

    def test_loan_to_value_ratio_calculation(self):
        """Test Loan-to-Value Ratio calculation."""
        # Create test nodes
        total_debt = FinancialStatementItemNode("total_debt", {"2023": 6_000_000})
        property_value = FinancialStatementItemNode("total_property_value", {"2023": 10_000_000})

        # Get LTV metric definition
        ltv_metric = metric_registry.get("loan_to_value_ratio")

        # Create calculation node
        ltv_node = FormulaCalculationNode(
            "ltv_test",
            inputs={"total_debt": total_debt, "total_property_value": property_value},
            formula=ltv_metric.formula,
        )

        # Test calculation
        result = ltv_node.calculate("2023")
        expected = (6_000_000 / 10_000_000) * 100  # 60%
        assert result == expected

    def test_debt_service_coverage_ratio_calculation(self):
        """Test Debt Service Coverage Ratio calculation."""
        # Create test nodes
        noi = FinancialStatementItemNode("net_operating_income", {"2023": 1_500_000})
        debt_service = FinancialStatementItemNode("mortgage_payments", {"2023": 1_200_000})

        # Get DSCR metric definition
        dscr_metric = metric_registry.get("debt_service_coverage_ratio_(real_estate)")

        # Create calculation node
        dscr_node = FormulaCalculationNode(
            "dscr_test",
            inputs={"net_operating_income": noi, "mortgage_payments": debt_service},
            formula=dscr_metric.formula,
        )

        # Test calculation
        result = dscr_node.calculate("2023")
        expected = 1_500_000 / 1_200_000  # 1.25x
        assert result == expected

    def test_interest_coverage_ratio_calculation(self):
        """Test Interest Coverage Ratio calculation."""
        # Create test nodes
        noi = FinancialStatementItemNode("net_operating_income", {"2023": 2_000_000})
        interest = FinancialStatementItemNode("interest_payments", {"2023": 800_000})

        # Get ICR metric definition
        icr_metric = metric_registry.get("interest_coverage_ratio_(real_estate)")

        # Create calculation node
        icr_node = FormulaCalculationNode(
            "icr_test",
            inputs={"net_operating_income": noi, "interest_payments": interest},
            formula=icr_metric.formula,
        )

        # Test calculation
        result = icr_node.calculate("2023")
        expected = 2_000_000 / 800_000  # 2.5x
        assert result == expected

    def test_unencumbered_asset_ratio_calculation(self):
        """Test Unencumbered Asset Ratio calculation."""
        # Create test nodes
        unencumbered = FinancialStatementItemNode("unencumbered_assets", {"2023": 3_000_000})
        total_value = FinancialStatementItemNode("total_property_value", {"2023": 10_000_000})

        # Get UAR metric definition
        uar_metric = metric_registry.get("unencumbered_asset_ratio")

        # Create calculation node
        uar_node = FormulaCalculationNode(
            "uar_test",
            inputs={
                "unencumbered_assets": unencumbered,
                "total_property_value": total_value,
            },
            formula=uar_metric.formula,
        )

        # Test calculation
        result = uar_node.calculate("2023")
        expected = (3_000_000 / 10_000_000) * 100  # 30%
        assert result == expected

    def test_fixed_rate_debt_percentage_calculation(self):
        """Test Fixed Rate Debt Percentage calculation."""
        # Create test nodes
        fixed_debt = FinancialStatementItemNode("fixed_rate_debt", {"2023": 8_000_000})
        total_debt = FinancialStatementItemNode("total_debt", {"2023": 10_000_000})

        # Get fixed rate percentage metric definition
        frd_metric = metric_registry.get("fixed_rate_debt_percentage")

        # Create calculation node
        frd_node = FormulaCalculationNode(
            "frd_test",
            inputs={"fixed_rate_debt": fixed_debt, "total_debt": total_debt},
            formula=frd_metric.formula,
        )

        # Test calculation
        result = frd_node.calculate("2023")
        expected = (8_000_000 / 10_000_000) * 100  # 80%
        assert result == expected

    def test_weighted_average_interest_rate_calculation(self):
        """Test Weighted Average Interest Rate calculation."""
        # Create test nodes
        interest_payments = FinancialStatementItemNode("interest_payments", {"2023": 500_000})
        total_debt = FinancialStatementItemNode("total_debt", {"2023": 10_000_000})

        # Get WAIR metric definition
        wair_metric = metric_registry.get("weighted_average_interest_rate")

        # Create calculation node
        wair_node = FormulaCalculationNode(
            "wair_test",
            inputs={"interest_payments": interest_payments, "total_debt": total_debt},
            formula=wair_metric.formula,
        )

        # Test calculation
        result = wair_node.calculate("2023")
        expected = (500_000 / 10_000_000) * 100  # 5.0%
        assert result == expected

    def test_debt_maturity_profile_calculation(self):
        """Test Debt Maturity Profile calculation."""
        # Create test nodes
        near_term_debt = FinancialStatementItemNode("debt_maturities_1_year", {"2023": 1_500_000})
        total_debt = FinancialStatementItemNode("total_debt", {"2023": 10_000_000})

        # Get debt maturity profile metric definition
        dmp_metric = metric_registry.get("debt_maturity_profile")

        # Create calculation node
        dmp_node = FormulaCalculationNode(
            "dmp_test",
            inputs={"debt_maturities_1_year": near_term_debt, "total_debt": total_debt},
            formula=dmp_metric.formula,
        )

        # Test calculation
        result = dmp_node.calculate("2023")
        expected = (1_500_000 / 10_000_000) * 100  # 15%
        assert result == expected

    def test_construction_loan_to_cost_ratio_calculation(self):
        """Test Construction Loan to Cost Ratio calculation."""
        # Create test nodes
        construction_loans = FinancialStatementItemNode("construction_loans", {"2023": 8_000_000})
        costs_to_date = FinancialStatementItemNode("development_costs_to_date", {"2023": 6_000_000})
        remaining_budget = FinancialStatementItemNode(
            "remaining_development_budget", {"2023": 4_000_000}
        )

        # Get construction LTC metric definition
        cltc_metric = metric_registry.get("construction_loan_to_cost_ratio")

        # Create calculation node
        cltc_node = FormulaCalculationNode(
            "cltc_test",
            inputs={
                "construction_loans": construction_loans,
                "development_costs_to_date": costs_to_date,
                "remaining_development_budget": remaining_budget,
            },
            formula=cltc_metric.formula,
        )

        # Test calculation
        result = cltc_node.calculate("2023")
        expected = (8_000_000 / (6_000_000 + 4_000_000)) * 100  # 80%
        assert result == expected

    def test_debt_yield_calculation(self):
        """Test Debt Yield calculation."""
        # Create test nodes
        noi = FinancialStatementItemNode("net_operating_income", {"2023": 1_000_000})
        total_debt = FinancialStatementItemNode("total_debt", {"2023": 10_000_000})

        # Get debt yield metric definition
        dy_metric = metric_registry.get("debt_yield")

        # Create calculation node
        dy_node = FormulaCalculationNode(
            "dy_test",
            inputs={"net_operating_income": noi, "total_debt": total_debt},
            formula=dy_metric.formula,
        )

        # Test calculation
        result = dy_node.calculate("2023")
        expected = (1_000_000 / 10_000_000) * 100  # 10%
        assert result == expected

    def test_debt_metric_interpretations(self):
        """Test that real estate debt metrics have proper interpretation guidelines."""
        # Test metrics that should have interpretation guidelines
        metrics_with_interpretations = [
            "loan_to_value_ratio",
            "debt_service_coverage_ratio_(real_estate)",
            "interest_coverage_ratio_(real_estate)",
            "unencumbered_asset_ratio",
            "fixed_rate_debt_percentage",
            "debt_maturity_profile",
            "construction_loan_to_cost_ratio",
            "debt_yield",
        ]

        for metric_name in metrics_with_interpretations:
            metric = metric_registry.get(metric_name)
            assert metric.interpretation is not None, f"Metric {metric_name} missing interpretation"
            assert metric.interpretation.notes is not None, (
                f"Metric {metric_name} missing interpretation notes"
            )

    def test_debt_metric_categories(self):
        """Test that debt metrics are properly categorized."""
        debt_metrics = [
            m
            for m in metric_registry.list_metrics()
            if "real_estate_debt" in metric_registry.get(m).category
        ]

        # Ensure all debt metrics have the correct category
        for metric_name in debt_metrics:
            metric = metric_registry.get(metric_name)
            assert metric.category == "real_estate_debt", (
                f"Metric {metric_name} has wrong category: {metric.category}"
            )

    def test_debt_metric_tags(self):
        """Test that debt metrics have appropriate tags."""
        debt_metrics = [
            "loan_to_value_ratio",
            "debt_service_coverage_ratio_(real_estate)",
            "debt_yield",
        ]

        for metric_name in debt_metrics:
            metric = metric_registry.get(metric_name)
            assert "real_estate" in metric.tags, f"Metric {metric_name} missing 'real_estate' tag"
            assert len(metric.tags) > 1, f"Metric {metric_name} should have multiple tags"
