from fin_statement_model.financial_statement import FinancialStatementGraph


def create_financial_statement(cells_info):
    """
    Create a FinancialStatementGraph object from a list of cell dictionaries.
    Each cell dict is expected to have keys such as 'row_name', 'column_name', and 'value'.

    This function groups cells by the 'row_name' (representing the financial statement item) and
    constructs a mapping of periods (from 'column_name') to values.
    
    Args:
        cells_info (list): List of dictionaries representing Excel cells.
            Example entry:
            {
                'cell_location': 'H63',
                'column': 'H',
                'row': 63,
                'value': 22,
                'formula': '=G63',
                'precedents': ['I63', 'H66'],
                'dependencies': ['G63'],
                'column_name': '2024',
                'row_name': 'Other Income / (Expense):',
                'formula_with_row_names': '=Other Income / (Expense):',
                'precedents_names': ['Other Income / (Expense):', 'Pre-Tax Income:'],
                'dependent_names': ['Other Income / (Expense):']
            },
            ...

    Returns:
        FinancialStatementGraph: The populated financial statement graph.
    """
    # Group cells by row_name to aggregate values per financial statement item
    items = {}
    unique_periods = set()
    for cell in cells_info:
        # Clean the item name and period
        item_name = cell.get('row_name', '').strip()
        period = cell.get('column_name', '').strip()
        value = cell.get('value')

        if not item_name or not period:
            continue

        unique_periods.add(period)

        if item_name not in items:
            items[item_name] = {}
        items[item_name][period] = value

    # Sort periods (assuming they are sortable, e.g., year strings) to pass to FinancialStatementGraph
    sorted_periods = sorted(unique_periods)

    # Create the FinancialStatementGraph with the detected periods
    fsg = FinancialStatementGraph(periods=sorted_periods)

    # Add each financial statement item with its period-value mapping
    for item, values in items.items():
        fsg.add_financial_statement_item(item, values)

    return fsg


# If run as a script, example usage:
if __name__ == '__main__':
    # Example cells_info list
    cells_info = [
        {
            'cell_location': 'H63',
            'column': 'H',
            'row': 63,
            'value': 22,
            'formula': '=G63',
            'precedents': ['I63', 'H66'],
            'dependencies': ['G63'],
            'column_name': '2024',
            'row_name': 'Other Income / (Expense):',
            'formula_with_row_names': '=Other Income / (Expense):',
            'precedents_names': ['Other Income / (Expense):', 'Pre-Tax Income:'],
            'dependent_names': ['Other Income / (Expense):']
        },
        {
            'cell_location': 'H64',
            'column': 'H',
            'row': 64,
            'value': 50,
            'formula': '',
            'precedents': [],
            'dependencies': [],
            'column_name': '2024',
            'row_name': 'Revenue:',
            'formula_with_row_names': '',
            'precedents_names': [],
            'dependent_names': []
        }
    ]

    # Create the financial statement object
    fs = create_financial_statement(cells_info)
    print("Financial Statement periods:", fs.graph.periods)
    # For demonstration, try calculating a dummy statement (actual calculation requires properly setup nodes)
    # This only shows the stored items
    for node in fs.graph.nodes.values():
        print(f"Item: {node.name}, Values: {getattr(node, 'values', {})}") 