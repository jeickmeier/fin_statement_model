"""Unit tests for the DataManager class.

This module contains test cases for the DataManager class which is responsible
for managing financial data in the graph.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fin_statement_model.core.data_manager import DataManager
from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode, Node


class TestDataManager:
    """Test cases for the DataManager class."""

    @pytest.fixture
    def graph(self):
        """Create a mock graph for testing."""
        return Mock(spec=Graph)

    @pytest.fixture
    def data_manager(self, graph):
        """Create a DataManager instance for testing."""
        return DataManager(graph)

    def test_init(self, data_manager, graph):
        """Test DataManager initialization."""
        assert data_manager.graph == graph

    def test_add_item(self, data_manager, graph):
        """Test adding a financial statement item."""
        # Setup
        name = "revenue"
        values = {"2022": 1000.0, "2023": 1200.0}
        mock_node = Mock(spec=FinancialStatementItemNode)
        
        # Create a MagicMock for nodes that will handle __contains__ properly
        mock_nodes = MagicMock()
        mock_nodes.__contains__.return_value = False  # Node doesn't exist yet
        graph.nodes = mock_nodes
        
        # Mock NodeFactory
        with patch('fin_statement_model.core.data_manager.NodeFactory') as mock_factory:
            mock_factory.create_financial_statement_item.return_value = mock_node
            
            # Execute
            result = data_manager.add_item(name, values)
            
            # Verify
            mock_factory.create_financial_statement_item.assert_called_once_with(name, values)
            graph.add_node.assert_called_once_with(mock_node)
            assert result == mock_node

    def test_add_item_duplicate(self, data_manager, graph):
        """Test adding an item with a duplicate name."""
        # Setup
        name = "revenue"
        values = {"2022": 1000.0}
        
        # Create a MagicMock for nodes that will handle __contains__ properly
        mock_nodes = MagicMock()
        mock_nodes.__contains__.return_value = True  # Node already exists
        graph.nodes = mock_nodes
        
        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            data_manager.add_item(name, values)
        assert str(exc_info.value) == f"Node '{name}' already exists in the graph"

    def test_update_item(self, data_manager, graph):
        """Test updating an existing financial statement item."""
        # Setup
        name = "revenue"
        existing_values = {"2022": 1000.0}
        new_values = {"2023": 1200.0}
        mock_node = Mock(spec=FinancialStatementItemNode)
        mock_node.values = existing_values.copy()
        graph.get_node.return_value = mock_node
        
        # Execute
        result = data_manager.update_item(name, new_values)
        
        # Verify
        graph.get_node.assert_called_once_with(name)
        assert mock_node.values == {"2022": 1000.0, "2023": 1200.0}
        graph.add_node.assert_called_once_with(mock_node)
        assert result == mock_node

    def test_update_item_replace(self, data_manager, graph):
        """Test updating an item with replace_existing=True."""
        # Setup
        name = "revenue"
        existing_values = {"2022": 1000.0}
        new_values = {"2023": 1200.0}
        mock_node = Mock(spec=FinancialStatementItemNode)
        mock_node.values = existing_values.copy()
        graph.get_node.return_value = mock_node
        
        # Execute
        result = data_manager.update_item(name, new_values, replace_existing=True)
        
        # Verify
        assert mock_node.values == new_values
        assert result == mock_node

    def test_update_item_not_found(self, data_manager, graph):
        """Test updating a non-existent item."""
        # Setup
        name = "revenue"
        values = {"2022": 1000.0}
        graph.get_node.return_value = None
        
        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            data_manager.update_item(name, values)
        assert str(exc_info.value) == f"No node found with name '{name}'"

    def test_update_item_wrong_type(self, data_manager, graph):
        """Test updating a node that is not a financial statement item."""
        # Setup
        name = "revenue"
        values = {"2022": 1000.0}
        mock_node = Mock(spec=Node)
        graph.get_node.return_value = mock_node
        
        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            data_manager.update_item(name, values)
        assert str(exc_info.value) == f"Node '{name}' is not a financial statement item node"

    def test_delete_item(self, data_manager, graph):
        """Test deleting a financial statement item."""
        # Setup
        name = "revenue"
        
        # Create mock nodes with proper dictionary behavior
        mock_nodes = MagicMock()
        mock_nodes.__contains__.return_value = True  # Node exists
        
        # Create an items() method that returns an empty iterator
        mock_nodes.items.return_value = []
        
        graph.nodes = mock_nodes
        
        # Execute
        result = data_manager.delete_item(name)
        
        # Verify
        assert result is True
        mock_nodes.__delitem__.assert_called_once_with(name)

    def test_delete_item_not_found(self, data_manager, graph):
        """Test deleting a non-existent item."""
        # Setup
        name = "revenue"
        
        # Create mock nodes with proper dictionary behavior
        mock_nodes = MagicMock()
        mock_nodes.__contains__.return_value = False  # Node doesn't exist
        graph.nodes = mock_nodes
        
        # Execute
        result = data_manager.delete_item(name)
        
        # Verify
        assert result is False
        mock_nodes.__delitem__.assert_not_called()

    def test_delete_item_referenced(self, data_manager, graph):
        """Test deleting an item that is referenced by other nodes."""
        # Setup
        name = "revenue"
        
        # Create mock input node
        mock_input = Mock()
        mock_input.name = name
        
        # Create mock calculation node with inputs
        mock_calc_node = Mock()
        mock_calc_node.inputs = [mock_input]
        
        # Create an items() method that returns the proper items
        mock_nodes = MagicMock()
        mock_nodes.__contains__.return_value = True  # Node exists
        mock_nodes.items.return_value = [
            ("revenue", Mock()),
            ("profit", mock_calc_node)
        ]
        
        graph.nodes = mock_nodes
        
        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            data_manager.delete_item(name)
        assert str(exc_info.value) == f"Cannot delete node '{name}' because it is referenced by 'profit'"

    def test_copy_forward_values(self, data_manager, graph):
        """Test copying forward values to missing periods."""
        # Setup
        periods = ["2021", "2022", "2023"]
        
        # Create a real dictionary for values
        values_dict = {"2021": 1000.0, "2022": 1200.0}
        
        # Create a properly mocked node
        mock_node = MagicMock(spec=FinancialStatementItemNode)
        
        # Configure the mock so isinstance(mock_node, FinancialStatementItemNode) returns True
        mock_node.__class__ = FinancialStatementItemNode
        
        # Set up values attribute as a dictionary
        mock_node.values = values_dict
        
        # Setup graph nodes
        mock_nodes = MagicMock()
        mock_nodes.items.return_value = [("revenue", mock_node)]
        graph.nodes = mock_nodes
        
        # Execute
        data_manager.copy_forward_values(periods)
        
        # Verify
        expected_values = {
            "2021": 1000.0,
            "2022": 1200.0,
            "2023": 1200.0  # Copied from 2022
        }
        assert values_dict == expected_values

    def test_copy_forward_values_no_historical(self, data_manager, graph):
        """Test copying forward values with no historical data."""
        # Setup
        periods = ["2021", "2022", "2023"]
        
        # Create a real dictionary for values
        values_dict = {}
        
        # Create a properly mocked node
        mock_node = MagicMock(spec=FinancialStatementItemNode)
        
        # Configure the mock so isinstance(mock_node, FinancialStatementItemNode) returns True
        mock_node.__class__ = FinancialStatementItemNode
        
        # Set up values attribute as a dictionary
        mock_node.values = values_dict
        
        # Setup graph nodes
        mock_nodes = MagicMock()
        mock_nodes.items.return_value = [("revenue", mock_node)]
        graph.nodes = mock_nodes
        
        # Execute
        data_manager.copy_forward_values(periods)
        
        # Verify
        assert values_dict == {}

    def test_copy_forward_values_mixed_periods(self, data_manager, graph):
        """Test copying forward values with mixed historical and forecast periods."""
        # Setup
        periods = ["2021", "2022", "2023", "2024"]
        
        # Create a simple test node class inheriting from FinancialStatementItemNode
        class TestNode(FinancialStatementItemNode):
            pass
        
        # Initial dictionary with missing periods
        values_dict = {
            "2021": 1000.0,
            "2023": 1500.0  # Missing 2022
        }
        
        # Create a node with our test values
        test_node = TestNode("revenue", values_dict)
        
        # Setup graph nodes to return our custom node
        mock_nodes = MagicMock()
        mock_nodes.items.return_value = [("revenue", test_node)]
        graph.nodes = mock_nodes
        
        # Execute
        data_manager.copy_forward_values(periods)
        
        # Verify
        expected_values = {
            "2021": 1000.0,
            "2022": 1000.0,  # Copied from 2021
            "2023": 1500.0,
            "2024": 1500.0  # Copied from 2023
        }
        assert test_node.values == expected_values 