import pytest
import json
import pandas as pd

from fin_statement_model.core.graph.graph import Graph
from fin_statement_model.statements.manager import StatementManager
from fin_statement_model.statements.structure import StatementStructure, Section, LineItem
from fin_statement_model.io.exceptions import WriteError


def make_manager_with_simple_statement():
    """Helper to create a manager with one simple statement containing a single line item."""
    graph = Graph(periods=["2020"])
    manager = StatementManager(graph)
    stmt = StatementStructure(id="s1", name="Test Statement")
    section = Section(id="sec1", name="Section 1")
    item = LineItem(id="item1", name="Item 1", node_id="n1")
    section.add_item(item)
    stmt.add_section(section)
    manager.register_statement(stmt)
    # Add node values to graph
    graph.add_financial_statement_item("n1", {"2020": 123})
    return manager


def test_to_excel_creates_file(tmp_path):
    manager = make_manager_with_simple_statement()
    file_path = tmp_path / "output.xlsx"
    # Should not raise
    manager.export_to_excel("s1", str(file_path))
    assert file_path.exists()
    df = pd.read_excel(file_path)
    # Check if "  Item 1" exists as a value in the "Line Item" column (note indentation)
    assert "  Item 1" in df["Line Item"].values
    # Check the value in the correct row and column (data is in "2020" column)
    # Find the row where line_name is "  Item 1"
    item_row = df[df["Line Item"] == "  Item 1"]
    assert len(item_row) == 1
    assert item_row.iloc[0]["2020"] == 123


def test_to_json_creates_file(tmp_path):
    manager = make_manager_with_simple_statement()
    file_path = tmp_path / "output.json"
    manager.export_to_json("s1", str(file_path))
    assert file_path.exists()
    text = file_path.read_text()
    data = json.loads(text)
    # JSON orient columns: column names map to index dictionaries
    # Check if "  Item 1" exists as a value in the "Line Item" dictionary
    assert "  Item 1" in data["Line Item"].values()
    # Find the index where Line Item is "  Item 1"
    item_index = None
    for index, name in data["Line Item"].items():
        if name == "  Item 1":
            item_index = index
            break
    assert item_index is not None
    # Check the value using the found index - compare string to string
    assert data["2020"][item_index] == "123.00"


def test_export_invalid_statement_raises_statement_error(tmp_path):
    manager = make_manager_with_simple_statement()
    bad_path = tmp_path / "dummy.xlsx"
    # Expect WriteError because the service wraps the StatementError
    with pytest.raises(WriteError):
        manager.export_to_excel("invalid_id", str(bad_path))


def test_export_to_excel_bad_path_raises_export_error(tmp_path):
    manager = make_manager_with_simple_statement()
    # Path in non-existent directory
    bad_path = tmp_path / "no_dir" / "file.xlsx"
    with pytest.raises(WriteError):
        manager.export_to_excel("s1", str(bad_path))


def test_export_to_json_bad_path_raises_export_error(tmp_path):
    manager = make_manager_with_simple_statement()
    bad_path = tmp_path / "no_dir" / "file.json"
    with pytest.raises(WriteError):
        manager.export_to_json("s1", str(bad_path))
