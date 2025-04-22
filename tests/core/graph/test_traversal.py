"""Tests for the GraphTraversalMixin."""

import pytest
from unittest.mock import MagicMock
from typing import Dict

from fin_statement_model.core.nodes.base import Node
from fin_statement_model.core.errors import NodeError

# Mixin under test
from fin_statement_model.core.graph.traversal import GraphTraversalMixin

# --- Helper Test Host Class ---


class HostTraversalGraph(GraphTraversalMixin):
    """Minimal host class to test the GraphTraversalMixin."""

    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        # Mock methods expected by the mixin
        self.get_node = lambda name: self._nodes.get(name)
        self.has_node = lambda name: name in self._nodes

    # Define the nodes property expected by the mixin
    @property
    def nodes(self) -> Dict[str, Node]:
        return self._nodes


# --- Fixtures ---


@pytest.fixture
def host_graph() -> HostTraversalGraph:
    """Provides an instance of the test host class."""
    return HostTraversalGraph()


@pytest.fixture
def simple_nodes() -> Dict[str, MagicMock]:
    """Creates a set of simple mock nodes."""
    nodes = {}
    for name in ["A", "B", "C", "D", "E", "F"]:
        node = MagicMock(spec=Node)
        node.name = name
        node.has_calculation.return_value = False
        node.inputs = []  # Default: no inputs
        nodes[name] = node
    return nodes


# --- Test Cases ---


def test_topological_sort_linear(
    host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]
):
    """Test topological sort for a simple linear graph A -> B -> C."""
    # Setup dependencies: C depends on B, B depends on A
    simple_nodes["C"].inputs = [simple_nodes["B"]]
    simple_nodes["B"].inputs = [simple_nodes["A"]]
    host_graph._nodes = {"A": simple_nodes["A"], "B": simple_nodes["B"], "C": simple_nodes["C"]}

    order = host_graph.topological_sort()
    assert order == ["A", "B", "C"]


def test_topological_sort_diamond(
    host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]
):
    """Test topological sort for a diamond shape: A -> B, A -> C, B -> D, C -> D."""
    # Setup dependencies
    simple_nodes["D"].inputs = [simple_nodes["B"], simple_nodes["C"]]
    simple_nodes["B"].inputs = [simple_nodes["A"]]
    simple_nodes["C"].inputs = [simple_nodes["A"]]
    host_graph._nodes = {
        "A": simple_nodes["A"],
        "B": simple_nodes["B"],
        "C": simple_nodes["C"],
        "D": simple_nodes["D"],
    }

    order = host_graph.topological_sort()
    # Valid orders: [A, B, C, D] or [A, C, B, D]
    assert order[0] == "A"
    assert order[-1] == "D"
    assert set(order) == {"A", "B", "C", "D"}
    # Check relative order of dependencies
    assert order.index("B") < order.index("D")
    assert order.index("C") < order.index("D")


def test_topological_sort_multiple_roots(
    host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]
):
    """Test topological sort with multiple independent roots."""
    # A -> C, B -> C, D -> F, E -> F
    simple_nodes["C"].inputs = [simple_nodes["A"], simple_nodes["B"]]
    simple_nodes["F"].inputs = [simple_nodes["D"], simple_nodes["E"]]
    host_graph._nodes = simple_nodes

    order = host_graph.topological_sort()
    assert len(order) == 6
    assert set(order) == {"A", "B", "C", "D", "E", "F"}
    # Check dependencies are met
    assert order.index("A") < order.index("C")
    assert order.index("B") < order.index("C")
    assert order.index("D") < order.index("F")
    assert order.index("E") < order.index("F")


def test_topological_sort_cycle(host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]):
    """Test topological sort raises ValueError on cycle detection."""
    # A -> B -> C -> A
    simple_nodes["A"].inputs = [simple_nodes["C"]]
    simple_nodes["B"].inputs = [simple_nodes["A"]]
    simple_nodes["C"].inputs = [simple_nodes["B"]]
    host_graph._nodes = {"A": simple_nodes["A"], "B": simple_nodes["B"], "C": simple_nodes["C"]}

    with pytest.raises(ValueError, match="Cycle detected in graph"):
        host_graph.topological_sort()


def test_get_calculation_nodes(host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]):
    """Test retrieving calculation nodes."""
    simple_nodes["A"].has_calculation.return_value = False
    simple_nodes["B"].has_calculation.return_value = True
    simple_nodes["C"].has_calculation.return_value = True
    host_graph._nodes = {"A": simple_nodes["A"], "B": simple_nodes["B"], "C": simple_nodes["C"]}

    calc_nodes = host_graph.get_calculation_nodes()
    assert set(calc_nodes) == {"B", "C"}


def test_get_dependencies_exists(
    host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]
):
    """Test getting dependencies for a node that has them."""
    simple_nodes["C"].inputs = [simple_nodes["A"], simple_nodes["B"]]
    host_graph._nodes = {"A": simple_nodes["A"], "B": simple_nodes["B"], "C": simple_nodes["C"]}

    deps = host_graph.get_dependencies("C")
    assert set(deps) == {"A", "B"}


def test_get_dependencies_no_inputs_attr(
    host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]
):
    """Test getting dependencies for a node without an 'inputs' attribute."""
    del simple_nodes["A"].inputs  # Remove attribute
    host_graph._nodes = {"A": simple_nodes["A"]}
    deps = host_graph.get_dependencies("A")
    assert deps == []


def test_get_dependencies_no_deps(
    host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]
):
    """Test getting dependencies for a node with no dependencies."""
    simple_nodes["A"].inputs = []
    host_graph._nodes = {"A": simple_nodes["A"]}
    deps = host_graph.get_dependencies("A")
    assert deps == []


def test_get_dependencies_node_not_found(host_graph: HostTraversalGraph):
    """Test getting dependencies raises NodeError if node doesn't exist."""
    with pytest.raises(NodeError, match="Node 'NonExistent' does not exist"):
        host_graph.get_dependencies("NonExistent")


def test_get_dependency_graph(host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]):
    """Test constructing the full dependency graph."""
    # A -> C, B -> C
    simple_nodes["C"].inputs = [simple_nodes["A"], simple_nodes["B"]]
    simple_nodes["A"].inputs = []
    simple_nodes["B"].inputs = []
    host_graph._nodes = {"A": simple_nodes["A"], "B": simple_nodes["B"], "C": simple_nodes["C"]}

    dep_graph = host_graph.get_dependency_graph()
    expected = {"A": [], "B": [], "C": ["A", "B"]}
    assert dep_graph == expected


def test_detect_cycles_no_cycle(host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]):
    """Test cycle detection when there are no cycles."""
    # A -> B -> C
    simple_nodes["C"].inputs = [simple_nodes["B"]]
    simple_nodes["B"].inputs = [simple_nodes["A"]]
    host_graph._nodes = {"A": simple_nodes["A"], "B": simple_nodes["B"], "C": simple_nodes["C"]}

    cycles = host_graph.detect_cycles()
    assert cycles == []


def test_detect_cycles_simple_cycle(
    host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]
):
    """Test detection of a simple cycle A -> B -> C -> A."""
    simple_nodes["A"].inputs = [simple_nodes["C"]]
    simple_nodes["B"].inputs = [simple_nodes["A"]]
    simple_nodes["C"].inputs = [simple_nodes["B"]]
    host_graph._nodes = {"A": simple_nodes["A"], "B": simple_nodes["B"], "C": simple_nodes["C"]}

    cycles = host_graph.detect_cycles()
    assert len(cycles) == 1
    # Order might vary depending on traversal start
    assert set(cycles[0]) == {"A", "B", "C"}
    # Check structure A->B->C->A (or permutation)
    assert cycles[0][-1] == cycles[0][0]  # Check loop back
    assert len(cycles[0]) == 4  # A, B, C, A


def test_detect_cycles_self_loop(
    host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]
):
    """Test detection of a self-loop A -> A."""
    simple_nodes["A"].inputs = [simple_nodes["A"]]
    host_graph._nodes = {"A": simple_nodes["A"]}

    cycles = host_graph.detect_cycles()
    assert cycles == [["A", "A"]]


def test_detect_cycles_multiple_cycles(
    host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]
):
    """Test detection of multiple cycles."""
    # Cycle 1: A -> B -> A
    simple_nodes["A"].inputs = [simple_nodes["B"]]
    simple_nodes["B"].inputs = [simple_nodes["A"]]
    # Cycle 2: C -> D -> C
    simple_nodes["C"].inputs = [simple_nodes["D"]]
    simple_nodes["D"].inputs = [simple_nodes["C"]]
    # Connect them: B -> C
    simple_nodes["C"].inputs.append(simple_nodes["B"])  # C now depends on B and D

    host_graph._nodes = {
        "A": simple_nodes["A"],
        "B": simple_nodes["B"],
        "C": simple_nodes["C"],
        "D": simple_nodes["D"],
    }

    cycles = host_graph.detect_cycles()
    assert len(cycles) >= 2  # Might detect overlapping paths differently
    # Check that both core cycles are represented
    found_ab = any(set(c) == {"A", "B"} for c in cycles)
    found_cd = any(set(c) == {"C", "D"} for c in cycles)
    assert found_ab
    assert found_cd


def test_validate_valid_graph(host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]):
    """Test validation returns no errors for a valid graph."""
    # A -> B -> C
    simple_nodes["C"].inputs = [simple_nodes["B"]]
    simple_nodes["B"].inputs = [simple_nodes["A"]]
    host_graph._nodes = {"A": simple_nodes["A"], "B": simple_nodes["B"], "C": simple_nodes["C"]}
    errors = host_graph.validate()
    assert errors == []


def test_validate_cycle_error(host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]):
    """Test validation detects and reports cycles."""
    # A -> B -> A
    simple_nodes["A"].inputs = [simple_nodes["B"]]
    simple_nodes["B"].inputs = [simple_nodes["A"]]
    host_graph._nodes = {"A": simple_nodes["A"], "B": simple_nodes["B"]}
    errors = host_graph.validate()
    assert len(errors) == 1
    assert (
        "Circular dependency detected: B -> A -> B" in errors
        or "Circular dependency detected: A -> B -> A" in errors
    )


def test_validate_missing_dependency(
    host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]
):
    """Test validation detects missing dependencies."""
    # B depends on MissingNode
    missing_node_ref = MagicMock(spec=Node)
    missing_node_ref.name = "MissingNode"
    simple_nodes["B"].inputs = [missing_node_ref]
    host_graph._nodes = {"B": simple_nodes["B"]}

    errors = host_graph.validate()
    assert len(errors) == 1
    assert errors[0] == "Node 'B' depends on non-existent node 'MissingNode'"


def test_validate_multiple_errors(
    host_graph: HostTraversalGraph, simple_nodes: Dict[str, MagicMock]
):
    """Test validation reports both cycles and missing dependencies."""
    # Cycle: A -> B -> A
    simple_nodes["A"].inputs = [simple_nodes["B"]]
    simple_nodes["B"].inputs = [simple_nodes["A"]]
    # Missing: C depends on MissingNode
    missing_node_ref = MagicMock(spec=Node)
    missing_node_ref.name = "MissingNode"
    simple_nodes["C"].inputs = [missing_node_ref]
    host_graph._nodes = {"A": simple_nodes["A"], "B": simple_nodes["B"], "C": simple_nodes["C"]}

    errors = host_graph.validate()
    assert len(errors) == 2
    # Check both types of errors are present (order might vary)
    assert any("Circular dependency detected" in e for e in errors)
    assert any("depends on non-existent node 'MissingNode'" in e for e in errors)
