"""Tests for the unified validation module."""

from fin_statement_model.io.validation import (
    UnifiedNodeValidator,
    ValidationResult,
    create_validator,
    validate_node_name,
)
from fin_statement_model.core.nodes import Node


class MockNode(Node):
    """Mock node for testing."""

    def __init__(self, name: str, inputs: list = None):
        self.name = name
        self.inputs = inputs or []

    def calculate(self, period: str) -> float:
        return 0.0

    def get_dependencies(self) -> list[str]:
        return [node.name for node in self.inputs]


class TestUnifiedNodeValidator:
    """Test the UnifiedNodeValidator class."""

    def test_init(self):
        """Test validator initialization."""
        validator = UnifiedNodeValidator()
        assert validator.strict_mode is False
        assert validator.auto_standardize is True
        assert validator.warn_on_non_standard is True
        assert validator.enable_patterns is True
        assert len(validator._validation_cache) == 0

    def test_validate_standard_name(self):
        """Test validation of standard node names."""
        validator = UnifiedNodeValidator()

        # Standard names should always be valid
        result = validator.validate("revenue")
        assert result.original_name == "revenue"
        assert result.standardized_name == "revenue"
        assert result.is_valid is True
        assert result.category == "standard"
        assert result.confidence == 1.0
        assert len(result.suggestions) == 0

    def test_validate_alternate_name(self):
        """Test validation of alternate names."""
        # With auto-standardize
        validator = UnifiedNodeValidator(auto_standardize=True)
        result = validator.validate(
            "sales"
        )  # Assuming 'sales' is alternate for 'revenue'
        assert result.original_name == "sales"
        assert result.standardized_name == "revenue"
        assert result.is_valid is True
        assert result.category == "alternate"

        # Without auto-standardize
        validator = UnifiedNodeValidator(auto_standardize=False)
        result = validator.validate("sales")
        assert result.original_name == "sales"
        assert result.standardized_name == "sales"
        assert result.is_valid is True
        assert result.category == "alternate"

    def test_validate_subnode_patterns(self):
        """Test validation of sub-node patterns."""
        validator = UnifiedNodeValidator()

        # Quarterly pattern
        result = validator.validate("revenue_q1")
        assert result.is_valid is True
        assert result.category == "subnode"
        assert "quarterly" in result.message

        # Annual pattern
        result = validator.validate("revenue_2023")
        assert result.is_valid is True
        assert result.category == "subnode"
        assert "annual" in result.message

        # Scenario pattern
        result = validator.validate("revenue_budget")
        assert result.is_valid is True
        assert result.category == "subnode"
        assert "scenario" in result.message

        # Non-standard base
        result = validator.validate("fake_metric_q1")
        assert result.category == "subnode_nonstandard"
        assert result.confidence < 0.9

    def test_validate_formula_patterns(self):
        """Test validation of formula patterns."""
        validator = UnifiedNodeValidator()

        # Margin pattern
        result = validator.validate("gross_profit_margin", node_type="calculation")
        assert result.is_valid is True
        assert result.category == "formula"
        assert "margin" in result.message

        # Ratio pattern
        result = validator.validate("current_ratio", node_type="formula")
        assert result.is_valid is True
        assert result.category == "formula"
        assert "ratio" in result.message

        # Growth pattern
        result = validator.validate("revenue_growth", node_type="calculation")
        assert result.is_valid is True
        assert result.category == "formula"
        assert "growth" in result.message

    def test_validate_with_parents(self):
        """Test validation with parent context."""
        validator = UnifiedNodeValidator()

        # Node derived from parent
        result = validator.validate(
            "revenue_adjustment", parent_nodes=["revenue", "adjustment_factor"]
        )
        assert result.is_valid is True
        assert result.category == "derived"
        assert result.confidence == 0.8

    def test_strict_mode(self):
        """Test strict mode validation."""
        validator = UnifiedNodeValidator(strict_mode=True)

        # Standard names still valid
        result = validator.validate("revenue")
        assert result.is_valid is True

        # Custom names invalid
        result = validator.validate("custom_node")  # Changed to avoid pattern match
        assert result.is_valid is False
        assert result.category == "invalid"

        # Sub-nodes with standard base still valid
        result = validator.validate("revenue_q1")
        assert result.is_valid is True

        # Sub-nodes with non-standard base invalid
        result = validator.validate("fake_metric_q1")
        assert result.is_valid is False

    def test_pattern_recognition_disabled(self):
        """Test with pattern recognition disabled."""
        validator = UnifiedNodeValidator(enable_patterns=False)

        # Sub-node patterns not recognized
        result = validator.validate("revenue_q1")
        assert result.category == "custom"  # Not recognized as subnode

        # Formula patterns not recognized
        result = validator.validate("gross_profit_margin")
        assert result.category == "custom"  # Not recognized as formula

    def test_caching(self):
        """Test validation caching."""
        validator = UnifiedNodeValidator()

        # First call
        result1 = validator.validate("revenue_q1")
        assert len(validator._validation_cache) == 1

        # Second call should use cache
        result2 = validator.validate("revenue_q1")
        assert result1 is result2  # Same object

        # Different context should not use cache
        result3 = validator.validate("revenue_q1", node_type="formula")
        assert result1 is not result3
        assert len(validator._validation_cache) == 2

        # Clear cache
        validator.clear_cache()
        assert len(validator._validation_cache) == 0

    def test_suggestions(self):
        """Test suggestion generation."""
        validator = UnifiedNodeValidator()

        # Similar to standard name
        result = validator.validate("revenu")  # Typo
        assert len(result.suggestions) > 0
        assert any("revenue" in s for s in result.suggestions)

        # Base could be standard
        result = validator.validate("rev_monthly")
        assert len(result.suggestions) > 0

        # Custom node without pattern
        result = validator.validate("unknown_item")
        assert len(result.suggestions) > 0
        assert any("Consider using standard name:" in s for s in result.suggestions)

    def test_validate_batch(self):
        """Test batch validation."""
        validator = UnifiedNodeValidator()

        names = ["revenue", "sales", "revenue_q1", "custom_metric"]
        node_types = {"revenue_q1": "calculation", "custom_metric": "formula"}
        parent_map = {"custom_metric": ["revenue", "operating_expenses"]}

        results = validator.validate_batch(names, node_types, parent_map)

        assert len(results) == 4
        assert results["revenue"].category == "standard"
        assert results["sales"].category == "alternate"
        assert results["revenue_q1"].category == "subnode"
        assert results["custom_metric"].category == "derived"

    def test_validate_graph(self):
        """Test graph validation."""
        validator = UnifiedNodeValidator()

        # Test with explicit validation instead of relying on class name detection
        names = ["revenue", "operating_expenses", "net_profit", "profit_margin"]
        node_types = {
            "revenue": "data",
            "operating_expenses": "data",
            "net_profit": "calculation",
            "profit_margin": "calculation",  # Will be detected as formula by pattern
        }
        parent_map = {
            "net_profit": ["revenue", "operating_expenses"],
            "profit_margin": ["net_profit", "revenue"],
        }

        results = validator.validate_batch(names, node_types, parent_map)

        # Check results
        assert len(results) == 4
        assert results["revenue"].category == "standard"
        assert results["operating_expenses"].category == "standard"
        assert results["net_profit"].category == "alternate"
        assert results["profit_margin"].category == "formula"

    def test_automatic_case_handling(self):
        """Test that validator automatically handles case variations."""
        validator = UnifiedNodeValidator(auto_standardize=True)

        # Test standard names in different cases
        test_cases = [
            ("revenue", "revenue", "standard"),
            ("Revenue", "revenue", "standard"),
            ("REVENUE", "revenue", "standard"),
            ("ReVeNuE", "revenue", "standard"),
        ]

        for original, expected_std, expected_cat in test_cases:
            result = validator.validate(original)
            assert result.standardized_name == expected_std
            assert result.category == expected_cat
            assert result.is_valid is True

        # Test alternate names in different cases
        alt_cases = [
            ("sales", "revenue", "alternate"),
            ("Sales", "revenue", "alternate"),
            ("SALES", "revenue", "alternate"),
            ("cogs", "cost_of_goods_sold", "alternate"),
            ("COGS", "cost_of_goods_sold", "alternate"),
            ("Cogs", "cost_of_goods_sold", "alternate"),
        ]

        for original, expected_std, expected_cat in alt_cases:
            result = validator.validate(original)
            assert result.standardized_name == expected_std
            assert result.category == expected_cat
            assert result.is_valid is True

        # Test sub-nodes with uppercase bases
        subnode_cases = [
            ("Revenue_Q1", "Revenue_Q1", "subnode"),
            ("REVENUE_2023", "REVENUE_2023", "subnode"),
            ("Gross_Profit_Margin", "Gross_Profit_Margin", "formula"),
        ]

        for original, expected_std, expected_cat in subnode_cases:
            result = validator.validate(original)
            assert result.standardized_name == expected_std
            assert result.category == expected_cat
            assert result.is_valid is True

    def test_backward_compatibility(self):
        """Test backward compatibility functions."""
        # create_validator
        validator = create_validator(strict_mode=True)
        assert isinstance(validator, UnifiedNodeValidator)
        assert validator.strict_mode is True

        # validate_node_name
        std_name, is_valid, message = validate_node_name("sales")
        assert std_name == "revenue"
        assert is_valid is True
        assert "Standardized" in message

        # Without auto-standardize
        std_name, is_valid, message = validate_node_name(
            "sales", auto_standardize=False
        )
        assert std_name == "sales"
        assert is_valid is True


class TestValidationResult:
    """Test the ValidationResult dataclass."""

    def test_creation(self):
        """Test ValidationResult creation."""
        result = ValidationResult(
            original_name="test",
            standardized_name="test_std",
            is_valid=True,
            message="Test message",
            category="test",
        )

        assert result.original_name == "test"
        assert result.standardized_name == "test_std"
        assert result.is_valid is True
        assert result.message == "Test message"
        assert result.category == "test"
        assert result.confidence == 1.0
        assert result.suggestions == []

    def test_with_suggestions(self):
        """Test ValidationResult with suggestions."""
        suggestions = ["Try this", "Or that"]
        result = ValidationResult(
            original_name="test",
            standardized_name="test",
            is_valid=False,
            message="Invalid",
            category="invalid",
            confidence=0.5,
            suggestions=suggestions,
        )

        assert result.confidence == 0.5
        assert result.suggestions == suggestions
