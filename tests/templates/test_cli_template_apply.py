"""CLI tests for `fsm template apply`."""

# ruff: noqa: S101, ANN001

from pathlib import Path

from click.testing import CliRunner

from fin_statement_model.cli import fsm
from fin_statement_model.core.graph import Graph
from fin_statement_model.templates.registry import TemplateRegistry


def test_template_apply_cli(tmp_path: Path, monkeypatch) -> None:
    """Happy-path: instantiate template and write to file."""
    monkeypatch.setenv("FSM_TEMPLATES_PATH", str(tmp_path))

    # Register dummy template -------------------------------------------------
    g = Graph(periods=["2023"])
    _ = g.add_financial_statement_item("Revenue", {"2023": 100.0})
    template_id = TemplateRegistry.register_graph(g, name="cli.apply", version="v1")

    out_file = tmp_path / "out.json"

    runner = CliRunner()
    result = runner.invoke(
        fsm,
        [
            "template",
            "apply",
            template_id,
            "--periods",
            "2024",
            "--output",
            str(out_file),
            "--format",
            "graph_definition_dict",
            "--quiet",
        ],
    )

    assert result.exit_code == 0, result.output
    assert out_file.exists(), "Output file not created"
