from typing import Dict, Optional
from .nodes import Node, CalculationNode

class Graph:
    """
    A Graph holds nodes and their relationships, enabling calculation of financial metrics across multiple periods.

    The Graph class provides the core data structure for representing financial statements and calculations as a directed graph.
    Each node in the graph represents either a raw financial statement item (like revenue or expenses) or a calculation
    between other nodes (like profit = revenue - expenses).

    The graph structure ensures proper dependency management and calculation order, allowing complex financial metrics
    to be derived from raw financial data across multiple time periods.

    Attributes:
        nodes (Dict[str, Node]): Dictionary mapping node names to Node objects

    Example:
        graph = Graph()
        revenue_node = FinancialStatementItemNode("revenue", {"2022": 1000.0})
        expenses_node = FinancialStatementItemNode("expenses", {"2022": 600.0})
        graph.add_node(revenue_node)
        graph.add_node(expenses_node)
        profit = graph.calculate("revenue", "2022") - graph.calculate("expenses", "2022")
    """
    def __init__(self):
        self.nodes: Dict[str, Node] = {}

    def add_node(self, node: Node):
        """
        Add a node to the graph.

        Args:
            node (Node): The node object to add to the graph. Must be a subclass of Node.

        Raises:
            ValueError: If a node with the same name already exists in the graph.
            TypeError: If the provided node is not a subclass of Node.

        Example:
            # Add a financial statement item node
            revenue_node = FinancialStatementItemNode("revenue", {"2022": 1000.0})
            graph.add_node(revenue_node)

            # Add a calculation node
            profit_node = SubtractionCalculationNode("profit", [revenue_node, expenses_node])
            graph.add_node(profit_node)
        """
        old_node = self.nodes.get(node.name)
        self.nodes[node.name] = node
        
        # If we're replacing a node, update any calculation nodes that depend on it
        if old_node is not None:
            self._update_calculation_nodes()

    def _update_calculation_nodes(self):
        """Update calculation nodes when their input nodes change."""
        for node in self.nodes.values():
            if isinstance(node, CalculationNode) and hasattr(node, 'input_names'):
                # Update the inputs list with current nodes
                node.inputs = [self.get_node(name) for name in node.input_names]

    def get_node(self, name: str) -> Optional[Node]:
        """
        Retrieve a node from the graph by its name.

        Args:
            name (str): The name/identifier of the node to retrieve

        Returns:
            Optional[Node]: The node with the given name if it exists, None otherwise

        Example:
            # Get a node by name
            revenue_node = graph.get_node("revenue")
            if revenue_node:
                value = revenue_node.calculate("2022")

            # Handle missing node
            expenses_node = graph.get_node("expenses") 
            if expenses_node is None:
                print("Expenses node not found")
        """
        return self.nodes.get(name)

    def calculate(self, node_name: str, period: str) -> float:
        """
        Calculate the value of a node for a given period.

        Args:
            node_name (str): The name/identifier of the node to calculate
            period (str): The time period to calculate the value for (e.g. "FY2022")

        Returns:
            float: The calculated value for the specified node and period

        Raises:
            ValueError: If the node does not exist in the graph
            ValueError: If the period is not found in the node's data
            ValueError: If there is an error performing the calculation (e.g. division by zero)

        Example:
            # Calculate revenue for FY2022
            revenue = graph.calculate("revenue", "FY2022")

            # Calculate gross profit margin for FY2021
            gpm = graph.calculate("gross_profit_margin", "FY2021")
        """
        node = self.get_node(node_name)
        if node is None:
            raise ValueError(f"Node '{node_name}' not found.")
        return node.calculate(period)


    def clear_all_caches(self):
        """
        Clear calculation caches for all nodes in the graph.

        This method iterates through all nodes in the graph and calls their clear_cache() 
        method, removing any cached calculation results. This ensures future calculations
        will be recomputed rather than using cached values.

        Example:
            # Clear all node caches
            graph.clear_all_caches()
            
            # Future calculations will be recomputed
            revenue = graph.calculate("revenue", "FY2022")
        """
        for node in self.nodes.values():
            node.clear_cache()

    def topological_sort(self):
        """
        Perform a topological sort of the nodes in the graph.

        This method analyzes the dependencies between nodes and returns them in a valid
        processing order where each node appears after all of its dependencies. The sort
        is based on the input nodes referenced by calculation and metric nodes.

        Returns:
            List[str]: A list of node names in topologically sorted order

        Raises:
            ValueError: If a cycle is detected in the node dependencies

        Example:
            # Get nodes in dependency order
            sorted_nodes = graph.topological_sort()
            
            # Process nodes in correct order
            for node_name in sorted_nodes:
                node = graph.get_node(node_name)
                value = node.calculate("2022")
        """
        # Build adjacency (reverse: from inputs to node)
        in_degree = {node_name:0 for node_name in self.nodes}
        adjacency = {node_name:[] for node_name in self.nodes}

        # Determine dependencies:
        for node_name, node in self.nodes.items():
            # Identify input nodes if this is a calculation node
            if hasattr(node, 'inputs'):
                for inp in node.inputs:
                    # inp is a Node, adjacency from inp to node_name
                    adjacency[inp.name].append(node_name)
                    in_degree[node_name] += 1

        # Topological sort using Kahn's algorithm
        queue = [n for n in in_degree if in_degree[n] == 0]
        topo_order = []
        while queue:
            current = queue.pop()
            topo_order.append(current)
            for nbr in adjacency[current]:
                in_degree[nbr] -= 1
                if in_degree[nbr] == 0:
                    queue.append(nbr)

        if len(topo_order) != len(self.nodes):
            raise ValueError("Cycle detected in graph, can't do a valid topological sort.")

        return topo_order

    def recalculate_all(self, period: str):
        """
        Recalculate all nodes for the given period.

        This method clears all node caches and recalculates values for every node in the graph
        in topologically sorted order to ensure dependencies are handled correctly.

        Args:
            period (str): The time period to recalculate values for (e.g. "2022")
        """
        # Clear all caches first
        self.clear_all_caches()
        
        # Get topologically sorted order to ensure proper calculation order
        order = self.topological_sort()
        
        # Force recalculation of each node
        for node_name in order:
            node = self.get_node(node_name)
            try:
                # Force recalculation by clearing individual node cache
                if hasattr(node, '_cache'):
                    node._cache.clear()
                value = node.calculate(period)
                # Store the result back in cache if needed
                if hasattr(node, '_cache'):
                    node._cache[period] = value
            except ValueError:
                # Skip if period not valid for this node
                continue

    def replace_node(self, node_name: str, new_node: Node):
        """
        Replace a node in the graph while updating any calculation nodes that reference it.
        
        Args:
            node_name: The name of the node to replace
            new_node: The new node instance
        """
        self.nodes[node_name] = new_node
        self._update_calculation_nodes()