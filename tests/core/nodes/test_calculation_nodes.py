import pytest

from fin_statement_model.core.nodes import (
    CalculationNode,
    FormulaCalculationNode,
    CustomCalculationNode,
    is_calculation_node,
)
from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode


class SumCalculation:
    def calculate(self, inputs, period):
        return sum(node.calculate(period) for node in inputs)


def test_calculation_node_basic_and_caching():
    a = FinancialStatementItemNode("a", {"p": 1.0})
    b = FinancialStatementItemNode("b", {"p": 2.0})
    calc = SumCalculation()
    node = CalculationNode("sum", [a, b], calc)
    # initial calculate
    assert node.calculate("p") == 3.0
    # cached
    assert node._values["p"] == 3.0
    # change input and clear cache
    a.set_value("p", 5.0)
    node.clear_cache()
    assert node.calculate("p") == 7.0
    # dependencies
    assert node.get_dependencies() == ["a", "b"]

    # to_dict contains calculation_type_class
    d = node.to_dict()
    assert d["type"] == "calculation"
    assert "calculation_type_class" in d

    # change underlying calculation via set_calculation
    class ProdCalc:
        def calculate(self, inputs, period):
            return inputs[0].calculate(period) * inputs[1].calculate(period)

    prod_calc = ProdCalc()
    node.set_calculation(prod_calc)
    # cache cleared and calculation updated
    assert node.calculate("p") == pytest.approx(10.0)


def test_formula_calculation_node_and_roundtrip():
    a = FinancialStatementItemNode("a", {"2023": 10})
    b = FinancialStatementItemNode("b", {"2023": 4})
    fnode = FormulaCalculationNode("diff", inputs={"x": a, "y": b}, formula="x - y")
    assert fnode.calculate("2023") == 6.0
    # clear cache
    a.set_value("2023", 20)
    fnode.clear_cache()
    assert fnode.calculate("2023") == 16.0

    # to_dict includes formula details and roundtrip
    d = fnode.to_dict()
    assert d["type"] == "formula_calculation"
    assert d.get("calculation_type") == "formula"
    assert d.get("formula") == "x - y"
    assert d.get("formula_variable_names") == ["x", "y"]
    # recreate via from_dict
    context = {"a": a, "b": b}
    new_fnode = FormulaCalculationNode.from_dict_with_context(d, context)
    assert isinstance(new_fnode, FormulaCalculationNode)
    assert new_fnode.calculate("2023") == pytest.approx(16.0)


def test_custom_calculation_node_and_errors():
    a = FinancialStatementItemNode("a", {"z": 3})
    b = FinancialStatementItemNode("b", {"z": 4})

    def mul(x, y):
        return x * y

    # non-list inputs
    with pytest.raises(TypeError):
        CustomCalculationNode("c", "notalist", mul)
    # non-callable formula_func
    with pytest.raises(TypeError):
        CustomCalculationNode("c", [a, b], "notcallable")

    node = CustomCalculationNode("c", [a, b], mul)
    assert node.calculate("z") == 12.0
    # caching and clear
    a.set_value("z", 5)
    node.clear_cache()
    assert node.calculate("z") == 20.0

    d = node.to_dict()
    assert d["type"] == "custom_calculation"
    assert "serialization_warning" in d
    # roundtrip creation not supported: from_dict absent
    assert not hasattr(CustomCalculationNode, "from_dict_with_context")


def test_is_calculation_node_helper():
    a = FinancialStatementItemNode("a", {"p": 1})
    # data node
    assert not is_calculation_node(a)
    # formula node
    fnode = FormulaCalculationNode("f", {"x": a}, formula="x * 2")
    assert is_calculation_node(fnode)
    # custom calc node
    cnode = CustomCalculationNode("c", [a], lambda x: x)
    assert is_calculation_node(cnode)
    # forecast node
    from fin_statement_model.core.nodes.forecast_nodes import FixedGrowthForecastNode

    fc = FixedGrowthForecastNode(a, "p", [])
    assert is_calculation_node(fc)
    # stats node
    from fin_statement_model.core.nodes.stats_nodes import YoYGrowthNode

    st = YoYGrowthNode("y", a, "p", "p")
    assert is_calculation_node(st)
    # Prepare another node for from_dict context
    b = FinancialStatementItemNode("b", {"p": 2})
    # Test CalculatorNode.from_dict_with_context for formula type
    # Create formula node dict
    fdict = {
        "type": "calculation",
        "name": "sum2",
        "inputs": ["a", "b"],
        "calculation_type": "formula",
        "formula_variable_names": ["a", "b"],
        "calculation_args": {"formula": "a + b"},
    }
    from fin_statement_model.core.nodes.calculation_nodes import CalculationNode

    context = {"a": a, "b": b}
    sum2 = CalculationNode.from_dict_with_context(fdict, context)
    assert isinstance(sum2, CalculationNode)
    assert sum2.calculate("p") == pytest.approx(a.calculate("p") + b.calculate("p"))


def test_calculation_node_error_cases():
    a = FinancialStatementItemNode("a", {"t": 1.0})
    # invalid inputs not list
    with pytest.raises(TypeError):
        CalculationNode("n", "notalist", SumCalculation())
    # calculation object missing calculate method
    with pytest.raises(TypeError):
        CalculationNode("n", [a], object())
    # initial valid case to ensure no error
    calc = SumCalculation()
    node = CalculationNode("sum", [a], calc)
    assert node.calculate("t") == 1.0
