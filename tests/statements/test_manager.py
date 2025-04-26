import pytest
import json
import pandas as pd

from fin_statement_model.core.graph.graph import Graph
from fin_statement_model.statements.manager import StatementManager
from fin_statement_model.statements.structure import StatementStructure, Section, LineItem
from fin_statement_model.io.exceptions import WriteError
from fin_statement_model.core.errors import StatementError


def make_manager_and_statement():
    """Initialize StatementManager with a simple statement and graph data."""
    graph = Graph(periods=["2020"])
    manager = StatementManager(graph)
    stmt = StatementStructure(id="s1", name="Test Statement")
    sec = Section(id="sec", name="Section")
    item1 = LineItem(id="item1", name="Item 1", node_id="n1")
    item2 = LineItem(id="item2", name="Item 2", node_id="n2")
    sec.add_item(item1)
    sec.add_item(item2)
    stmt.add_section(sec)
    manager.register_statement(stmt)
    # Add values in graph
    graph.add_financial_statement_item("n1", {"2020": 10})
    graph.add_financial_statement_item("n2", {"2020": 20})
    return manager


def test_full_pipeline_dataframe_and_html(tmp_path):
    manager = make_manager_and_statement()
    # Create calculations (none for plain items)
    created = manager.create_calculations("s1")
    assert created == []

    # Format as DataFrame
    df = manager.format_statement("s1", format_type="dataframe")
    assert isinstance(df, pd.DataFrame)
    # Check rows: Item 1, Item 2 (section headers likely excluded)
    assert len(df) == 2
    assert df.iloc[0]["Line Item"] == "  Item 1" # Note indentation
    assert df.iloc[0]["2020"] == "10.00" # Formatted string
    assert df.iloc[1]["Line Item"] == "  Item 2" # Note indentation
    assert df.iloc[1]["2020"] == "20.00" # Formatted string

    # Format as HTML
    html = manager.format_statement("s1", format_type="html")
    assert isinstance(html, str)
    # Check for non-indented item name and formatted value in HTML
    assert "Item 1" in html and "10.00" in html
    assert "Item 2" in html and "20.00" in html


def test_export_and_invalid_errors(tmp_path):
    manager = make_manager_and_statement()
    # Invalid statement id - Expect core StatementError
    with pytest.raises(StatementError):
        manager.create_calculations("invalid")

    # Valid export to Excel
    excel_file = tmp_path / "s1.xlsx"
    manager.export_to_excel("s1", str(excel_file))
    assert excel_file.exists()

    # Valid export to JSON
    json_file = tmp_path / "s1.json"
    manager.export_to_json("s1", str(json_file))
    assert json_file.exists()
    data = json.loads(json_file.read_text())
    # Check JSON structure based on new format
    assert "Line Item" in data
    assert "  Item 1" in data["Line Item"].values()
    assert "  Item 2" in data["Line Item"].values()
    # Find indices and check values (these are now formatted strings)
    idx1, idx2 = None, None
    for idx, name in data["Line Item"].items():
        if name == "  Item 1":
            idx1 = idx
        if name == "  Item 2":
            idx2 = idx
    assert idx1 is not None and idx2 is not None
    assert data["2020"][idx1] == "10.00"
    assert data["2020"][idx2] == "20.00"

    # Bad path
    bad_excel = tmp_path / "no_dir" / "f.xlsx"
    with pytest.raises(WriteError):
        manager.export_to_excel("s1", str(bad_excel))

    bad_json = tmp_path / "no_dir" / "f.json"
    with pytest.raises(WriteError):
        manager.export_to_json("s1", str(bad_json))
