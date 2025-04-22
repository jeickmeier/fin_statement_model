import pytest
import logging
from fin_statement_model.core.data_manager import DataManager
from fin_statement_model.core.nodes import Node, FinancialStatementItemNode


# --- Concrete Node for Testing ---


class ConcreteTestNode(Node):
    """Simple concrete Node subclass for testing abstract methods."""

    def calculate(self, period: str):
        """Dummy implementation for abstract method."""
        return 0.0  # Or any simple value


# --- Fixtures ---


@pytest.fixture
def shared_registry():
    """Provides an empty dictionary to act as the shared node registry."""
    return {}


@pytest.fixture
def data_manager(shared_registry):
    """Provides a DataManager instance initialized with the shared registry."""
    return DataManager(shared_registry)


@pytest.fixture
def simple_node():
    """Provides a basic Node instance for testing."""
    return ConcreteTestNode(name="SimpleNode")


# --- Test Cases ---


def test_data_manager_initialization(data_manager, shared_registry):
    """Test that DataManager initializes correctly."""
    assert data_manager._nodes is shared_registry
    assert data_manager.periods == []
    assert data_manager._node_factory is not None


def test_add_periods_initial(data_manager):
    """Test adding periods for the first time."""
    periods_to_add = ["2023Q2", "2023Q1", "2023Q3"]
    data_manager.add_periods(periods_to_add)
    assert data_manager.periods == ["2023Q1", "2023Q2", "2023Q3"]


def test_add_periods_with_duplicates(data_manager):
    """Test adding periods with duplicates within the input and existing list."""
    data_manager.add_periods(["2023Q1", "2023Q2"])
    periods_to_add = ["2023Q2", "2023Q3", "2023Q1", "2023Q3"]
    data_manager.add_periods(periods_to_add)
    assert data_manager.periods == ["2023Q1", "2023Q2", "2023Q3"]


def test_add_periods_empty(data_manager):
    """Test adding an empty list of periods."""
    data_manager.add_periods([])
    assert data_manager.periods == []
    data_manager.add_periods(["2023"])
    data_manager.add_periods([])
    assert data_manager.periods == ["2023"]


def test_add_node_new(data_manager, shared_registry, simple_node):
    """Test adding a new generic node."""
    added_node = data_manager.add_node(simple_node)
    assert added_node is simple_node
    assert shared_registry == {"SimpleNode": simple_node}
    assert data_manager.get_node("SimpleNode") is simple_node


def test_add_node_overwrite(data_manager, shared_registry, simple_node, caplog):
    """Test that adding a node with an existing name overwrites it and logs a warning."""
    # Add initial node
    data_manager.add_node(simple_node)
    assert shared_registry.get("SimpleNode") is simple_node

    # Add new node with same name
    new_node = ConcreteTestNode(name="SimpleNode")  # Different instance
    with caplog.at_level(logging.WARNING):
        added_node = data_manager.add_node(new_node)

    assert added_node is new_node
    assert shared_registry.get("SimpleNode") is new_node  # Overwritten
    assert len(caplog.records) == 1
    assert "Overwriting node 'SimpleNode'" in caplog.text


def test_get_node_exists(data_manager, shared_registry):
    """Test getting an existing node."""
    node = FinancialStatementItemNode(name="Revenue", values={"2023": 100})
    shared_registry["Revenue"] = node
    retrieved_node = data_manager.get_node("Revenue")
    assert retrieved_node is node


def test_get_node_not_exists(data_manager):
    """Test getting a non-existent node."""
    retrieved_node = data_manager.get_node("NonExistent")
    assert retrieved_node is None


def test_add_item_new(data_manager, shared_registry):
    """Test adding a new financial statement item."""
    values = {"2024": 1200, "2023": 1000}
    item_node = data_manager.add_item("Revenue", values)

    assert isinstance(item_node, FinancialStatementItemNode)
    assert item_node.name == "Revenue"
    assert item_node.values == {k: float(v) for k, v in values.items()}  # Values are floats
    assert shared_registry.get("Revenue") is item_node
    assert data_manager.periods == ["2023", "2024"]


def test_add_item_already_exists(data_manager):
    """Test adding an item when a node with the same name already exists."""
    data_manager.add_item("Revenue", {"2023": 100})
    with pytest.raises(ValueError, match="Node with name 'Revenue' already exists"):
        data_manager.add_item("Revenue", {"2024": 200})


def test_update_item_merge(data_manager, shared_registry):
    """Test updating an item by merging new values (default)."""
    initial_values = {"2023": 500, "2024": 600}
    data_manager.add_item("Expenses", initial_values)

    update_values = {"2024": 650, "2025": 700}  # Overlap and new
    updated_node = data_manager.update_item("Expenses", update_values)

    assert updated_node.name == "Expenses"
    expected_values = {"2023": 500.0, "2024": 650.0, "2025": 700.0}
    assert updated_node.values == expected_values
    assert shared_registry.get("Expenses").values == expected_values
    assert data_manager.periods == ["2023", "2024", "2025"]


def test_update_item_replace(data_manager, shared_registry):
    """Test updating an item by replacing all existing values."""
    initial_values = {"2023": 500, "2024": 600}
    data_manager.add_item("Expenses", initial_values)

    replace_values = {"2025": 700, "2026": 800}
    updated_node = data_manager.update_item("Expenses", replace_values, replace_existing=True)

    expected_values = {"2025": 700.0, "2026": 800.0}
    assert updated_node.values == expected_values
    assert shared_registry.get("Expenses").values == expected_values
    # Periods should reflect initial, update (merge), and replace operations
    assert data_manager.periods == ["2023", "2024", "2025", "2026"]


def test_update_item_not_found(data_manager):
    """Test updating an item that does not exist."""
    with pytest.raises(ValueError, match="Node 'NonExistent' not found in registry"):
        data_manager.update_item("NonExistent", {"2023": 100})


def test_update_item_wrong_type(data_manager, shared_registry, simple_node):
    """Test updating an item that is not a FinancialStatementItemNode."""
    shared_registry[simple_node.name] = simple_node  # Add a generic node
    with pytest.raises(TypeError, match="Cannot update item values for node 'SimpleNode'"):
        data_manager.update_item(simple_node.name, {"2023": 100})


def test_delete_item_exists(data_manager, shared_registry):
    """Test deleting an existing item."""
    data_manager.add_item("ToDelete", {"2023": 1})
    assert "ToDelete" in shared_registry
    deleted = data_manager.delete_item("ToDelete")
    assert deleted is True
    assert "ToDelete" not in shared_registry
    assert data_manager.get_node("ToDelete") is None


def test_delete_item_not_exists(data_manager, shared_registry, caplog):
    """Test deleting a non-existent item."""
    assert "NonExistent" not in shared_registry
    with caplog.at_level(logging.WARNING):
        deleted = data_manager.delete_item("NonExistent")

    assert deleted is False
    assert len(caplog.records) == 1
    assert "Attempted to delete non-existent node 'NonExistent'" in caplog.text


def test_periods_property(data_manager):
    """Test the periods property reflects current state after operations."""
    assert data_manager.periods == []
    data_manager.add_item("A", {"2023": 1, "2021": 2})
    assert data_manager.periods == ["2021", "2023"]
    data_manager.add_item("B", {"2022": 3})
    assert data_manager.periods == ["2021", "2022", "2023"]
    data_manager.update_item("A", {"2020": 0, "2023": 1.5})  # Merge
    assert data_manager.periods == ["2020", "2021", "2022", "2023"]
    data_manager.update_item("B", {"2024": 4}, replace_existing=True)
    assert data_manager.periods == ["2020", "2021", "2022", "2023", "2024"]
    data_manager.delete_item("A")
    # Periods list is not affected by deletion, only additions/updates
    assert data_manager.periods == ["2020", "2021", "2022", "2023", "2024"]
    data_manager.add_periods(["2022", "2025"])
    assert data_manager.periods == ["2020", "2021", "2022", "2023", "2024", "2025"]
