"""Unit tests for the calculation_strategy module.

This module contains tests for the various calculation strategies
that are used to perform different operations on financial data.
"""
import pytest
from unittest.mock import Mock, patch
import inspect

from fin_statement_model.calculations.calculation_strategy import (
    CalculationStrategy,
    AdditionStrategy,
    SubtractionStrategy,
    MultiplicationStrategy,
    DivisionStrategy,
    WeightedAverageStrategy,
    CustomFormulaStrategy
)


class TestCalculationStrategy:
    """Tests for the abstract CalculationStrategy base class."""
    
    def test_line_41_direct_coverage(self):
        """Directly test line 41 in calculation_strategy.py.
        
        This test uses a specialized technique to directly execute line 41
        independently of other code.
        """
        # Create a concrete subclass that we can control
        class DirectTestStrategy(CalculationStrategy):
            def calculate(self, inputs, period):
                return 0.0
                
            # Override property getter directly to force line 41 testing
            @property
            def description(self):
                # This directly calls the original description getter
                # which should cover line 41: return self.__class__.__name__
                return CalculationStrategy.description.fget(self)
                
        # Create an instance with a known class name
        strategy = DirectTestStrategy()
        
        # The description should use our class name through line 41
        assert strategy.description == "DirectTestStrategy"
    
    def test_abstract_calculate_method(self):
        """Test that CalculationStrategy cannot be instantiated due to abstract methods."""
        with pytest.raises(TypeError):
            CalculationStrategy()
    
    def test_description_property(self):
        """Test the description property returns the class name."""
        # Create a concrete subclass for testing
        class TestStrategy(CalculationStrategy):
            def calculate(self, inputs, period):
                return 0.0
                
        strategy = TestStrategy()
        assert strategy.description == "TestStrategy"
    
    def test_base_description_property(self):
        """Test the description property directly from the base class implementation.
        
        This test specifically targets how the description property uses the class name.
        """
        # Create a subclass for testing that doesn't override description
        class SimpleTestStrategy(CalculationStrategy):
            def calculate(self, inputs, period):
                return 0.0
        
        # Create an instance
        strategy = SimpleTestStrategy()
        
        # Test the property directly
        assert strategy.description == "SimpleTestStrategy"
        
        # Additional test to ensure full coverage
        # Change the class name at runtime to verify it's using __class__.__name__
        original_name = SimpleTestStrategy.__name__
        try:
            # Temporarily change the class name
            SimpleTestStrategy.__name__ = "ModifiedTestStrategy"
            # This should use the modified class name
            assert strategy.description == "ModifiedTestStrategy"
        finally:
            # Restore the original name
            SimpleTestStrategy.__name__ = original_name


class TestAdditionStrategy:
    """Tests for the AdditionStrategy class."""
    
    @pytest.fixture
    def mock_input_nodes(self):
        """Create mock input nodes with calculate method."""
        node1 = Mock()
        node1.calculate = lambda period: 100.0 if period == "2023" else 90.0
        
        node2 = Mock()
        node2.calculate = lambda period: 50.0 if period == "2023" else 45.0
        
        node3 = Mock()
        node3.calculate = lambda period: 25.0 if period == "2023" else 22.5
        
        return [node1, node2, node3]
    
    def test_calculate_sum(self, mock_input_nodes):
        """Test that addition strategy returns sum of all inputs."""
        strategy = AdditionStrategy()
        result = strategy.calculate(mock_input_nodes, "2023")
        
        # 100 + 50 + 25 = 175
        assert result == 175.0
    
    def test_calculate_different_period(self, mock_input_nodes):
        """Test calculation with a different period."""
        strategy = AdditionStrategy()
        result = strategy.calculate(mock_input_nodes, "2022")
        
        # 90 + 45 + 22.5 = 157.5
        assert result == 157.5
    
    def test_calculate_empty_input(self):
        """Test calculation with empty input list."""
        strategy = AdditionStrategy()
        result = strategy.calculate([], "2023")
        
        # Sum of empty list is 0
        assert result == 0.0
    
    def test_description(self):
        """Test the description property returns a descriptive string."""
        strategy = AdditionStrategy()
        assert "Addition" in strategy.description
        assert "sum" in strategy.description.lower()


class TestSubtractionStrategy:
    """Tests for the SubtractionStrategy class."""
    
    @pytest.fixture
    def mock_input_nodes(self):
        """Create mock input nodes with calculate method."""
        node1 = Mock()
        node1.calculate = lambda period: 100.0 if period == "2023" else 90.0
        
        node2 = Mock()
        node2.calculate = lambda period: 50.0 if period == "2023" else 45.0
        
        node3 = Mock()
        node3.calculate = lambda period: 25.0 if period == "2023" else 22.5
        
        return [node1, node2, node3]
    
    def test_calculate_subtraction(self, mock_input_nodes):
        """Test that subtraction strategy returns first input minus subsequent inputs."""
        strategy = SubtractionStrategy()
        result = strategy.calculate(mock_input_nodes, "2023")
        
        # 100 - 50 - 25 = 25
        assert result == 25.0
    
    def test_calculate_different_period(self, mock_input_nodes):
        """Test calculation with a different period."""
        strategy = SubtractionStrategy()
        result = strategy.calculate(mock_input_nodes, "2022")
        
        # 90 - 45 - 22.5 = 22.5
        assert result == 22.5
    
    def test_calculate_single_input(self):
        """Test calculation with a single input."""
        node = Mock()
        node.calculate = lambda period: 100.0
        
        strategy = SubtractionStrategy()
        result = strategy.calculate([node], "2023")
        
        # Just return the first value
        assert result == 100.0
    
    def test_calculate_empty_input(self):
        """Test calculation with empty input list raises ValueError."""
        strategy = SubtractionStrategy()
        with pytest.raises(ValueError) as excinfo:
            strategy.calculate([], "2023")
        
        assert "requires at least one input" in str(excinfo.value).lower()
    
    def test_description(self):
        """Test the description property returns a descriptive string."""
        strategy = SubtractionStrategy()
        assert "Subtraction" in strategy.description
        assert "minus" in strategy.description.lower()


class TestMultiplicationStrategy:
    """Tests for the MultiplicationStrategy class."""
    
    @pytest.fixture
    def mock_input_nodes(self):
        """Create mock input nodes with calculate method."""
        node1 = Mock()
        node1.calculate = lambda period: 10.0 if period == "2023" else 9.0
        
        node2 = Mock()
        node2.calculate = lambda period: 5.0 if period == "2023" else 4.5
        
        node3 = Mock()
        node3.calculate = lambda period: 2.0 if period == "2023" else 2.0
        
        return [node1, node2, node3]
    
    def test_calculate_multiplication(self, mock_input_nodes):
        """Test that multiplication strategy returns product of all inputs."""
        strategy = MultiplicationStrategy()
        result = strategy.calculate(mock_input_nodes, "2023")
        
        # 10 * 5 * 2 = 100
        assert result == 100.0
    
    def test_calculate_different_period(self, mock_input_nodes):
        """Test calculation with a different period."""
        strategy = MultiplicationStrategy()
        result = strategy.calculate(mock_input_nodes, "2022")
        
        # 9 * 4.5 * 2 = 81
        assert result == 81.0
    
    def test_calculate_single_input(self):
        """Test calculation with a single input."""
        node = Mock()
        node.calculate = lambda period: 10.0
        
        strategy = MultiplicationStrategy()
        result = strategy.calculate([node], "2023")
        
        # Just return the first value
        assert result == 10.0
    
    def test_calculate_empty_input(self):
        """Test calculation with empty input list raises ValueError."""
        strategy = MultiplicationStrategy()
        with pytest.raises(ValueError) as excinfo:
            strategy.calculate([], "2023")
        
        assert "requires at least one input" in str(excinfo.value).lower()
    
    def test_description(self):
        """Test the description property returns a descriptive string."""
        strategy = MultiplicationStrategy()
        assert "Multiplication" in strategy.description
        assert "product" in strategy.description.lower()


class TestDivisionStrategy:
    """Tests for the DivisionStrategy class."""
    
    @pytest.fixture
    def mock_input_nodes(self):
        """Create mock input nodes with calculate method."""
        node1 = Mock()
        node1.calculate = lambda period: 100.0 if period == "2023" else 90.0
        
        node2 = Mock()
        node2.calculate = lambda period: 5.0 if period == "2023" else 4.5
        
        node3 = Mock()
        node3.calculate = lambda period: 2.0 if period == "2023" else 2.0
        
        return [node1, node2, node3]
    
    def test_calculate_division(self, mock_input_nodes):
        """Test that division strategy returns first input divided by subsequent inputs."""
        strategy = DivisionStrategy()
        result = strategy.calculate(mock_input_nodes, "2023")
        
        # 100 / 5 / 2 = 10
        assert result == 10.0
    
    def test_calculate_different_period(self, mock_input_nodes):
        """Test calculation with a different period."""
        strategy = DivisionStrategy()
        result = strategy.calculate(mock_input_nodes, "2022")
        
        # 90 / 4.5 / 2 = 10
        assert result == 10.0
    
    def test_calculate_single_input(self):
        """Test calculation with a single input raises ValueError."""
        node = Mock()
        node.calculate = lambda period: 100.0
        
        strategy = DivisionStrategy()
        with pytest.raises(ValueError) as excinfo:
            strategy.calculate([node], "2023")
        
        assert "requires at least two input" in str(excinfo.value).lower()
    
    def test_calculate_empty_input(self):
        """Test calculation with empty input list raises ValueError."""
        strategy = DivisionStrategy()
        with pytest.raises(ValueError) as excinfo:
            strategy.calculate([], "2023")
        
        assert "requires at least two input" in str(excinfo.value).lower()

    def test_division_by_zero(self):
        """Test that division by zero raises ZeroDivisionError."""
        node1 = Mock()
        node1.calculate = lambda period: 100.0
        
        node2 = Mock()
        node2.calculate = lambda period: 0.0  # Will cause division by zero
        
        strategy = DivisionStrategy()
        with pytest.raises(ZeroDivisionError) as excinfo:
            strategy.calculate([node1, node2], "2023")
            
        assert "division by zero" in str(excinfo.value).lower()
    
    def test_description(self):
        """Test the description property returns a descriptive string."""
        strategy = DivisionStrategy()
        assert "Division" in strategy.description
        assert "divided" in strategy.description.lower()


class TestWeightedAverageStrategy:
    """Tests for the WeightedAverageStrategy class."""
    
    @pytest.fixture
    def mock_input_nodes(self):
        """Create mock input nodes with calculate method."""
        node1 = Mock()
        node1.calculate = lambda period: 100.0 if period == "2023" else 90.0
        
        node2 = Mock()
        node2.calculate = lambda period: 50.0 if period == "2023" else 45.0
        
        node3 = Mock()
        node3.calculate = lambda period: 25.0 if period == "2023" else 22.5
        
        return [node1, node2, node3]
    
    def test_calculate_equal_weights(self, mock_input_nodes):
        """Test weighted average with equal weights (default)."""
        strategy = WeightedAverageStrategy()  # No weights, defaults to equal
        result = strategy.calculate(mock_input_nodes, "2023")
        
        # (100 + 50 + 25) / 3 = 58.33...
        assert result == pytest.approx(58.333, 0.001)
    
    def test_calculate_custom_weights(self, mock_input_nodes):
        """Test weighted average with custom weights."""
        strategy = WeightedAverageStrategy(weights=[0.5, 0.3, 0.2])
        result = strategy.calculate(mock_input_nodes, "2023")
        
        # 100*0.5 + 50*0.3 + 25*0.2 = 50 + 15 + 5 = 70
        assert result == 70.0
    
    def test_calculate_different_period(self, mock_input_nodes):
        """Test calculation with a different period."""
        strategy = WeightedAverageStrategy(weights=[0.5, 0.3, 0.2])
        result = strategy.calculate(mock_input_nodes, "2022")
        
        # 90*0.5 + 45*0.3 + 22.5*0.2 = 45 + 13.5 + 4.5 = 63
        assert result == 63.0
    
    def test_mismatched_weights(self, mock_input_nodes):
        """Test that mismatched weights and inputs raises ValueError."""
        strategy = WeightedAverageStrategy(weights=[0.5, 0.5])  # Only 2 weights for 3 inputs
        with pytest.raises(ValueError) as excinfo:
            strategy.calculate(mock_input_nodes, "2023")
        
        assert "number of weights must match" in str(excinfo.value).lower()
    
    def test_empty_inputs(self):
        """Test that empty inputs raises ValueError."""
        strategy = WeightedAverageStrategy()
        with pytest.raises(ValueError) as excinfo:
            strategy.calculate([], "2023")
            
        assert "requires at least one input" in str(excinfo.value).lower()
    
    def test_description(self):
        """Test the description property returns a descriptive string."""
        strategy = WeightedAverageStrategy()
        assert "Weighted Average" in strategy.description
        assert "weighted sum" in strategy.description.lower()


class TestCustomFormulaStrategy:
    """Tests for the CustomFormulaStrategy class."""
    
    @pytest.fixture
    def mock_input_nodes(self):
        """Create mock input nodes with calculate method and names."""
        node1 = Mock()
        node1.name = "revenue"
        node1.calculate = lambda period: 1000.0 if period == "2023" else 900.0
        
        node2 = Mock()
        node2.name = "cost"
        node2.calculate = lambda period: 600.0 if period == "2023" else 540.0
        
        node3 = Mock()
        node3.name = "tax_rate"
        node3.calculate = lambda period: 0.3 if period == "2023" else 0.25
        
        return [node1, node2, node3]
    
    def test_calculate_custom_formula(self, mock_input_nodes):
        """Test that custom formula strategy applies the provided formula."""
        # Net income formula: (revenue - cost) * (1 - tax_rate)
        def net_income_formula(values):
            return (values["revenue"] - values["cost"]) * (1 - values["tax_rate"])
        
        strategy = CustomFormulaStrategy(net_income_formula)
        result = strategy.calculate(mock_input_nodes, "2023")
        
        # (1000 - 600) * (1 - 0.3) = 400 * 0.7 = 280
        assert result == 280.0
    
    def test_calculate_different_period(self, mock_input_nodes):
        """Test calculation with a different period."""
        def net_income_formula(values):
            return (values["revenue"] - values["cost"]) * (1 - values["tax_rate"])
        
        strategy = CustomFormulaStrategy(net_income_formula)
        result = strategy.calculate(mock_input_nodes, "2022")
        
        # (900 - 540) * (1 - 0.25) = 360 * 0.75 = 270
        assert result == 270.0
    
    def test_unnamed_nodes(self):
        """Test with nodes that don't have names."""
        # Create mocks with spec to ensure they don't have the 'name' attribute
        node1 = Mock(spec=['calculate'])
        node1.calculate = lambda period: 100.0
        
        node2 = Mock(spec=['calculate'])
        node2.calculate = lambda period: 50.0
        
        # Verify the mocks don't have a name attribute
        assert not hasattr(node1, 'name')
        assert not hasattr(node2, 'name')
        
        def sum_formula(values):
            return values["input_0"] + values["input_1"]
        
        strategy = CustomFormulaStrategy(sum_formula)
        result = strategy.calculate([node1, node2], "2023")
        
        # 100 + 50 = 150
        assert result == 150.0
    
    def test_formula_error(self, mock_input_nodes):
        """Test that errors in the formula are propagated with ValueError."""
        def error_formula(values):
            # Intentionally cause a KeyError
            return values["nonexistent_key"]
        
        strategy = CustomFormulaStrategy(error_formula)
        with pytest.raises(ValueError) as excinfo:
            strategy.calculate(mock_input_nodes, "2023")
            
        assert "error in custom formula" in str(excinfo.value).lower()
    
    def test_description(self):
        """Test the description property returns a descriptive string."""
        strategy = CustomFormulaStrategy(lambda x: 0)
        assert "Custom Formula" in strategy.description
        assert "user-defined" in strategy.description.lower() 