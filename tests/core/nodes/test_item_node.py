import pytest
from fin_statement_model.core.nodes.item_node import FinancialStatementItemNode


def test_calculate_and_set_value():
    data = {"2022": 100.0, "2023": 150.0}
    node = FinancialStatementItemNode("revenue", data)
    # existing data
    assert node.calculate("2022") == 100.0
    assert node.calculate("2023") == 150.0
    # missing period returns 0.0
    assert node.calculate("2021") == 0.0
    # set new value
    node.set_value("2024", 200.0)
    assert node.calculate("2024") == 200.0


def test_to_dict_and_from_dict_success():
    values = {"FY": 500.0}
    node = FinancialStatementItemNode("item", values)
    node_dict = node.to_dict()
    assert node_dict["type"] == "financial_statement_item"
    assert node_dict["name"] == "item"
    assert node_dict["values"] == values

    new_node = FinancialStatementItemNode.from_dict(node_dict)
    assert isinstance(new_node, FinancialStatementItemNode)
    assert new_node.name == "item"
    assert new_node.values == values


def test_from_dict_invalid_type_or_missing_fields():
    # wrong type
    with pytest.raises(ValueError):
        FinancialStatementItemNode.from_dict({"type": "wrong"})
    # missing name
    with pytest.raises(ValueError):
        FinancialStatementItemNode.from_dict(
            {"type": "financial_statement_item", "values": {}}
        )
    # values not a dict
    with pytest.raises(TypeError):
        FinancialStatementItemNode.from_dict(
            {"type": "financial_statement_item", "name": "n", "values": "notadict"}
        )
