"""Tests for writer helpers: ExcelWriter and MarkdownWriter."""

from __future__ import annotations


import pandas as pd
import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.core.nodes import FinancialStatementItemNode
from fin_statement_model.io.formats.excel_writer import ExcelWriter
from fin_statement_model.io.formats.markdown_writer import MarkdownWriter
from fin_statement_model.io.config.models import ExcelWriterConfig, MarkdownWriterConfig
from fin_statement_model.statements.structure.containers import (
    StatementStructure,
    Section,
)
from fin_statement_model.statements.structure.items import LineItem


@pytest.fixture()
def simple_graph() -> Graph:
    g = Graph(periods=["2023"])
    g.add_node(FinancialStatementItemNode(name="Revenue", values={"2023": 100.0}))
    return g


def test_excel_writer(tmp_path, simple_graph: Graph) -> None:
    """ExcelWriter should create a file without errors."""
    target_file = tmp_path / "output.xlsx"
    cfg = ExcelWriterConfig(sheet_name="Data")
    writer = ExcelWriter(cfg)

    writer.write(simple_graph, str(target_file))
    # pandas should have created the file
    assert target_file.exists() and target_file.stat().st_size > 0

    # Sanity check by reading back with pandas
    df = pd.read_excel(target_file, sheet_name="Data", index_col=0)
    assert not df.empty
    assert "2023" in df.columns
    assert "Revenue" in df.index


def _build_minimal_structure() -> StatementStructure:
    structure = StatementStructure(id="stmt", name="Test Statement")
    section = Section(id="sec", name="Main")
    line_item = LineItem(id="rev", name="Revenue", node_id="Revenue")
    section.add_item(line_item)
    structure.add_section(section)
    return structure


def test_markdown_writer(simple_graph: Graph) -> None:
    """MarkdownWriter should return a non-empty markdown string."""
    structure = _build_minimal_structure()
    cfg = MarkdownWriterConfig(format_type="markdown")
    writer = MarkdownWriter(cfg)

    md = writer.write(simple_graph, statement_structure=structure)
    assert isinstance(md, str) and "Revenue" in md
