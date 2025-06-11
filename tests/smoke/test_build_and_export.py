import pytest
from pathlib import Path

from fin_statement_model.core.graph.graph import Graph
from fin_statement_model.io.formats.markdown.writer import MarkdownWriter
from fin_statement_model.io.formats.excel.writer import ExcelWriter
from fin_statement_model.io.config.models import ExcelWriterConfig
from fin_statement_model.statements.structure import (
    StatementStructure,
    Section,
    LineItem,
)


def _build_sample_graph() -> Graph:
    """Create a minimal Graph with a single data node."""
    graph = Graph(periods=["2023"])
    graph.add_financial_statement_item("Revenue", {"2023": 1000.0})
    return graph


def _build_sample_structure() -> StatementStructure:
    """Construct a bare-bones StatementStructure that references the sample Graph."""
    statement = StatementStructure(
        id="IS",
        name="Income Statement",
        display_scale_factor=1.0,
    )
    section = Section(
        id="revenue_section",
        name="Revenue Section",
        display_scale_factor=1.0,
    )
    section.add_item(
        LineItem(
            id="rev",
            name="Revenue",
            node_id="Revenue",
            display_scale_factor=1.0,
        )
    )
    statement.add_section(section)
    return statement


@pytest.mark.parametrize("sheet_name", ["Sheet1"])
def test_markdown_and_excel_export(tmp_path: Path, sheet_name: str) -> None:
    """Ensure Markdown and Excel writers produce non-empty outputs."""
    graph = _build_sample_graph()
    structure = _build_sample_structure()

    # Markdown export (returns string)
    md_writer = MarkdownWriter()
    markdown_out = md_writer.write(graph, statement_structure=structure)
    assert isinstance(markdown_out, str) and markdown_out.strip(), (
        "Markdown output is empty"
    )

    # Excel export (writes file)
    target_file = tmp_path / "export.xlsx"
    cfg = ExcelWriterConfig(
        format_type="excel",
        target=str(target_file),
        sheet_name=sheet_name,
    )
    excel_writer = ExcelWriter(cfg)
    excel_writer.write(graph, target=str(target_file))

    assert target_file.exists() and target_file.stat().st_size > 0, (
        "Excel file not created or empty"
    )
