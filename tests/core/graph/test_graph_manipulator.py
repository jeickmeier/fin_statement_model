import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.graph.manipulator import GraphManipulator
from fin_statement_model.core.errors import NodeError
from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.nodes.calculation_nodes import CalculationNode


class DummyDataNode(Node):
    """Simple data node supporting set_value / calculate for tests."""

    def __init__(self, name: str, initial: float = 0.0):
        super().__init__(name)
        self.values: dict[str, float] = {}
        if initial is not None:
            self.values["2023"] = float(initial)
        self.cache_cleared: int = 0

    def set_value(self, period: str, value: float) -> None:  # noqa: D401
        self.values[period] = float(value)

    def calculate(self, period: str) -> float:  # noqa: D401
        return self.values.get(period, 0.0)

    def clear_cache(self) -> None:  # noqa: D401
        self.cache_cleared += 1

    def to_dict(self):  # noqa: D401
        return {}

    @classmethod
    def from_dict(cls, data, context=None):  # noqa: D401
        return cls(data["name"])  # type: ignore[arg-type]


class DummyCalcNode(Node):
    """Calculation-like node exposing *input_names* so manipulator updates it."""

    def __init__(self, name: str, input_names: list[str]):
        super().__init__(name)
        self.input_names = input_names  # names to be resolved by manipulator
        self.inputs: list[Node] = []  # will be populated by manipulator
        self.cache_cleared: bool = False

    def calculate(self, period: str) -> float:  # noqa: D401
        return sum(inp.calculate(period) for inp in self.inputs)

    def clear_cache(self) -> None:  # noqa: D401
        self.cache_cleared = True

    def to_dict(self):  # noqa: D401
        return {}

    @classmethod
    def from_dict(cls, data, context=None):  # noqa: D401
        return cls(data["name"], input_names=data.get("inputs", []))


class DummyNoSetNode(Node):
    """Node without set_value implementation to trigger TypeError."""

    def calculate(self, period: str) -> float:  # noqa: D401
        return 0.0

    def to_dict(self):  # noqa: D401
        return {}

    @classmethod
    def from_dict(cls, data, context=None):  # noqa: D401
        return cls(data["name"])


def _fresh_graph() -> tuple[Graph, GraphManipulator]:
    g = Graph(periods=["2023"])
    return g, g.manipulator


# ---------------------------------------------------------------------------
# add_node & has_node behaviour
# ---------------------------------------------------------------------------


def test_add_node_replaces_existing():
    g, m = _fresh_graph()
    n1 = DummyDataNode("N", 1)
    m.add_node(n1)
    assert m.has_node("N") is True

    n2 = DummyDataNode("N", 2)
    m.add_node(n2)  # should replace silently
    assert m.get_node("N") is n2


def test_add_node_type_error():
    g, m = _fresh_graph()
    with pytest.raises(TypeError):
        m.add_node(object())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _update_calculation_nodes invoked via remove_node
# ---------------------------------------------------------------------------


def test_update_calculation_nodes_after_removal(caplog):
    g, m = _fresh_graph()
    a = DummyDataNode("A", 1)
    b = DummyDataNode("B", 2)
    calc = DummyCalcNode("C", input_names=["A", "B"])

    for nd in (a, b, calc):
        m.add_node(nd)

    # calc.inputs initially empty. After removing B the manipulator will try
    # to update calc and encounter missing B, logging an exception.
    with caplog.at_level("ERROR"):
        m.remove_node("B")

    # Since 'B' is missing, calc.inputs should remain empty but clear_cache called.
    assert calc.inputs == []
    # No cache clear expected due to NodeError
    assert calc.cache_cleared is False


# ---------------------------------------------------------------------------
# set_value branches ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


def test_set_value_happy_path():
    g, m = _fresh_graph()
    n = DummyDataNode("Data")
    m.add_node(n)
    m.set_value("Data", "2023", 99.0)
    # Value updated
    assert n.values["2023"] == 99.0
    # Graph cache cleared -> cache_cleared incremented once
    assert n.cache_cleared == 1


def test_set_value_invalid_period():
    g, m = _fresh_graph()
    n = DummyDataNode("Data")
    m.add_node(n)
    with pytest.raises(ValueError):
        m.set_value("Data", "2099", 1.0)


def test_set_value_missing_node():
    g, m = _fresh_graph()
    with pytest.raises(NodeError):
        m.set_value("Ghost", "2023", 1.0)


def test_set_value_node_without_method():
    g, m = _fresh_graph()
    n = DummyNoSetNode("NoSetter")
    m.add_node(n)
    with pytest.raises(NotImplementedError):
        m.set_value("NoSetter", "2023", 1.0)


# ---------------------------------------------------------------------------
# Additional coverage for _update_calculation_nodes, replace_node, clear caches
# ---------------------------------------------------------------------------


def test_update_calculation_nodes_success():
    g, m = _fresh_graph()
    a = DummyDataNode("A", 1)
    b = DummyDataNode("B", 2)
    calc = DummyCalcNode("C", input_names=["A", "B"])
    for nd in (a, b, calc):
        m.add_node(nd)

    # Call the internal updater directly
    m._update_calculation_nodes()

    # DummyCalcNode is not a CalculationNode, so inputs untouched.
    assert calc.inputs == []


def test_replace_node_and_clear_caches():
    g, m = _fresh_graph()
    n_old = DummyDataNode("Data", 10)
    m.add_node(n_old)

    # Replace node with a new instance of same name
    n_new = DummyDataNode("Data", 20)
    m.replace_node("Data", n_new)
    assert m.get_node("Data") is n_new

    # clear_all_caches should iterate over nodes and invoke clear_cache
    n_new.cache_cleared = 0
    m.clear_all_caches()
    assert n_new.cache_cleared == 1


def test_replace_node_name_mismatch_raises():
    g, m = _fresh_graph()
    n_old = DummyDataNode("X")
    m.add_node(n_old)
    with pytest.raises(ValueError):
        m.replace_node("X", DummyDataNode("Y"))


# ---------------------------------------------------------------------------
# Real CalculationNode to exercise successful resolution path
# ---------------------------------------------------------------------------


class _Adder:  # Simple calculation strategy
    def calculate(self, inputs, period):  # noqa: D401
        return sum(n.calculate(period) for n in inputs)


def test_update_inputs_real_calculation_node():
    g, m = _fresh_graph()
    a = DummyDataNode("A", 1)
    b = DummyDataNode("B", 2)
    calc = CalculationNode("C", inputs=[a, b], calculation=_Adder())
    # Inject input_names attr expected by manipulator
    calc.input_names = ["A", "B"]
    # Overwrite inputs to empty to ensure update repopulates
    calc.inputs = []

    for nd in (a, b, calc):
        m.add_node(nd)

    m._update_calculation_nodes()

    assert [n.name for n in calc.inputs] == ["A", "B"]  # successfully resolved
