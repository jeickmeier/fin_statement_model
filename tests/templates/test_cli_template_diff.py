"""CLI tests for `fsm template diff`."""

# ruff: noqa: S101, ANN001

from pathlib import Path

from click.testing import CliRunner

from fin_statement_model.cli import fsm
from fin_statement_model.core.graph import Graph
from fin_statement_model.templates.registry import TemplateRegistry


def test_template_diff_cli(tmp_path: Path, monkeypatch) -> None:
    """End-to-end diff CLI should exit with code 1 when differences exist."""
    monkeypatch.setenv("FSM_TEMPLATES_PATH", str(tmp_path))

    # Base graph ----------------------------------------------------------------
    g1 = Graph(periods=["2023"])
    _ = g1.add_financial_statement_item("Revenue", {"2023": 100.0})
    tid1 = TemplateRegistry.register_graph(g1, name="cli.diff", version="v1")

    # Modified graph with extra node --------------------------------------------
    g2 = g1.clone(deep=True)
    _ = g2.add_financial_statement_item("COGS", {"2023": 40.0})
    tid2 = TemplateRegistry.register_graph(g2, name="cli.diff", version="v2")

    runner = CliRunner()
    result = runner.invoke(
        fsm,
        [
            "template",
            "diff",
            tid1,
            tid2,
            "--summary",
        ],
    )

    # Expect exit code 1 when diff present
    assert result.exit_code == 1, result.output
    assert "DIFF" in result.output
