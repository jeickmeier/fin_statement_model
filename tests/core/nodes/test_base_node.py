import pytest
from fin_statement_model.core.nodes.base import Node


class DummyNode(Node):
    def calculate(self, period: str) -> float:
        return 42.0

    def to_dict(self) -> dict:
        return {"type": "dummy", "name": self.name}


def test_node_name_validation():
    # valid name
    dn = DummyNode("valid")
    assert dn.name == "valid"
    # empty name
    with pytest.raises(ValueError):
        DummyNode("")
    # whitespace around name
    with pytest.raises(ValueError):
        DummyNode(" bad")
    with pytest.raises(ValueError):
        DummyNode("bad ")
    # invalid characters
    with pytest.raises(ValueError):
        DummyNode("bad\nname")
    with pytest.raises(ValueError):
        DummyNode("bad\tname")


def test_attribute_methods_and_set_value_error():
    dn = DummyNode("test")
    # has_attribute
    assert dn.has_attribute("name")
    assert not dn.has_attribute("nonexistent")
    # get_attribute
    assert dn.get_attribute("name") == "test"
    with pytest.raises(AttributeError):
        dn.get_attribute("unknown")
    # set_value not implemented
    with pytest.raises(NotImplementedError):
        dn.set_value("p", 1.0)


def test_to_dict_and_get_dependencies_with_stub():
    dn = DummyNode("node")
    # to_dict returns stub implementation
    d = dn.to_dict()
    assert isinstance(d, dict)
    assert d.get("type") == "dummy"
    assert d.get("name") == "node"
    # get_dependencies default
    assert dn.get_dependencies() == []
