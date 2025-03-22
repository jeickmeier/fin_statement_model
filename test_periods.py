from fin_statement_model.core.financial_statement import FinancialStatementGraph

# Create the main graph
fs = FinancialStatementGraph()
fs.graph._periods = ['2020', '2021']
print('Before:', fs.graph._periods)

# Create the other graph
other = FinancialStatementGraph()
other.graph._periods = ['2021', '2022', '2023']
print('Other graph periods:', other.graph.periods)

# Simulate the period update code from _merge_graph
print("\nSimulating the update manually:")
for period in other.graph.periods:
    print(f"Checking period: {period}")
    if period not in fs.graph.periods:
        print(f"  Adding {period}")
        fs.graph._periods.append(period)
    else:
        print(f"  {period} already exists")
print('After manual update:', fs.graph._periods)

# Reset and try actual merge
fs.graph._periods = ['2020', '2021']
print("\nResetting and calling actual _merge_graph:")
print('Before actual merge:', fs.graph._periods)
fs._merge_graph(other)
print('After actual merge:', fs.graph._periods)

# Modify _merge_graph to use _periods directly
print("\nPatching _merge_graph to use _periods directly:")
original_function = FinancialStatementGraph._merge_graph

def patched_merge_graph(self, other_graph):
    # Update periods - modified to use _periods directly
    for period in other_graph.graph.periods:
        if period not in self.graph._periods:
            self.graph._periods.append(period)
    self.graph._periods.sort()
    
    # Merge nodes (unchanged)
    for node_name, node in other_graph.graph.nodes.items():
        existing_node = self.graph.get_node(node_name)
        if existing_node is not None:
            # Update existing node with new values
            if hasattr(node, 'values'):
                for period, value in node.values.items():
                    existing_node.values[period] = value
            self.graph.add_node(existing_node)  # Re-add to update
        else:
            # Add new node
            self.graph.add_node(node)

# Replace the method
FinancialStatementGraph._merge_graph = patched_merge_graph

# Reset and try the patched merge
fs.graph._periods = ['2020', '2021']
print('Before patched merge:', fs.graph._periods)
fs._merge_graph(other)
print('After patched merge:', fs.graph._periods)

# Restore original function
FinancialStatementGraph._merge_graph = original_function 